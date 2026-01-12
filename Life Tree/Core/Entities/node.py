import uuid

class Node:
    def __init__(self, label, uid=None, status="neutral", description=""):
        self.label = label
        self.uid = uid if uid else str(uuid.uuid4()) # Unique Identifier
        self.status = status # status: solved, solving, neutral
        self.description = description
        self.children = []
        self.intentions = [] # List of dicts: {"text": str, "status": str, "stats": dict}
        self.archived_stats = {"time": 0, "words": 0, "chars": 0} # Accumulated stats from cleared intentions/deleted children
        self.allowed_windows = [] # Whitelist for Deep Focus
        self.parent = None
        self.x = 0
        self.y = 0
        self.width = 100
        self.height = 40
        self.cycle_time = 0 # Seconds spent in current 8-hour cycle
        self.cycle_count = 0 # Number of completed 8-hour cycles

    def add_child(self, node):
        node.parent = self
        self.children.append(node)
        return node
        
    def delete(self):
        """Removes this node from its parent's list of children (recursive delete)."""
        if self.parent:
            if self in self.parent.children:
                self.parent.children.remove(self)
        else:
            print("Cannot delete root node or node with no parent!")

    def delete_keep_children(self):
        """Removes this node but promotes its children to the parent's level."""
        if self.parent:
            if self in self.parent.children:
                index = self.parent.children.index(self)
                self.parent.children.remove(self)
                # Insert children at the same position
                for child in reversed(self.children):
                    child.parent = self.parent
                    self.parent.children.insert(index, child)
        else:
             print("Cannot delete root node or node with no parent!")

    def translate(self, dx, dy):
        """Moves this node and all its descendants by dx, dy."""
        self.x += dx
        self.y += dy
        for child in self.children:
            child.translate(dx, dy)

    def to_dict(self):
        return {
            "label": self.label,
            "uid": self.uid,
            "status": self.status,
            "description": self.description,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "intentions": self.intentions,
            "archived_stats": self.archived_stats,
            "allowed_windows": self.allowed_windows,
            "cycle_time": self.cycle_time,
            "cycle_count": self.cycle_count,
            "children": [child.to_dict() for child in self.children]
        }

    @classmethod
    def from_dict(cls, data):
        node = cls(
            data.get("label", "Unknown"),
            uid=data.get("uid"),
            status=data.get("status", "neutral"),
            description=data.get("description", "")
        )
        node.intentions = data.get("intentions", [])
        node.archived_stats = data.get("archived_stats", {"time": 0, "words": 0, "chars": 0})
        node.allowed_windows = data.get("allowed_windows", [])
        node.x = data.get("x", 0)
        node.y = data.get("y", 0)
        node.width = data.get("width", 100)
        node.height = data.get("height", 40)
        node.cycle_time = data.get("cycle_time", 0)
        node.cycle_count = data.get("cycle_count", 0)
        for child_data in data.get("children", []):
            child_node = cls.from_dict(child_data)
            node.add_child(child_node)
        return node
