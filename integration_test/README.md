# Integration Test Suite for Schema Transformer API

This directory contains integration tests for all API actions in the Schema Transformer service.

## Overview

The integration test suite includes:
- **Multiple test cases** per action (one per schema variant)
- Request payloads in `request_payloads/` directory
- Expected response payloads in `responses/` directory
- Test runner script (`test_integration.py`)
- Schema sync script (`sync_from_schemas.py`)
- Response template generator (`generate_response_templates.py`)

## Quick Start

```bash
# From project root
make test              # Run all tests
make test-strict       # Run in strict mode
make sync-schemas      # Sync from cached schemas
make generate-responses # Generate expected responses
```

Or manually:

```bash
cd integration_test
source ../venv/bin/activate
python test_integration.py
```

## Test Cases

### Core API Endpoints
- `health_check` - GET /health
- `list_schemas` - GET /schemas
- `refresh_schemas` - POST /refresh-schemas
- `get_schema` - GET /schemas/{schema_name}

### Transform Actions (Multiple Variants)

Each action may have multiple test cases based on schema variants:

| Action | Example Test Cases |
|--------|-------------------|
| `discover` | `transform_discover_discovery-by-QR`, `transform_discover_discovery-within-a-circular-boundary`, etc. |
| `on_discover` | `transform_on_discover` |
| `select` | `transform_select` |
| `on_select` | `transform_on_select` |
| `init` | `transform_init_ev-charging-init-bap`, `transform_init_ev-charging-init-bpp` |
| `on_init` | `transform_on_init_ev-charging-on-init-bap`, `transform_on_init_ev-charging-on_init-bpp` |
| `confirm` | `transform_confirm` |
| `on_confirm` | `transform_on_confirm` |
| `update` | `transform_update_ev-charging-start-update`, `transform_update_ev-charging-stop-update` |
| `on_update` | `transform_on_update_ev-charging-start-on_update`, `transform_on_update_ev-charging-completed-on_update` |
| `track` | `transform_track` |
| `on_track` | `transform_on_track` |
| `on_status` | `transform_on_status_ev-charging-session-interupt-on_status`, etc. |
| `rating` | `transform_rating` |
| `on_rating` | `transform_on_rating` |
| `support` | `transform_support` |
| `on_support` | `transform_on_support` |
| `cancel` | `transform_cancel` |
| `on_cancel` | `transform_on_cancel` |
| `publish` | `transform_publish` |
| `on_publish` | `transform_on_publish` |

### Edge Cases
- `transform_with_empty_values` - Tests value filtering (empty strings, null, empty arrays/dicts)

## Using Makefile Commands

From the project root directory:

```bash
# Run all tests
make test

# Run tests in strict mode (fail on any differences)
make test-strict

# View cache statistics (schemas + ASTs)
make cache-stats

# Clear AST cache (force rebuild on next start)
make clean-ast-cache

# Run a specific test
make test-single T=transform_support

# Run tests and save results
make test-save

# Sync test payloads from cached schemas
make sync-schemas

# Generate expected responses from API (server must be running)
make generate-responses
```

## Manual Usage

### Prerequisites

1. **Activate the virtual environment**:
   ```bash
   source ../venv/bin/activate
   ```
   
   Or use the venv's Python directly:
   ```bash
   ../venv/bin/python3 test_integration.py
   ```

2. **Ensure the API server is running**:
   ```bash
   # From project root
   make run
   # Or manually:
   python -m src.main
   ```

3. The server should be accessible at `http://localhost:8000` (or configure with `--url`)

### Running Tests

#### Run All Tests

```bash
cd integration_test
python test_integration.py
```

#### Run Specific Test

```bash
python test_integration.py --test transform_support
```

#### Run in Strict Mode

Strict mode fails tests if there are any differences between actual and expected responses:

```bash
python test_integration.py --strict
```

#### Save Results to File

```bash
python test_integration.py --save
```

This creates `test_results.json` with detailed test results.

#### Custom API URL

```bash
python test_integration.py --url http://localhost:8080
```

## Syncing Test Payloads from Schemas

The `sync_from_schemas.py` script generates request/response pairs from cached schemas:

```bash
# Using Makefile
make sync-schemas

# Or manually
cd integration_test
python sync_from_schemas.py
```

This script:
1. Reads all schemas from `cache/schemas/`
2. Detects the action from `context.action` or filename
3. Generates request payloads (flattened data) in `request_payloads/`
4. Generates expected responses (nested structure) in `responses/`
5. Creates multiple test cases per action when multiple schema variants exist

## Generating Response Templates

To generate expected response files from actual API responses:

```bash
# Using Makefile (API must be running)
make generate-responses

# Or manually
cd integration_test
python generate_response_templates.py
```

Or with custom URL:

```bash
python generate_response_templates.py http://localhost:8080
```

This will:
1. Read all request files from `request_payloads/` directory
2. Make actual API calls
3. Save responses to `responses/` directory
4. Handle errors gracefully

**Note**: This is useful for initial setup or when updating expected responses after API changes.

## Adding New Test Cases

### Option 1: Add Schema and Sync

1. Add the new schema to `cache/schemas/`
2. Run sync:
   ```bash
   make sync-schemas
   ```
3. Generate expected responses:
   ```bash
   make generate-responses
   ```

### Option 2: Manual Creation

1. Create a new request file in `request_payloads/` directory:
   ```json
   {
     "method": "POST",
     "endpoint": "/transform",
     "headers": {
       "Content-Type": "application/json"
     },
     "body": {
       "data": {
         "context.version": "2.0.0",
         "context.action": "your_action",
         "context.domain": "your_domain",
         "message.field": "value"
       }
     }
   }
   ```

2. Generate expected response:
   ```bash
   python generate_response_templates.py
   ```

3. Review and adjust the generated response file in `responses/` if needed

4. Run the test:
   ```bash
   python test_integration.py --test your_test_name
   ```

## Test Structure

### Request Files

Each request file (`request_payloads/*.json`) contains:
- `method`: HTTP method (GET, POST)
- `endpoint`: API endpoint path
- `headers`: HTTP headers
- `body`: Request body (for POST requests)

### Response Files

Each response file (`responses/*.json`) contains the expected JSON response structure.

### Test Runner

The `test_integration.py` script:
- Loads request payloads
- Makes HTTP requests to the API
- Compares actual vs expected responses
- Reports differences
- Generates test summary

## Comparison Logic

The test runner performs deep comparison:
- Type checking (dict, list, primitive)
- Key existence checking
- Value comparison
- Recursive traversal for nested structures
- Difference tracking with full paths

In **non-strict mode** (default):
- Tests pass even with differences
- Differences are reported but don't fail the test

In **strict mode**:
- Tests fail if any differences are found
- Useful for regression testing

## Troubleshooting

### API Server Not Running

**Error**: `Connection refused` or `ConnectionError`

**Solution**: Start the API server:
```bash
make run
# Or: python -m src.main
```

### Module Not Found: requests

**Error**: `ModuleNotFoundError: No module named 'requests'`

**Solution**: Activate virtual environment:
```bash
source ../venv/bin/activate
```

### Tests Failing with 404

**Error**: HTTP 404 Not Found

**Solution**: 
- Check that the endpoint path is correct
- Verify the API server is running
- Check API logs for errors

### Tests Failing with 500

**Error**: HTTP 500 Internal Server Error

**Solution**:
- Check API server logs
- Verify request payload structure
- Ensure schemas are loaded (check `/health` endpoint)

### Response Mismatches

**Issue**: Actual response doesn't match expected

**Solution**:
1. Review the differences reported
2. Update expected response file if API behavior changed
3. Or regenerate responses: `make generate-responses`

### Missing Response Files

**Issue**: Warning about missing expected response files

**Solution**: Generate response templates:
```bash
make generate-responses
```

### No Schemas Found (sync_from_schemas.py)

**Issue**: Script reports no schemas found

**Solution**: Ensure schemas are cached:
```bash
make refresh-schemas
# Or start the API server, which fetches schemas on startup
make run
```

## Example Output

```
# Integration Test Suite for Schema Transformer API
# Base URL: http://localhost:8000
############################################################

Found 46 test cases:
  - get_schema
  - health_check
  - list_schemas
  - transform_cancel
  - transform_confirm
  - transform_discover_discovery-by-QR
  - transform_discover_discovery-services-by-a-cpo
  ...

============================================================
Running test: health_check
============================================================
✓ Loaded request from: health_check.json
✓ Made GET request to /health
  Status Code: 200
✓ Loaded expected response from: health_check.json
✓ Test PASSED - Response matches expected

...

############################################################
# Test Summary
############################################################
Total Tests: 46
Passed: 46
Failed: 0
Errors: 0
############################################################
```

## Continuous Integration

### Using Makefile

```bash
# Start server, run tests, stop server
make run &
sleep 5
make test-strict
```

### Manual CI Script

```bash
# Start API server in background
python -m src.main &
sleep 5  # Wait for server to start

# Run tests in strict mode
cd integration_test
python test_integration.py --strict --save

# Check exit code
if [ $? -eq 0 ]; then
    echo "All tests passed"
else
    echo "Some tests failed"
    exit 1
fi

# Cleanup
pkill -f "src.main"
```

## Performance Notes

The Schema Transformer uses optimized AST operations:

- **O(1) path lookups** via hash indexing (not O(N) tree traversal)
- **Memoized `has_value()`** checks with cache invalidation
- **Disk-cached ASTs** for fast cold starts (~0.5s vs ~2-3s)

If you notice unexpected behavior after schema changes:

```bash
# Clear AST cache to force rebuild
make clean-ast-cache

# Restart server to rebuild ASTs
make run
```

## Best Practices

1. **Keep request files up to date** with actual API usage
2. **Review generated responses** before committing
3. **Use strict mode** in CI/CD pipelines
4. **Document any expected differences** in test comments
5. **Add new test cases** when new actions are added
6. **Run tests before committing** changes to the API
7. **Clear AST cache** if schema structure changes significantly
8. **Resync schemas** when upstream schemas change:
   ```bash
   make refresh-schemas
   make clean-ast-cache
   make sync-schemas
   make generate-responses
   make test-strict
   ```
