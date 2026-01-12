from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsDropShadowEffect
from PyQt6.QtGui import QBrush, QPen, QColor, QFont
from PyQt6.QtCore import Qt
import datetime
from Infrastructure.variables import BG_COLOR, CARD_BG_COLOR, TEXT_COLOR, PRIMARY_COLOR, SECONDARY_COLOR, BORDER_COLOR

class NodeHoverPopup(QGraphicsRectItem):
    def __init__(self):
        super().__init__(0, 0, 160, 85)
        self.setBrush(QBrush(QColor(CARD_BG_COLOR)))
        self.setPen(QPen(QColor(PRIMARY_COLOR), 1))
        self.setZValue(200) # Topmost
        
        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0,0,0, 150))
        self.setGraphicsEffect(shadow)
        
        # Init Items
        self.title_item = QGraphicsSimpleTextItem("", self)
        self.title_item.setBrush(QBrush(QColor(TEXT_COLOR)))
        self.title_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.title_item.setPos(10, 10)
        
        self.info_item = QGraphicsSimpleTextItem("", self)
        self.info_item.setBrush(QBrush(QColor(TEXT_COLOR)))
        self.info_item.setFont(QFont("Segoe UI", 8))
        self.info_item.setPos(10, 30)
        
        self.hide() # Hidden by default

    def update_node(self, node, show_status=True):
        if show_status:
            is_solved = getattr(node, "status", "neutral") == "solved"
            status = "Completed" if is_solved else "Active"
        else:
            status = "Information"
        
        # Always aggregate stats recursively so parents show subtree totals
        stats = self._aggregate_stats_recursive(node)
        
        # Determine Prefix based on root label or depth
        if node.parent is None:
             prefix = f"Global "
        else:
             prefix = ""

        # Dynamic Time Formatting
        time_sec = stats["time"]
        time_str = self.format_time(time_sec)
        
        words = stats["words"]
        chars = stats["chars"]

        self.title_item.setText(f"{prefix}{status}")
        if show_status:
            self.title_item.setBrush(QBrush(QColor(SECONDARY_COLOR) if status == "Completed" else QColor(PRIMARY_COLOR)))
        else:
            self.title_item.setBrush(QBrush(QColor(TEXT_COLOR)))
        
        if hasattr(node, 'cycle_time'):
            cycle_limit = 28800 # or import CYCLE_TIME_LIMIT
            cycle_perc = (node.cycle_time / cycle_limit) * 100
            cycle_hours = node.cycle_time / 3600
            
            self.info_item.setText(
                f"Time: {time_str}\n"
                f"Words: {words}\n"
                f"Chars: {chars}\n"
                f"Cycle: {node.cycle_count} ({cycle_hours:.1f}h / 8h)"
            )
            # Adjust height to fit extra line
            self.setRect(0, 0, 160, 100)
        else:
            self.info_item.setText(
                f"Time: {time_str}\n"
                f"Words: {words}\n"
                f"Chars: {chars}"
            )
            self.setRect(0, 0, 160, 85)

    def _get_node_intentions_stats(self, node):
        totals = {"time": 0, "words": 0, "chars": 0}
        
        # Add archived stats (from cleared intentions and deleted children)
        archived = getattr(node, 'archived_stats', {"time": 0, "words": 0, "chars": 0})
        totals['time'] += archived.get('time', 0)
        totals['words'] += archived.get('words', 0)
        totals['chars'] += archived.get('chars', 0)
        
        # Add stats from active intentions
        for intent in getattr(node, 'intentions', []):
            stats = intent.get('stats', {})
            totals['time'] += stats.get('time', 0)
            totals['words'] += stats.get('words', 0)
            totals['chars'] += stats.get('chars', 0)
        return totals

    def _aggregate_stats_recursive(self, node):
        totals = self._get_node_intentions_stats(node)
        for child in node.children:
            child_totals = self._aggregate_stats_recursive(child)
            totals['time'] += child_totals['time']
            totals['words'] += child_totals['words']
            totals['chars'] += child_totals['chars']
        return totals

    def format_time(self, seconds):
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        elif seconds < 86400:
            return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
        else:
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            return f"{days}d {hours}h"
