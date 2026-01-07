"""AST Node model for schema representation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional


class NodeType(Enum):
    """Types of AST nodes."""
    OBJECT = "object"
    ARRAY = "array"
    LEAF = "leaf"
    VALUE = "value"


@dataclass
class ASTNode:
    """
    Abstract Syntax Tree node representing a schema structure.
    Each node knows its key placement and can be filled with data.
    
    Performance optimizations:
    - _path_index: O(1) lookup by path (built once, reused)
    - _has_value_cache: Memoized has_value() result
    """
    key: str  # The key name (e.g., "version", "support", "channels")
    node_type: NodeType  # Type of node
    path: str  # Full path from root (e.g., "context.version", "message.support.name")
    value: Any = None  # Value (filled from backend data)
    children: Dict[str, 'ASTNode'] = field(default_factory=dict)  # Child nodes for objects
    array_items: List['ASTNode'] = field(default_factory=list)  # Items for arrays
    parent: Optional['ASTNode'] = None  # Parent node reference
    schema_value: Any = None  # Default value from schema (for structure preservation)
    is_required: bool = False  # Whether this field is required
    
    # Performance optimization fields (not serialized)
    _path_index: Dict[str, 'ASTNode'] = field(default_factory=dict, repr=False)
    _has_value_cache: Optional[bool] = field(default=None, repr=False)
    
    def get_full_path(self) -> str:
        """Get the full dot-notation path for this node."""
        if self.parent is None:
            return self.key
        parent_path = self.parent.get_full_path()
        if parent_path:
            return f"{parent_path}.{self.key}"
        return self.key
    
    def build_path_index(self, index: Optional[Dict[str, 'ASTNode']] = None) -> Dict[str, 'ASTNode']:
        """
        Build a path index for O(1) node lookups.
        
        Args:
            index: Existing index to add to (for recursive calls)
            
        Returns:
            Dictionary mapping paths to nodes
        """
        if index is None:
            index = {}
            self._path_index = index
        
        # Add this node to index
        full_path = self.path
        if full_path:
            index[full_path] = self
        
        # Index all children
        for child in self.children.values():
            child.build_path_index(index)
            child._path_index = index  # Share index with children
        
        # Index all array items
        for item in self.array_items:
            item.build_path_index(index)
            item._path_index = index  # Share index with items
        
        return index
    
    def get_node_by_path(self, path: str) -> Optional['ASTNode']:
        """
        Get a node by path using O(1) index lookup.
        
        Falls back to tree traversal if index not built.
        
        Args:
            path: Dot-notation path (e.g., "context.version")
            
        Returns:
            ASTNode if found, None otherwise
        """
        # Try O(1) index lookup first
        if self._path_index:
            return self._path_index.get(path)
        
        # Fallback to O(N) traversal if index not built
        return self.find_node_by_path(path)
    
    def has_value(self) -> bool:
        """
        Check if node has a valid (non-empty) value.
        
        Uses memoization for O(1) repeated calls.
        
        Returns:
            True if node has a valid value, False otherwise
        """
        # Return cached result if available
        if self._has_value_cache is not None:
            return self._has_value_cache
        
        # Compute result
        result = self._compute_has_value()
        
        # Cache the result
        self._has_value_cache = result
        return result
    
    def _compute_has_value(self) -> bool:
        """Compute has_value without caching (internal use)."""
        if self.node_type == NodeType.OBJECT:
            # Object has value if any child has value
            return any(child.has_value() for child in self.children.values())
        elif self.node_type == NodeType.ARRAY:
            # Array has value if it has any items with values
            return len(self.array_items) > 0 and any(item.has_value() for item in self.array_items)
        else:
            # Leaf or value node - check if value is not empty
            if self.value is None:
                return False
            if isinstance(self.value, str) and self.value == "":
                return False
            if isinstance(self.value, dict) and len(self.value) == 0:
                return False
            if isinstance(self.value, list) and len(self.value) == 0:
                return False
            return True
    
    def invalidate_cache(self):
        """
        Invalidate the has_value cache for this node and all ancestors.
        
        Called when a value is modified to ensure cache consistency.
        """
        self._has_value_cache = None
        
        # Invalidate parent caches up to root
        if self.parent is not None:
            self.parent.invalidate_cache()
    
    def to_dict(self) -> Any:
        """
        Convert AST node to dictionary/JSON structure.
        Only includes keys with actual values (skips empty values).
        
        Returns:
            Dictionary, list, or value representing the node structure
        """
        if self.node_type == NodeType.OBJECT:
            result = {}
            for child_key, child_node in self.children.items():
                if child_node.has_value():
                    result[child_key] = child_node.to_dict()
            # Return None if object is empty (will be filtered out)
            return result if result else None
        elif self.node_type == NodeType.ARRAY:
            result = []
            for item in self.array_items:
                if item.has_value():
                    item_dict = item.to_dict()
                    if item_dict is not None:
                        result.append(item_dict)
            # Return None if array is empty (will be filtered out)
            return result if result else None
        else:
            # Leaf or value node - return value if it's not empty
            if self.has_value():
                return self.value
            return None
    
    def find_node_by_path(self, path: str) -> Optional['ASTNode']:
        """
        Find a node by its dot-notation path (O(N) traversal).
        
        Prefer get_node_by_path() for O(1) lookup when index is built.
        
        Args:
            path: Dot-notation path (e.g., "context.version")
            
        Returns:
            ASTNode if found, None otherwise
        """
        if self.path == path:
            return self
        
        # Search in children
        for child in self.children.values():
            found = child.find_node_by_path(path)
            if found:
                return found
        
        # Search in array items
        for item in self.array_items:
            found = item.find_node_by_path(path)
            if found:
                return found
        
        return None
    
    def fill_value(self, value: Any):
        """
        Fill the node with a value from backend data.
        
        Invalidates has_value cache for this node and ancestors.
        
        Args:
            value: Value to fill
        """
        self.value = value
        self.invalidate_cache()
    
    def to_serializable(self) -> Dict[str, Any]:
        """
        Convert AST node to a JSON-serializable dictionary.
        
        Used for disk persistence in cache/asts/.
        
        Returns:
            JSON-serializable dictionary representation
        """
        data = {
            "key": self.key,
            "node_type": self.node_type.value,
            "path": self.path,
            "value": self.value,
            "schema_value": self.schema_value,
            "is_required": self.is_required,
        }
        
        # Serialize children
        if self.children:
            data["children"] = {
                k: v.to_serializable() for k, v in self.children.items()
            }
        
        # Serialize array items
        if self.array_items:
            data["array_items"] = [
                item.to_serializable() for item in self.array_items
            ]
        
        return data
    
    @classmethod
    def from_serializable(cls, data: Dict[str, Any], parent: Optional['ASTNode'] = None) -> 'ASTNode':
        """
        Reconstruct an AST node from a serialized dictionary.
        
        Args:
            data: Serialized node data
            parent: Parent node (for setting parent reference)
            
        Returns:
            Reconstructed ASTNode
        """
        node = cls(
            key=data["key"],
            node_type=NodeType(data["node_type"]),
            path=data["path"],
            value=data.get("value"),
            schema_value=data.get("schema_value"),
            is_required=data.get("is_required", False),
            parent=parent,
        )
        
        # Reconstruct children
        if "children" in data:
            for child_key, child_data in data["children"].items():
                child_node = cls.from_serializable(child_data, parent=node)
                node.children[child_key] = child_node
        
        # Reconstruct array items
        if "array_items" in data:
            for item_data in data["array_items"]:
                item_node = cls.from_serializable(item_data, parent=node)
                node.array_items.append(item_node)
        
        return node
