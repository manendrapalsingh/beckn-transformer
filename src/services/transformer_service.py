"""Schema Transformer Service - Main transformation orchestration."""

import json
import hashlib
from typing import Dict, Any, Optional, List
from pathlib import Path
from src.fetchers.github_fetcher import GitHubSchemaFetcher
from src.builders.ast_builder import SchemaASTBuilder
from src.processors.ast_filler import ASTFiller
from src.models.ast_node import ASTNode


class SchemaTransformerService:
    """Service that orchestrates schema fetching, AST building, and transformation."""
    
    def __init__(self, repo_owner: str = "bhim", repo_name: str = "ubc-tsd", 
                 branch: str = "main", schema_path: str = "Example-schemas",
                 cache_dir: str = "cache"):
        """
        Initialize the transformer service.
        
        Args:
            repo_owner: GitHub repo owner
            repo_name: GitHub repo name
            branch: Branch name
            schema_path: Path to schemas in repo
            cache_dir: Directory for caching schemas and ASTs
        """
        self.fetcher = GitHubSchemaFetcher(repo_owner, repo_name, branch, schema_path)
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.asts: Dict[str, ASTNode] = {}  # Cache of ASTs by schema name
        self.schema_index: Dict[str, List[str]] = {}  # Index by action for quick lookup
        
        # Cache directories
        self.cache_dir = Path(cache_dir)
        self.ast_cache_dir = self.cache_dir / "asts"
        self.ast_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_schema_hash(self, schema: Dict[str, Any]) -> str:
        """
        Get a hash of a schema for cache validation.
        
        Args:
            schema: Schema dictionary
            
        Returns:
            MD5 hash of the schema
        """
        schema_str = json.dumps(schema, sort_keys=True)
        return hashlib.md5(schema_str.encode()).hexdigest()
    
    def _save_ast_to_cache(self, name: str, ast_root: ASTNode, schema_hash: str):
        """
        Serialize and save AST to cache directory.
        
        Args:
            name: Schema name
            ast_root: Root AST node
            schema_hash: Hash of source schema for validation
        """
        cache_file = self.ast_cache_dir / f"{name}.json"
        try:
            cache_data = {
                "schema_hash": schema_hash,
                "ast": ast_root.to_serializable()
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            print(f"  ⚠️  Failed to cache AST for {name}: {e}")
    
    def _load_ast_from_cache(self, name: str, schema_hash: str) -> Optional[ASTNode]:
        """
        Load AST from cache if exists and schema unchanged.
        
        Args:
            name: Schema name
            schema_hash: Current schema hash for validation
            
        Returns:
            Cached ASTNode if valid, None otherwise
        """
        cache_file = self.ast_cache_dir / f"{name}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Validate schema hash
            if cache_data.get("schema_hash") != schema_hash:
                print(f"  ⚠️  Schema changed, rebuilding AST for: {name}")
                return None
            
            # Reconstruct AST from serialized data
            ast_root = ASTNode.from_serializable(cache_data["ast"])
            
            # Build path index for O(1) lookups
            ast_root.build_path_index()
            
            return ast_root
        except Exception as e:
            print(f"  ⚠️  Failed to load cached AST for {name}: {e}")
            return None
    
    def fetch_and_build_asts(self):
        """
        Fetch schemas from GitHub and build ASTs for each.
        
        Uses cached ASTs when available and schema unchanged.
        """
        print("🔄 Fetching schemas from GitHub...")
        self.schemas = self.fetcher.fetch_all_schemas()
        
        print(f"📦 Building ASTs for {len(self.schemas)} schemas...")
        self.asts = {}
        self.schema_index = {}
        
        cache_hits = 0
        cache_misses = 0
        
        for name, schema_info in self.schemas.items():
            try:
                schema = schema_info['schema']
                schema_hash = self._get_schema_hash(schema)
                
                # Try to load from cache first
                cached_ast = self._load_ast_from_cache(name, schema_hash)
                
                if cached_ast:
                    self.asts[name] = cached_ast
                    cache_hits += 1
                    print(f"  ✓ Loaded AST from cache: {name}")
                else:
                    # Build new AST
                    ast_root = SchemaASTBuilder.build_ast(schema, "root")
                    self.asts[name] = ast_root
                    cache_misses += 1
                    
                    # Save to cache for next time
                    self._save_ast_to_cache(name, ast_root, schema_hash)
                    print(f"  ✓ Built AST for: {name}")
                
                # Index by action if context.action exists
                if isinstance(schema, dict) and 'context' in schema:
                    action = schema.get('context', {}).get('action')
                    if action:
                        if action not in self.schema_index:
                            self.schema_index[action] = []
                        self.schema_index[action].append(name)
                
            except Exception as e:
                print(f"  ✗ Error building AST for {name}: {e}")
        
        print(f"✅ Loaded {len(self.asts)} ASTs (cache hits: {cache_hits}, built: {cache_misses})")
    
    def process_backend_data(self, flat_data: Dict[str, Any], 
                            schema_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Process backend flat data and convert to JSON using AST.
        
        Args:
            flat_data: Flat key-value pairs from backend
            schema_name: Optional schema name (auto-detected if not provided)
            
        Returns:
            Nested JSON structure
        """
        # Auto-detect schema from action
        if not schema_name:
            action = flat_data.get('context.action')
            if action and action in self.schema_index:
                # Use first matching schema
                schema_name = self.schema_index[action][0]
                print(f"Auto-detected schema: {schema_name} (action: {action})")
        
        if not schema_name or schema_name not in self.asts:
            print(f"⚠️  Schema '{schema_name}' not found. Using generic AST.")
            # Create generic AST from flat data structure
            ast_root = SchemaASTBuilder.build_ast(flat_data, "root")
        else:
            # Get AST from cache (create a copy to avoid modifying cached AST)
            ast_root = self._copy_ast(self.asts[schema_name])
        
        # Fill AST with backend data
        filled_ast = ASTFiller.fill_ast(ast_root, flat_data)
        
        # Convert AST to JSON
        result = filled_ast.to_dict()
        
        # Remove root wrapper if it exists and is empty
        if isinstance(result, dict):
            if "root" in result and len(result) == 1:
                root_value = result["root"]
                if isinstance(root_value, dict):
                    result = root_value
        
        # Filter out None values at top level
        if isinstance(result, dict):
            result = {k: v for k, v in result.items() if v is not None}
        
        return result
    
    def _copy_ast(self, node: ASTNode) -> ASTNode:
        """
        Create a deep copy of an AST node with path index.
        
        Optimized to rebuild path index after copying.
        
        Args:
            node: AST node to copy
            
        Returns:
            Copy of the AST node with path index
        """
        new_node = self._copy_ast_recursive(node)
        # Rebuild path index for O(1) lookups on the copy
        new_node.build_path_index()
        return new_node
    
    def _copy_ast_recursive(self, node: ASTNode) -> ASTNode:
        """
        Recursively copy an AST node without rebuilding index.
        
        Args:
            node: AST node to copy
            
        Returns:
            Copy of the AST node (without path index)
        """
        new_node = ASTNode(
            key=node.key,
            node_type=node.node_type,
            path=node.path,
            value=node.value,
            parent=None,  # Will be set by children
            schema_value=node.schema_value,
            is_required=node.is_required
        )
        
        # Copy children
        for child_key, child_node in node.children.items():
            child_copy = self._copy_ast_recursive(child_node)
            child_copy.parent = new_node
            new_node.children[child_key] = child_copy
        
        # Copy array items
        for item in node.array_items:
            item_copy = self._copy_ast_recursive(item)
            item_copy.parent = new_node
            new_node.array_items.append(item_copy)
        
        return new_node
    
    def clear_ast_cache(self):
        """Clear all cached AST files."""
        for cache_file in self.ast_cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except Exception as e:
                print(f"Failed to delete {cache_file}: {e}")
        print("🗑️  AST cache cleared")
    
    def get_schema_by_action(self, action: str) -> Optional[Dict[str, Any]]:
        """
        Get schema by action name.
        
        Args:
            action: The action name (e.g., 'support', 'init', 'confirm')
            
        Returns:
            Schema dictionary or None if not found
        """
        if action in self.schema_index and self.schema_index[action]:
            schema_name = self.schema_index[action][0]  # Use first match
            return self.schemas.get(schema_name, {}).get('schema')
        return None
    
    def get_schema_by_name(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """
        Get schema by name.
        
        Args:
            schema_name: Name of the schema file (without .json extension)
            
        Returns:
            Schema dictionary or None if not found
        """
        if schema_name in self.schemas:
            return self.schemas[schema_name]['schema']
        return None
    
    def list_available_schemas(self) -> List[str]:
        """
        List all available schema names.
        
        Returns:
            List of schema names
        """
        return list(self.schemas.keys())
    
    def list_available_actions(self) -> List[str]:
        """
        List all available actions.
        
        Returns:
            List of action names
        """
        return list(self.schema_index.keys())
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the AST cache.
        
        Returns:
            Dictionary with cache statistics
        """
        cache_files = list(self.ast_cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "cached_asts": len(cache_files),
            "total_size_bytes": total_size,
            "total_size_kb": round(total_size / 1024, 2),
            "cache_dir": str(self.ast_cache_dir)
        }
