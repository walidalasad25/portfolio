from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsLineItem, QGraphicsSimpleTextItem, QGraphicsTextItem, QMenu, QGraphicsDropShadowEffect, QInputDialog
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPainter, QLinearGradient, QTextCursor
from PyQt6.QtCore import Qt, QSettings, QTimer, pyqtSignal
import json
import os
import math
from Core.Entities.node import Node
from Core.Services.node_service import NodeService
from Core.Services.percentage_engine import calculate_node_percentage
from Adapters.UI.Popups.node_hover_popup import NodeHoverPopup
from Infrastructure.variables import APP_STATE_PATH, BG_COLOR, TREE_DATA_PATH

class EditableTextItem(QGraphicsTextItem):
    def __init__(self, node, tree_view):
        super().__init__(node.label)
        self.node = node
        self.tree_view = tree_view
        self.original_text = node.label
        self.setDefaultTextColor(QColor("#ffffff"))
        self.setFont(QFont("Segoe UI", 10))
        
        self.setData(0, node)
        
        # Initially strictly read-only and ignores mouse (except hover now)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton) 
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        # Enable hover events so the popup doesn't die when hovering text
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        self.tree_view.show_hover_popup(self.node)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.tree_view.hide_hover_popup(self.node)
        super().hoverLeaveEvent(event)

    def start_editing(self):
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setFocus()
        
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        self.setTextCursor(cursor)

    def focusOutEvent(self, event):
        self.finish_editing()
        super().focusOutEvent(event)
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.clearFocus() # Triggers focusOut
            return
        elif event.key() == Qt.Key.Key_Escape:
            self.setPlainText(self.original_text)
            self.clearFocus()
            return
            
        super().keyPressEvent(event)

    def finish_editing(self):
        # Disable editing
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        # Check if changed
        new_text = self.toPlainText().strip()
        if new_text and new_text != self.original_text:
            self.tree_view.state_manager.rename_node(self.node, new_text)
            self.original_text = new_text
            QTimer.singleShot(0, self.tree_view.build_and_layout)
        else:
            self.setPlainText(self.original_text)


class NodeBox(QGraphicsRectItem):
    def __init__(self, x, y, w, h, node, tree_view):
        super().__init__(x, y, w, h)
        self.node = node
        self.tree_view = tree_view
        self.setAcceptHoverEvents(True)
        # Style
        self.setBrush(QBrush(QColor("#3c3c3c")))
        self.setPen(QPen(QColor("#d4d4d4"), 2))
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setData(0, node)

    def update_color(self, is_active):
        status = getattr(self.node, 'status', 'neutral')
        
        target_glow_color = None
        target_blur = 0

        if is_active:
            self.setBrush(QBrush(QColor("#e65100"))) # Deep Orange
            self.setPen(QPen(QColor("#ffffff"), 2))
            target_glow_color = QColor("#ffae00")
            target_blur = 50
        elif status == "solved" and self.tree_view.show_percentages:
            self.setBrush(QBrush(QColor("#1b5e20"))) # Dark Green
            self.setPen(QPen(QColor("#4CAF50"), 2)) 
            target_glow_color = QColor("#4CAF50")
            target_blur = 30
        else:
            self.setBrush(QBrush(QColor("#3c3c3c")))
            self.setPen(QPen(QColor("#d4d4d4"), 2))
            target_glow_color = None

        # Optimize Effect Update
        current_effect = self.graphicsEffect()
        if target_glow_color:
            if isinstance(current_effect, QGraphicsDropShadowEffect):
                if current_effect.color() != target_glow_color or current_effect.blurRadius() != target_blur:
                    current_effect.setColor(target_glow_color)
                    current_effect.setBlurRadius(target_blur)
            else:
                glow = QGraphicsDropShadowEffect()
                glow.setBlurRadius(target_blur)
                glow.setColor(target_glow_color)
                glow.setOffset(0, 0)
                self.setGraphicsEffect(glow)
        else:
            if current_effect:
                self.setGraphicsEffect(None)

    def hoverEnterEvent(self, event):
        self.tree_view.show_hover_popup(self.node)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.tree_view.hide_hover_popup(self.node)
        super().hoverLeaveEvent(event)

class Tree(QGraphicsView):
    node_double_clicked = pyqtSignal(object) # Carries the Node object

    def __init__(self, state_manager=None, show_percentages=True):
        super().__init__()
        self.show_percentages = show_percentages
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setBackgroundBrush(QBrush(QColor(BG_COLOR)))
        
        # Navigation Settings
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMouseTracking(True) # Required for automatic cursor changes
        self._is_panning = False
        self._pan_start = None
        self._pan_click_pos = None

        # Persistence
        self.state_file_path = APP_STATE_PATH
        if state_manager:
            self.state_manager = state_manager
        else:
            self.state_manager = NodeService(TREE_DATA_PATH, "My Problems")
        
        self.perspective_name = self.state_manager.initial_root_label.lower().replace("my ", "") # e.g. 'problems' or 'values'
        
        # Active State
        self.active_node = None
        self.active_beam = None
        
        # Connection State
        self.connecting_node = None
        self.temp_connection_line = None
        self.connection_instruction_text = None
        
        # Hover State
        self.hover_popup = NodeHoverPopup()
        self.scene.addItem(self.hover_popup)
        self.current_hovered_node = None

        # Hover Refresh Timer
        self.hover_refresh_timer = QTimer(self)
        self.hover_refresh_timer.timeout.connect(self.refresh_hover_content)
        self.hover_refresh_timer.start(1000)

    def refresh_hover_content(self):
        """Periodically refreshes the hover popup if it is visible."""
        if self.current_hovered_node and self.hover_popup.isVisible():
            self.hover_popup.update_node(self.current_hovered_node, show_status=self.show_percentages)


    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        
        clicked_node = None
        if isinstance(item, (NodeBox, QGraphicsSimpleTextItem, EditableTextItem)):
             clicked_node = item.data(0)
             
        if clicked_node:
            # Emit signal for Main Window to handle
            self.node_double_clicked.emit(clicked_node)
            
            # Set active node and update visuals
            self.active_node = clicked_node
            self.update_node_styles()

            # Auto-Center on the clicked node
            self.centerOn(clicked_node.x + clicked_node.width/2, clicked_node.y + clicked_node.height/2)
            
            # Remove old beam if active (Cleanup)
            if self.active_beam:
                if isinstance(self.active_beam, list):
                     for item in self.active_beam: self.scene.removeItem(item)
                else:
                     self.scene.removeItem(self.active_beam)
                self.active_beam = None

            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
            
    def keyPressEvent(self, event):
        # Undo: Ctrl + Z
        if event.key() == Qt.Key.Key_Z and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            if self.state_manager.undo():
                self.build_and_layout()
        # Redo: Ctrl + Y
        elif event.key() == Qt.Key.Key_Y and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            if self.state_manager.redo():
                self.build_and_layout()
        # Select All: Ctrl + A
        elif event.key() == Qt.Key.Key_A and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.select_all()
        # Delete: Del Key
        elif event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        # Clear focus on any potential click to ensure editing commits (if logic allows)
        if not self.itemAt(event.pos()):
             self.scene.clearFocus()
             
        # Handle Connection Mode Click
        if self.connecting_node:
            # We use items() because itemAt() might hit the connection line itself
            items = self.items(event.pos())
            target_node = None
            
            for item in items:
                if item == self.temp_connection_line:
                    continue
                    
                if isinstance(item, (NodeBox, QGraphicsSimpleTextItem, EditableTextItem)):
                    # Check if this item carries a node
                    potential_node = item.data(0)
                    if potential_node:
                        target_node = potential_node
                        break
            
            if target_node and target_node != self.connecting_node:
                # Complete Connection
                self.finish_connection(target_node)
            else:
                # Cancel or Invalid
                self.cancel_connection()
            
            event.accept()
            return

        # Check if clicking on an item
        item = self.itemAt(event.pos())
        
        if item:
            # Let standard event handle selection/interaction
            super().mousePressEvent(event)
        else:
            # Background Interactions
            
            # Shift + Drag = Rubberband Selection
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
                super().mousePressEvent(event)
                return

            # Start Panning (Left or Middle button)
            if event.button() == Qt.MouseButton.LeftButton or event.button() == Qt.MouseButton.MiddleButton:
                self._is_panning = True
                self._pan_start = event.pos()
                if event.button() == Qt.MouseButton.LeftButton:
                    self._pan_click_pos = event.pos() # Track click for potential deselect
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()

    def mouseReleaseEvent(self, event):
        # If we were in Rubberband mode, reset
        if self.dragMode() == QGraphicsView.DragMode.RubberBandDrag:
            super().mouseReleaseEvent(event)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            return

        if self._is_panning:
            self._is_panning = False
            
            # Check for Click vs Drag logic (Deselect on Background Click)
            if event.button() == Qt.MouseButton.LeftButton and self._pan_click_pos:
                if (event.pos() - self._pan_click_pos).manhattanLength() < 5:
                    self.scene.clearSelection()

            # Reset cursor based on current position
            if self.itemAt(event.pos()):
                self.setCursor(Qt.CursorShape.ArrowCursor)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
        
        # Safety Check: Did we pan the view out of sight?
        self.check_visibility()

    def mouseMoveEvent(self, event):
        if self.dragMode() == QGraphicsView.DragMode.RubberBandDrag:
            super().mouseMoveEvent(event)
            return

        if self.connecting_node:
            # Update temporary line
            start_pos = self.mapFromScene(self.connecting_node.x + self.connecting_node.width/2, 
                                        self.connecting_node.y + self.connecting_node.height)
            
            # Draw line from node center-bottom to mouse
            # We need scene coords for the line item
            scene_mouse_pos = self.mapToScene(event.pos())
            
            start_scene = self.connecting_node.x + self.connecting_node.width/2
            start_y = self.connecting_node.y + self.connecting_node.height
            
            if self.temp_connection_line:
                self.temp_connection_line.setLine(start_scene, start_y, 
                                                scene_mouse_pos.x(), scene_mouse_pos.y())
            
            # Update text position
            if self.connection_instruction_text:
                 self.connection_instruction_text.setPos(scene_mouse_pos.x() + 15, scene_mouse_pos.y() + 15)

            event.accept()
            return

        if self._is_panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            # Automatic Cursor Switching
            if self.itemAt(event.pos()):
                self.setCursor(Qt.CursorShape.ArrowCursor)
            else:
                # If Shift is held, maybe show Cross? 
                 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                     self.setCursor(Qt.CursorShape.CrossCursor)
                 else:
                     self.setCursor(Qt.CursorShape.OpenHandCursor)
            super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        # Calculate smooth zoom factor based on scroll delta
        zoom_factor = 1.0015 ** event.angleDelta().y()
        
        # Clamp Scale
        current_scale = self.transform().m11()
        new_scale = current_scale * zoom_factor
        
        if new_scale < 0.1:
            zoom_factor = 0.1 / current_scale
            
        self.scale(zoom_factor, zoom_factor)
        self.check_visibility()
        
    def showEvent(self, event):
        super().showEvent(event)
        # We use a singleShot timer to run this AFTER the layout is fully processed/sized
        # otherwise fitInView might calculate on a 0x0 window.
        if not hasattr(self, '_initialized'):
            QTimer.singleShot(0, self.load_initial_view)
            self._initialized = True

    def build_and_layout(self):
        self.scene.clear()
        
        # Re-create persistent UI elements after clear
        self.hover_popup = NodeHoverPopup()
        self.scene.addItem(self.hover_popup)
        self.current_hovered_node = None
        
        # Use roots from manager
        self.roots = self.state_manager.roots
        
        # Calculate Layout
        if self.roots:
            for root in self.roots:
                 # Anchor Strategy: 
                 # We want the root to stay exactly where it is (root.x, root.y).
                 # But we need to layout its children relative to it.
                 target_x = root.x
                 target_y = root.y
                 
                 # 1. Calculate the layout of the subtree starting at 0,0 (virtual space)
                 # This sets root.x to the visual center of the subtree
                 self.layout_tree(root, 0, 0, 80)
                 
                 # 2. Calculate shift needed to move root back to target
                 dx = target_x - root.x
                 dy = target_y - root.y
                 
                 # 3. Apply shift to entire subtree
                 root.translate(dx, dy)
                 
                 self.draw_node(root)
            
            self.update_node_styles()
            
            # Set scene rect so scrolling knows the boundaries
            rect = self.scene.itemsBoundingRect()
            margin = 50000 # Massive bound for effectively infinite panning
            rect.adjust(-margin, -margin, margin, margin)
            self.setSceneRect(rect)
            
    def get_view_state(self):
        center = self.mapToScene(self.viewport().rect().center())
        return {
            "center_x": center.x(),
            "center_y": center.y(),
            "zoom": self.transform().m11()
        }

    def set_view_state(self, state):
        if not state: return
        zoom = state.get("zoom", 1.0)
        center_x = state.get("center_x", 0.0)
        center_y = state.get("center_y", 0.0)
        
        matrix = self.transform()
        matrix.reset()
        matrix.scale(zoom, zoom)
        self.setTransform(matrix)
        self.centerOn(center_x, center_y)

    def save_state(self):
        state = self.get_view_state()
        
        # Load existing full state to preserve other perspectives
        full_state = {}
        if os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, 'r') as f:
                    full_state = json.load(f)
            except:
                full_state = {}
        
        # Update current perspective
        full_state[self.perspective_name] = {
            "view_center_x": state["center_x"],
            "view_center_y": state["center_y"],
            "view_zoom": state["zoom"]
        }
        
        try:
            with open(self.state_file_path, 'w') as f:
                json.dump(full_state, f, indent=4)
        except Exception as e:
            print(f"Failed to save state: {e}")

    def load_initial_view(self):
        self.build_and_layout()
        
        full_state = {}
        if os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, 'r') as f:
                    full_state = json.load(f)
            except:
                pass
        
        # Check for specific perspective state
        state = full_state.get(self.perspective_name, {})
        
        if "view_zoom" in state:
            # Restore previous state
            zoom = float(state.get("view_zoom", 1.0))
            center_x = float(state.get("view_center_x", 0.0))
            center_y = float(state.get("view_center_y", 0.0))

            # Apply Zoom
            matrix = self.transform()
            matrix.reset()
            matrix.scale(zoom, zoom)
            self.setTransform(matrix)

            # Apply Pan
            self.centerOn(center_x, center_y)
        else:
            # Fallback to shared global if perspective doesn't exist yet
            global_zoom = full_state.get("view_zoom")
            if global_zoom is not None:
                self.set_view_state({
                    "zoom": float(global_zoom),
                    "center_x": float(full_state.get("view_center_x", 0)),
                    "center_y": float(full_state.get("view_center_y", 0))
                })
            else:
                # First time run: Fit everything
                if self.scene.itemsBoundingRect().width() > 0:
                    self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def check_visibility(self):
        """Ensure the content hasn't been panned/zoomed completely off-screen."""
        view_rect_scene = self.mapToScene(self.viewport().rect()).boundingRect()
        items_rect = self.scene.itemsBoundingRect()
        
        # If items are empty (no nodes), nothing to do
        if items_rect.width() == 0:
            return

        # Check intersection
        if not view_rect_scene.intersects(items_rect):
            # We are lost! Smoothly reset.
            print("Tree lost! Auto-centering...")
            self.fitInView(items_rect, Qt.AspectRatioMode.KeepAspectRatio)
            # Maybe back off a little bit
            self.scale(0.9, 0.9)
        else:
            # OPTIONAL: Hard constraint
            # If we want to guarantee it NEVER leaves, we can clamp the center.
            # But the current intersection check is usually enough to prevent "completely lost".
            pass

    def contextMenuEvent(self, event):
        item = self.scene.itemAt(self.mapToScene(event.pos()), self.transform())
        
        # Check if we clicked a node
        clicked_node = None
        if isinstance(item, (NodeBox, QGraphicsSimpleTextItem, EditableTextItem)):
             clicked_node = item.data(0)

        menu = QMenu(self)

        if clicked_node:
            add_child_action = menu.addAction("Add Child")
            connect_action = menu.addAction("Connect")
            menu.addSeparator()
            
            # Toggle Solved/Neutral
            if self.show_percentages:
                current_status = getattr(clicked_node, 'status', 'neutral')
                if current_status == "solved":
                    toggle_solved_action = menu.addAction("Unmark Solved")
                else:
                    toggle_solved_action = menu.addAction("Mark Solved")
            else:
                toggle_solved_action = None
                
            menu.addSeparator()
            
            # Protect "My Life" from Rename/Delete
            is_life = (clicked_node.label == "My Life")
            rename_action = menu.addAction("Rename")
            rename_action.setEnabled(not is_life)
            
            delete_action = menu.addAction("Delete")
            delete_action.setEnabled(not is_life)
            
            delete_all_action = menu.addAction("Delete All")
            delete_all_action.setEnabled(not is_life)
            
            action = menu.exec(event.globalPos())
            
            # Check for multi-selection first
            selected_items = self.scene.selectedItems()
            is_multi_select = item.isSelected() and len(selected_items) > 1

            if action == add_child_action:
                self.add_child_node(clicked_node)
            elif action == connect_action:
                self.start_connection(clicked_node)
            elif action == toggle_solved_action:
                new_status = "neutral" if current_status == "solved" else "solved"
                self.state_manager.update_node_status(clicked_node, new_status)
                self.build_and_layout()
            elif action == rename_action:
                self.rename_node(clicked_node)
            elif action == delete_action:
                if is_multi_select:
                     self.delete_selected(keep_children=True)
                else:
                     self.delete_node(clicked_node, keep_children=True)
            elif action == delete_all_action:
                 if is_multi_select:
                     self.delete_selected(keep_children=False)
                 else:
                     self.delete_node(clicked_node, keep_children=False)
        else:
            # Background Context Menu
            add_node_action = menu.addAction("Add Node")
            action = menu.exec(event.globalPos())
            
            if action == add_node_action:
                # Pass the global position, we need to map it nicely
                self.add_node(event.pos())
                
    def add_child_node(self, parent_node):
        new_node = self.state_manager.add_child_node(parent_node, "New Child")
        self.build_and_layout()
        self.centerOn(new_node.x + new_node.width/2, new_node.y + new_node.height/2)
                
    def add_node(self, pos):
        # Convert view position (mouse) to scene position
        scene_pos = self.mapToScene(pos)
        new_node = self.state_manager.add_root_node("New Node", scene_pos.x(), scene_pos.y())
        self.build_and_layout()
        self.centerOn(new_node.x + new_node.width/2, new_node.y + new_node.height/2)

    def start_connection(self, node):
        self.connecting_node = node
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Create temp line
        start_x = node.x + node.width / 2
        start_y = node.y + node.height
        self.temp_connection_line = QGraphicsLineItem(start_x, start_y, start_x, start_y)
        pen = QPen(QColor("#00ff00"), 2) # Green line for active connection
        pen.setStyle(Qt.PenStyle.DashLine)
        self.temp_connection_line.setPen(pen)
        self.scene.addItem(self.temp_connection_line)

        # Create instruction text
        self.connection_instruction_text = QGraphicsSimpleTextItem("Click on Parent Node")
        self.connection_instruction_text.setBrush(QBrush(QColor("#00ff00")))
        font = QFont("Segoe UI", 12)
        font.setBold(True)
        self.connection_instruction_text.setFont(font)
        self.connection_instruction_text.setZValue(100) # Ensure it's on top
        self.scene.addItem(self.connection_instruction_text)
        # Initial position
        self.connection_instruction_text.setPos(start_x + 15, start_y + 15)

    def finish_connection(self, target_parent):
        # Logic to reparent
        success = self.state_manager.reparent_node(self.connecting_node, target_parent)
        self.cancel_connection() # Clean up UI state
        
        if success:
             self.build_and_layout()

    def cancel_connection(self):
        if self.temp_connection_line:
            self.scene.removeItem(self.temp_connection_line)
            self.temp_connection_line = None
        
        if self.connection_instruction_text:
            self.scene.removeItem(self.connection_instruction_text)
            self.connection_instruction_text = None

        self.connecting_node = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def rename_node(self, node):
        # Find the text item for this node
        for item in self.scene.items():
            if isinstance(item, EditableTextItem) and item.data(0) == node:
                 item.start_editing()
                 break

    def select_all(self):
        for item in self.scene.items():
            if isinstance(item, NodeBox):
                item.setSelected(True)

    def delete_selected(self, keep_children=False):
        selected_items = self.scene.selectedItems()
        nodes_to_delete = []
        for item in selected_items:
            if isinstance(item, NodeBox):
                node = item.data(0)
                if node and node.parent: # Can't delete root
                    nodes_to_delete.append(node)
        
        if not nodes_to_delete:
            return

        # Delegate to manager
        success = False
        if keep_children:
            success = self.state_manager.delete_nodes_keep_children(nodes_to_delete)
        else:
            success = self.state_manager.delete_nodes(nodes_to_delete)

        if success:
            self.build_and_layout()

    def delete_node(self, node, keep_children=False):
        # Delegate to manager
        success = False
        if keep_children:
            success = self.state_manager.delete_nodes_keep_children([node])
        else:
            success = self.state_manager.delete_nodes([node])

        if success:
            self.build_and_layout()

    def layout_tree(self, node, x, y, level_height):
        """Simple recursive layout. Returns the total width of this node's subtree."""
        node.y = y
        
        # Calculate dynamic width based on text
        from PyQt6.QtGui import QFontMetrics
        metrics = QFontMetrics(QFont("Segoe UI", 10))
        text_width = metrics.horizontalAdvance(node.label)
        node.width = max(100, text_width + 40) # Min 100, add 40px padding
        
        if not node.children:
            node.x = x
            return node.width + 40 # 40px margin
            
        total_width = 0
        child_x = x
        
        # Calculate subtree widths
        subtree_widths = []
        for child in node.children:
            w = self.layout_tree(child, child_x, y + level_height, level_height)
            subtree_widths.append(w)
            child_x += w
            total_width += w
            
        # Center parent over its children's subtree
        # Use the total_width to center, not just the children's positions
        node.x = x + (total_width - node.width) / 2
        
        return max(total_width, node.width + 40)


    def draw_node(self, node):
        # Draw connections first (so lines are behind boxes)
        for child in node.children:
            self.draw_connection(node, child)
            self.draw_node(child)

        # Draw Box
        rect_item = NodeBox(node.x, node.y, node.width, node.height, node, self)
        self.scene.addItem(rect_item)

        # Draw Text
        text_item = EditableTextItem(node, self)
        
        # Center text in box
        text_rect = text_item.boundingRect()
        text_x = node.x + (node.width - text_rect.width()) / 2
        text_y = node.y + (node.height - text_rect.height()) / 2
        text_item.setPos(text_x, text_y)
        
        self.scene.addItem(text_item)

        # Draw Percentage Badge (Top-Right)
        if self.show_percentages:
            percentage = calculate_node_percentage(node)
            perc_item = QGraphicsSimpleTextItem(f"{int(percentage)}%")
            perc_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            
            # Color based on progress
            if percentage == 100:
                perc_item.setBrush(QBrush(QColor("#00E676"))) # Green
            elif percentage > 0:
                perc_item.setBrush(QBrush(QColor("#ffae00"))) # Orange
            else:
                perc_item.setBrush(QBrush(QColor("#888888"))) # Grey

            # Position: Center of the top edge of the box (above the label)
            perc_rect = perc_item.boundingRect()
            perc_x = node.x + (node.width - perc_rect.width()) / 2
            perc_y = node.y - perc_rect.height() - 2
            perc_item.setPos(perc_x, perc_y)
            
            # Add a subtle shadow
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(4)
            shadow.setOffset(1, 1)
            shadow.setColor(QColor(0, 0, 0, 200))
            perc_item.setGraphicsEffect(shadow)
            
            self.scene.addItem(perc_item)

        # Draw Cycle Percentage Badge (Bottom-Right) - Blue
        if hasattr(node, 'cycle_time'):
            from Infrastructure.variables import CYCLE_TIME_LIMIT
            cycle_perc = (node.cycle_time / CYCLE_TIME_LIMIT) * 100
            
            c_perc_item = QGraphicsSimpleTextItem(f"{int(cycle_perc)}%")
            c_perc_item.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            c_perc_item.setBrush(QBrush(QColor("#2196F3"))) # Electric Blue
            
            # Position: Bottom-right corner of the box
            c_rect = c_perc_item.boundingRect()
            c_x = node.x + node.width - c_rect.width() - 4
            c_y = node.y + node.height - c_rect.height() - 2
            c_perc_item.setPos(c_x, c_y)
            
            # Subtle shadow
            c_shadow = QGraphicsDropShadowEffect()
            c_shadow.setBlurRadius(2)
            c_shadow.setOffset(1, 1)
            c_shadow.setColor(QColor(0, 0, 0, 180))
            c_perc_item.setGraphicsEffect(c_shadow)
            
            self.scene.addItem(c_perc_item)

    def draw_connection(self, parent, child):
        start_x = parent.x + parent.width / 2
        start_y = parent.y + parent.height
        end_x = child.x + child.width / 2
        end_y = child.y
        
        # Draw elbow connector
        path = QGraphicsLineItem(start_x, start_y, end_x, end_y)
        pen = QPen(QColor("#888888"), 2)
        path.setPen(pen)
        self.scene.addItem(path)

    def update_node_styles(self):
        active_label = self.active_node.label if self.active_node else None
        
        for item in self.scene.items():
            if isinstance(item, NodeBox):
                # Identity check first, then Label check as fallback for shared nodes between perspectives
                is_active = (item.node == self.active_node) or (active_label and item.node.label == active_label)
                item.update_color(is_active)


    def show_hover_popup(self, node):
        # Update content
        self.hover_popup.update_node(node, show_status=self.show_percentages)
        
        # Position simply above the node
        self.hover_popup.setPos(node.x + node.width + 10, node.y)
        self.hover_popup.show()
        
        self.current_hovered_node = node
        
    def hide_hover_popup(self, node):
        # Only hide if we are leaving the currently shown node
        # This prevents hiding the new popup if we quickly moved to another node
        if self.current_hovered_node == node:
            self.hover_popup.hide()
            self.current_hovered_node = None
