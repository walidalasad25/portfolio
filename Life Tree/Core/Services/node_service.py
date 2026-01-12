import json
import os
from Core.Entities.node import Node

class NodeService:
    """
    Core service for managing the tree structure and its state.
    (Derived from the original NodeStateManager)
    """
    def __init__(self, file_path, initial_root_label="My Life"):
        self.file_path = file_path
        self.initial_root_label = initial_root_label
        self.roots = []
        self.undo_stack = []
        self.redo_stack = []
        self.load()

    def load(self):
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.roots = [Node.from_dict(d) for d in data]
                    else:
                        self.roots = [Node.from_dict(data)]
            else:
                self.roots = [Node(self.initial_root_label)]
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading tree data: {e}")
            self.roots = [Node(self.initial_root_label)]
        
        # Ensure initial_root_label is the ONLY root node
        life_node = next((r for r in self.roots if r.label == self.initial_root_label), None)
        if not life_node:
            life_node = Node(self.initial_root_label)
            self.roots.insert(0, life_node)
        
        # Move all other roots to be children of initial_root_label
        other_roots = [r for r in self.roots if r != life_node]
        for r in other_roots:
            life_node.add_child(r)
            self.roots.remove(r)
        
        # Ensure roots only contains the main label
        self.roots = [life_node]

    def save(self):
        data = [r.to_dict() for r in self.roots]
        try:
             with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"NodeService: Failed to save tree data: {e}")

    def push_state(self):
        self.undo_stack.append([r.to_dict() for r in self.roots])
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return False
            
        self.redo_stack.append([r.to_dict() for r in self.roots])
        previous_state = self.undo_stack.pop()
        self.roots = [Node.from_dict(d) for d in previous_state]
        self.save()
        return True

    def redo(self):
        if not self.redo_stack:
            return False
            
        self.undo_stack.append([r.to_dict() for r in self.roots])
        next_state = self.redo_stack.pop()
        self.roots = [Node.from_dict(d) for d in next_state]
        self.save()
        return True

    def add_root_node(self, label, x, y):
        self.push_state()
        life_node = next((r for r in self.roots if r.label == self.initial_root_label), None)
        if life_node:
            new_node = Node(label)
            new_node.x = x
            new_node.y = y
            life_node.add_child(new_node)
            self.save()
            return new_node
        
        new_node = Node(label)
        new_node.x = x
        new_node.y = y
        self.roots.append(new_node)
        self.save()
        return new_node

    def add_child_node(self, parent_node, label):
        self.push_state()
        new_node = Node(label)
        new_node.x = parent_node.x
        new_node.y = parent_node.y + 50
        parent_node.add_child(new_node)
        self.save()
        return new_node

    def rename_node(self, node, new_label):
        if node.label == self.initial_root_label:
            return False
        self.push_state()
        node.label = new_label
        self.save()
        return True

    def update_node_status(self, node, status):
        self.push_state()
        node.status = status
        self.save()
        return True

    def reparent_node(self, child_node, new_parent):
        if child_node == new_parent:
            return False

        ancestor = new_parent
        while ancestor:
            if ancestor == child_node:
                return False
            ancestor = ancestor.parent
            
        self.push_state()
        if child_node.parent:
            if child_node in child_node.parent.children:
                child_node.parent.children.remove(child_node)
        elif child_node in self.roots:
            self.roots.remove(child_node)
            
        new_parent.add_child(child_node)
        self.save()
        return True

    def _get_node_total_stats(self, node):
        """Calculate total stats for a node including intentions, archived_stats, and all children."""
        totals = {"time": 0, "words": 0, "chars": 0}
        
        # Add archived stats
        archived = getattr(node, 'archived_stats', {"time": 0, "words": 0, "chars": 0})
        totals["time"] += archived.get("time", 0)
        totals["words"] += archived.get("words", 0)
        totals["chars"] += archived.get("chars", 0)
        
        # Add stats from active intentions
        for intention in getattr(node, 'intentions', []):
            stats = intention.get("stats", {})
            totals["time"] += stats.get("time", 0)
            totals["words"] += stats.get("words", 0)
            totals["chars"] += stats.get("chars", 0)
        
        # Recursively add children stats
        for child in node.children:
            child_stats = self._get_node_total_stats(child)
            totals["time"] += child_stats["time"]
            totals["words"] += child_stats["words"]
            totals["chars"] += child_stats["chars"]
        
        return totals

    def _archive_stats_to_parent(self, node):
        """Archive node's total stats to its parent before deletion."""
        if not node.parent:
            return
            
        # Get total stats from this node and all its children
        total_stats = self._get_node_total_stats(node)
        
        # Ensure parent has archived_stats
        if not hasattr(node.parent, 'archived_stats'):
            node.parent.archived_stats = {"time": 0, "words": 0, "chars": 0}
        
        # Add to parent's archived stats
        node.parent.archived_stats["time"] += total_stats["time"]
        node.parent.archived_stats["words"] += total_stats["words"]
        node.parent.archived_stats["chars"] += total_stats["chars"]

    def delete_nodes(self, nodes):
        if not nodes:
            return False
            
        self.push_state()
        nodes_deleted = False
        for node in nodes:
            if node.label == self.initial_root_label:
                continue
            if node.parent:
                # Archive stats to parent before deletion
                self._archive_stats_to_parent(node)
                node.delete()
                nodes_deleted = True
            elif node in self.roots:
                self.roots.remove(node)
                nodes_deleted = True
        
        if nodes_deleted:
            self.save()
            return True
        return False

    def delete_nodes_keep_children(self, nodes):
        if not nodes:
            return False
            
        self.push_state()
        nodes_deleted = False
        for node in nodes:
            if node.label == self.initial_root_label:
                continue
            if node.parent:
                # Archive only this node's stats (not children's since they're kept)
                node_own_stats = {"time": 0, "words": 0, "chars": 0}
                
                # Add archived stats
                archived = getattr(node, 'archived_stats', {"time": 0, "words": 0, "chars": 0})
                node_own_stats["time"] += archived.get("time", 0)
                node_own_stats["words"] += archived.get("words", 0)
                node_own_stats["chars"] += archived.get("chars", 0)
                
                # Add stats from intentions
                for intention in getattr(node, 'intentions', []):
                    stats = intention.get("stats", {})
                    node_own_stats["time"] += stats.get("time", 0)
                    node_own_stats["words"] += stats.get("words", 0)
                    node_own_stats["chars"] += stats.get("chars", 0)
                
                # Archive to parent
                if not hasattr(node.parent, 'archived_stats'):
                    node.parent.archived_stats = {"time": 0, "words": 0, "chars": 0}
                node.parent.archived_stats["time"] += node_own_stats["time"]
                node.parent.archived_stats["words"] += node_own_stats["words"]
                node.parent.archived_stats["chars"] += node_own_stats["chars"]
                
                node.delete_keep_children()
                nodes_deleted = True
            elif node in self.roots:
                index = self.roots.index(node)
                self.roots.remove(node)
                for child in reversed(node.children):
                    child.parent = None
                    self.roots.insert(index, child)
                nodes_deleted = True
        
        if nodes_deleted:
            self.save()
            return True
        return False

    def get_all_nodes(self):
        """Returns a flat list of all nodes in all roots."""
        all_nodes = []
        def _collect(n):
            all_nodes.append(n)
            for c in n.children:
                _collect(c)
        for r in self.roots:
            _collect(r)
        return all_nodes
