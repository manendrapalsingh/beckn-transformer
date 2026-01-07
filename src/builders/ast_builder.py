"""AST Builder for creating AST from JSON schemas."""

from typing import Dict, Any, Optional
from src.models.ast_node import ASTNode, NodeType


class SchemaASTBuilder:
    """Builds AST from JSON schema structure."""
    
    @staticmethod
    def build_ast(schema: Dict[str, Any], root_key: str = "root") -> ASTNode:
        """
        Recursively build AST from schema.
        
        Builds path index after construction for O(1) lookups.
        
        Args:
            schema: JSON schema dictionary
            root_key: Root key name
            
        Returns:
            Root AST node with path index built
        """
        root = SchemaASTBuilder._build_node(root_key, schema, None, "")
        # Build path index for O(1) lookups
        root.build_path_index()
        return root
    
    @staticmethod
    def _build_node(key: str, value: Any, parent: Optional[ASTNode], path: str) -> ASTNode:
        """
        Recursively build a node from schema value.
        
        Args:
            key: Key name for this node
            value: Value from schema (dict, list, or primitive)
            parent: Parent node
            path: Current path string
            
        Returns:
            ASTNode representing this part of the schema
        """
        current_path = f"{path}.{key}" if path else key
        
        if isinstance(value, dict):
            node = ASTNode(
                key=key,
                node_type=NodeType.OBJECT,
                path=current_path,
                parent=parent,
                schema_value=value
            )
            
            # Build children
            for child_key, child_value in value.items():
                child_node = SchemaASTBuilder._build_node(
                    child_key, child_value, node, current_path
                )
                node.children[child_key] = child_node
            
            return node
        
        elif isinstance(value, list):
            node = ASTNode(
                key=key,
                node_type=NodeType.ARRAY,
                path=current_path,
                parent=parent,
                schema_value=value
            )
            
            # Build array item structure from first item (if exists)
            if value and isinstance(value[0], (dict, list)):
                # Create template node from first item
                template = value[0]
                if isinstance(template, dict):
                    item_node = SchemaASTBuilder._build_node(
                        f"{key}[0]", template, node, current_path
                    )
                else:
                    item_node = ASTNode(
                        key=f"{key}[0]",
                        node_type=NodeType.VALUE,
                        path=f"{current_path}[0]",
                        parent=node,
                        schema_value=template
                    )
                node.array_items.append(item_node)
            elif value:
                # Simple array of values - create nodes for each
                for i, item in enumerate(value):
                    item_node = ASTNode(
                        key=f"{key}[{i}]",
                        node_type=NodeType.VALUE,
                        path=f"{current_path}[{i}]",
                        parent=node,
                        schema_value=item
                    )
                    node.array_items.append(item_node)
            
            return node
        
        else:
            # Leaf node (primitive value)
            return ASTNode(
                key=key,
                node_type=NodeType.LEAF,
                path=current_path,
                parent=parent,
                schema_value=value
            )

