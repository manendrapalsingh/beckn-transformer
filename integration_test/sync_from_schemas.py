"""Sync integration test payloads from cached schemas (flat structure)."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
# Schemas are stored flat in cache/schemas/
SCHEMAS_DIR = ROOT / "cache" / "schemas"
REQUEST_DIR = ROOT / "integration_test" / "request_payloads"
RESPONSE_DIR = ROOT / "integration_test" / "responses"


def flatten(obj: Any, prefix: str = "") -> Dict[str, Any]:
    """Flatten nested dict/list into dotted keys."""
    items: Dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            items.update(flatten(v, new_prefix))
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            new_prefix = f"{prefix}[{idx}]"
            items.update(flatten(v, new_prefix))
    else:
        items[prefix] = obj
    return items


def slugify(name: str) -> str:
    """Safe slug for filenames."""
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", name)


def get_action_from_schema(schema: Dict[str, Any], filename: str) -> str:
    """Extract action from schema's context.action or infer from filename."""
    # Try to get from context.action
    if "context" in schema and "action" in schema["context"]:
        return schema["context"]["action"]
    
    # Infer from filename patterns
    filename_lower = filename.lower()
    
    # on_* actions (check these first as they're more specific)
    if "on_discover" in filename_lower:
        return "on_discover"
    if "on_select" in filename_lower:
        return "on_select"
    if "on_init" in filename_lower or "on-init" in filename_lower:
        return "on_init"
    if "on_confirm" in filename_lower:
        return "on_confirm"
    if "on_update" in filename_lower:
        return "on_update"
    if "on_track" in filename_lower:
        return "on_track"
    if "on_status" in filename_lower:
        return "on_status"
    if "on_rating" in filename_lower:
        return "on_rating"
    if "on_support" in filename_lower:
        return "on_support"
    if "on_cancel" in filename_lower or "cancels" in filename_lower:
        return "on_cancel"
    if "on_publish" in filename_lower:
        return "on_publish"
    
    # Base actions
    if "discover" in filename_lower:
        return "discover"
    if "select" in filename_lower:
        return "select"
    if "init" in filename_lower:
        return "init"
    if "confirm" in filename_lower:
        return "confirm"
    if "update" in filename_lower:
        return "update"
    if "track" in filename_lower:
        return "track"
    if "status" in filename_lower:
        return "status"
    if "rating" in filename_lower:
        return "rating"
    if "support" in filename_lower:
        return "support"
    if "cancel" in filename_lower:
        return "cancel"
    if "publish" in filename_lower:
        return "publish"
    if "catalog" in filename_lower:
        return "publish"
    
    return "unknown"


def main():
    REQUEST_DIR.mkdir(parents=True, exist_ok=True)
    RESPONSE_DIR.mkdir(parents=True, exist_ok=True)

    if not SCHEMAS_DIR.exists():
        print(f"❌ Schemas directory not found: {SCHEMAS_DIR}")
        print("   Make sure schemas are cached (start the API server first).")
        return

    schema_files = list(SCHEMAS_DIR.glob("*.json"))
    if not schema_files:
        print(f"❌ No JSON files found in {SCHEMAS_DIR}")
        return

    print(f"Found {len(schema_files)} schema files in {SCHEMAS_DIR}\n")

    # Group schemas by action
    schemas_by_action: Dict[str, List[tuple]] = defaultdict(list)

    for schema_path in sorted(schema_files):
        try:
            with open(schema_path, "r") as f:
                schema = json.load(f)
        except json.JSONDecodeError as e:
            print(f"⚠️  Skipping invalid JSON: {schema_path.name} - {e}")
            continue

        action = get_action_from_schema(schema, schema_path.name)
        schemas_by_action[action].append((schema_path, schema))

    # Generate test cases for each action
    total_generated = 0
    for action in sorted(schemas_by_action.keys()):
        schemas = schemas_by_action[action]
        print(f"\n📁 Action: {action} ({len(schemas)} schema(s))")

        for schema_path, schema in schemas:
            case_slug = slugify(schema_path.stem)
            
            # Use simpler name if only one schema for this action
            if len(schemas) == 1:
                req_name = f"transform_{action}.json"
                resp_name = f"transform_{action}.json"
            else:
                req_name = f"transform_{action}_{case_slug}.json"
                resp_name = f"transform_{action}_{case_slug}.json"

            # Create request payload (flattened data)
            flat = flatten(schema)
            request_payload = {
                "method": "POST",
                "endpoint": "/transform",
                "headers": {"Content-Type": "application/json"},
                "body": {"data": flat},
            }

            req_file = REQUEST_DIR / req_name
            with open(req_file, "w") as f:
                json.dump(request_payload, f, indent=2, ensure_ascii=False)

            # Create expected response (nested structure)
            resp_payload = {
                "result": schema,
                "schema_used": schema_path.stem,
            }
            resp_file = RESPONSE_DIR / resp_name
            with open(resp_file, "w") as f:
                json.dump(resp_payload, f, indent=2, ensure_ascii=False)

            print(f"   ✓ {schema_path.name} → {req_name}")
            total_generated += 1

    print(f"\n✅ Generated {total_generated} test case(s)")
    print(f"   Requests:  {REQUEST_DIR}")
    print(f"   Responses: {RESPONSE_DIR}")


if __name__ == "__main__":
    main()
