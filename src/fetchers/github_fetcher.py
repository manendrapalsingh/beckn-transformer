"""GitHub Schema Fetcher for fetching schemas from GitHub repository."""

import json
import os
from pathlib import Path
from typing import Dict, Any, List
import requests


class GitHubSchemaFetcher:
    """Fetches schemas from GitHub repository."""
    
    def __init__(self, repo_owner: str, repo_name: str, branch: str = "main", 
                 schema_path: str = "Example-schemas"):
        """
        Initialize GitHub fetcher.
        
        Args:
            repo_owner: GitHub repository owner (e.g., "bhim")
            repo_name: Repository name (e.g., "ubc-tsd")
            branch: Branch name (default: "main")
            schema_path: Path to schemas in repo (default: "Example-schemas")
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.schema_path = schema_path
        self.base_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}"
        self.local_cache_dir = Path("cache/schemas")
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch_all_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch all JSON schema files from GitHub.
        
        Returns:
            Dictionary mapping schema names to schema data
        """
        schemas = {}
        
        # Get list of files from GitHub API
        api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/{self.schema_path}"
        
        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            contents = response.json()
            
            # Recursively fetch all JSON files
            schemas = self._fetch_recursive(contents, self.schema_path)
            
            # Cache schemas locally
            self._cache_schemas(schemas)
            
            print(f"✓ Fetched {len(schemas)} schemas from GitHub")
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Error fetching from GitHub: {e}")
            print("Falling back to local cache...")
            schemas = self._load_from_cache()
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            print("Falling back to local cache...")
            schemas = self._load_from_cache()
        
        return schemas
    
    def _fetch_recursive(self, contents: List[Dict], current_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Recursively fetch JSON files from GitHub.
        
        Args:
            contents: List of file/directory items from GitHub API
            current_path: Current path in repository
            
        Returns:
            Dictionary of schemas
        """
        schemas = {}
        
        for item in contents:
            if item['type'] == 'file' and item['name'].endswith('.json'):
                # Fetch JSON file
                file_url = f"{self.base_url}/{item['path']}"
                try:
                    response = requests.get(file_url, timeout=30)
                    response.raise_for_status()
                    schema_data = response.json()
                    schema_name = Path(item['name']).stem
                    schemas[schema_name] = {
                        'schema': schema_data,
                        'path': item['path'],
                        'name': schema_name
                    }
                    print(f"  ✓ Fetched: {item['path']}")
                except Exception as e:
                    print(f"  ✗ Error fetching {item['path']}: {e}")
            
            elif item['type'] == 'dir':
                # Recursively fetch from subdirectory
                sub_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/{item['path']}"
                try:
                    sub_response = requests.get(sub_url, timeout=30)
                    sub_response.raise_for_status()
                    sub_contents = sub_response.json()
                    sub_schemas = self._fetch_recursive(sub_contents, item['path'])
                    schemas.update(sub_schemas)
                except Exception as e:
                    print(f"  ✗ Error fetching directory {item['path']}: {e}")
        
        return schemas
    
    def _cache_schemas(self, schemas: Dict[str, Dict[str, Any]]):
        """
        Cache schemas locally.
        
        Args:
            schemas: Dictionary of schemas to cache
        """
        for name, schema_info in schemas.items():
            cache_file = self.local_cache_dir / f"{name}.json"
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(schema_info, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"  ✗ Error caching {name}: {e}")
    
    def _load_from_cache(self) -> Dict[str, Dict[str, Any]]:
        """
        Load schemas from local cache.
        
        Returns:
            Dictionary of cached schemas
        """
        schemas = {}
        if not self.local_cache_dir.exists():
            print(f"  ⚠ Cache directory does not exist: {self.local_cache_dir}")
            return schemas
        
        for cache_file in self.local_cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    schema_info = json.load(f)
                    schemas[schema_info['name']] = schema_info
            except Exception as e:
                print(f"  ✗ Error loading cache {cache_file}: {e}")
        
        print(f"  ✓ Loaded {len(schemas)} schemas from cache")
        return schemas

