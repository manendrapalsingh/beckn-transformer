"""AST Filler for filling AST with backend data."""

from typing import Dict, Any, List
from src.models.ast_node import ASTNode, NodeType
from src.builders.ast_builder import SchemaASTBuilder


class ASTFiller:
    """Fills AST with data from backend flat key-value pairs."""
    
    @staticmethod
    def _is_empty_value(value: Any) -> bool:
        """
        Check if a value is considered empty.
        
        Args:
            value: Value to check
            
        Returns:
            True if value is empty, False otherwise
        """
        if value is None:
            return True
        if isinstance(value, str) and value == "":
            return True
        if isinstance(value, dict) and len(value) == 0:
            return True
        if isinstance(value, list) and len(value) == 0:
            return True
        return False
    
    @staticmethod
    def fill_ast(ast_root: ASTNode, flat_data: Dict[str, Any]) -> ASTNode:
        """
        Recursively fill AST with flat backend data.
        
        Uses O(1) path index lookup when available.
        
        Args:
            ast_root: Root AST node
            flat_data: Flat key-value pairs from backend
            
        Returns:
            Filled AST root
        """
        for key_path, value in flat_data.items():
            # Skip empty values
            if ASTFiller._is_empty_value(value):
                continue
            
            # O(1) lookup using path index (falls back to O(N) if index not built)
            node = ast_root.get_node_by_path(key_path)
            
            if node:
                # Fill the node
                ASTFiller._fill_node_recursive(node, value, flat_data)
            else:
                # Try to create node if it doesn't exist (for dynamic fields)
                ASTFiller._create_and_fill_node(ast_root, key_path, value)
        
        return ast_root
    
    @staticmethod
    def _fill_node_recursive(node: ASTNode, value: Any, flat_data: Dict[str, Any]):
        """
        Recursively fill a node and its children.
        
        Args:
            node: Node to fill
            value: Value to fill
            flat_data: Full flat data dictionary
        """
        if node.node_type == NodeType.LEAF or node.node_type == NodeType.VALUE:
            node.fill_value(value)
        elif node.node_type == NodeType.OBJECT:
            # For objects, check if value is a dict and fill children
            if isinstance(value, dict):
                for child_key, child_value in value.items():
                    if child_key in node.children:
                        ASTFiller._fill_node_recursive(
                            node.children[child_key], child_value, flat_data
                        )
            else:
                # Store value directly if not a dict
                node.fill_value(value)
        elif node.node_type == NodeType.ARRAY:
            # Handle array filling
            if isinstance(value, list):
                # Clear existing items and create new ones
                node.array_items = []
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        # Create object node for array item
                        item_node = ASTNode(
                            key=f"{node.key}[{i}]",
                            node_type=NodeType.OBJECT,
                            path=f"{node.path}[{i}]",
                            parent=node,
                            schema_value=item
                        )
                        # Build children from item
                        for child_key, child_value in item.items():
                            child_node = SchemaASTBuilder._build_node(
                                child_key, child_value, item_node, item_node.path
                            )
                            item_node.children[child_key] = child_node
                        node.array_items.append(item_node)
                    else:
                        # Simple value
                        item_node = ASTNode(
                            key=f"{node.key}[{i}]",
                            node_type=NodeType.VALUE,
                            path=f"{node.path}[{i}]",
                            parent=node,
                            value=item
                        )
                        node.array_items.append(item_node)
            else:
                node.fill_value(value)
    
    @staticmethod
    def _create_and_fill_node(root: ASTNode, key_path: str, value: Any):
        """
        Create a node dynamically if it doesn't exist in AST.
        
        Args:
            root: Root AST node
            key_path: Dot-notation path (e.g., "context.version")
            value: Value to fill
        """
        keys = ASTFiller._parse_key_path(key_path)
        current = root
        
        for i, key in enumerate(keys):
            # Handle array indices
            if '[' in key and key.endswith(']'):
                base_key, index_str = key.rsplit('[', 1)
                index = int(index_str.rstrip(']'))
                
                if base_key not in current.children:
                    # Create array node
                    array_node = ASTNode(
                        key=base_key,
                        node_type=NodeType.ARRAY,
                        path=f"{current.path}.{base_key}" if current.path else base_key,
                        parent=current
                    )
                    current.children[base_key] = array_node
                
                array_node = current.children[base_key]
                # Ensure array is large enough
                while len(array_node.array_items) <= index:
                    item_node = ASTNode(
                        key=f"{base_key}[{len(array_node.array_items)}]",
                        node_type=NodeType.VALUE,
                        path=f"{array_node.path}[{len(array_node.array_items)}]",
                        parent=array_node
                    )
                    array_node.array_items.append(item_node)
                
                current = array_node.array_items[index]
            else:
                if key not in current.children:
                    # Determine node type
                    is_last = (i == len(keys) - 1)
                    node_type = NodeType.LEAF if is_last else NodeType.OBJECT
                    
                    new_node = ASTNode(
                        key=key,
                        node_type=node_type,
                        path=f"{current.path}.{key}" if current.path else key,
                        parent=current
                    )
                    current.children[key] = new_node
                
                current = current.children[key]
        
        # Fill the final node
        current.fill_value(value)
    
    @staticmethod
    def _parse_key_path(key: str) -> List[str]:
        """
        Parse a key path, handling array indices and special characters.
        
        Examples:
            "context.version" -> ["context", "version"]
            "message.support.channels[0]" -> ["message", "support", "channels[0]"]
            "message.order.beckn:buyer.beckn:id" -> ["message", "order", "beckn:buyer", "beckn:id"]
        
        Args:
            key: Key path string
            
        Returns:
            List of key parts
        """
        # Split by dots, but preserve array indices
        parts = []
        current = ""
        bracket_depth = 0
        
        for char in key:
            if char == '[':
                bracket_depth += 1
                current += char
            elif char == ']':
                bracket_depth -= 1
                current += char
            elif char == '.' and bracket_depth == 0:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
        
        if current:
            parts.append(current)
        
        return parts if parts else [key]

