# Schema Transformer with AST

A Python REST API service that transforms flat backend data (with dot notation keys) into nested JSON structures using Abstract Syntax Trees (AST) built from schema definitions.

## Features

- **Dynamic Schema Handling**: Automatically fetches and processes schemas from GitHub
- **AST-Based Transformation**: Uses Abstract Syntax Trees to maintain schema structure
- **Auto-Detection**: Automatically detects the correct schema from `context.action` field
- **Value Filtering**: Only includes keys with actual values (excludes None, empty strings, empty dicts/lists)
- **Performance Optimized**: O(1) path lookups, memoized computations, and disk caching
- **Caching**: Local cache for schemas and serialized ASTs for fast cold starts
- **REST API**: Simple REST endpoints for transformation and schema management
- **Integration Tests**: Comprehensive test suite for all API actions

## Architecture

The system:
1. Fetches JSON schemas from GitHub repository
2. Builds AST structures for each schema with **path indexing for O(1) lookups**
3. **Caches serialized ASTs to disk** for faster subsequent startups
4. Accepts flat backend data via REST API (e.g., `context.version`, `message.support.name`)
5. Fills AST nodes using **O(1) indexed lookups** (not O(N) tree traversal)
6. Converts filled AST to nested JSON with **memoized value checks**

### Performance Optimizations

| Operation | Complexity | Description |
|-----------|------------|-------------|
| Path lookup | O(1) | Hash-based index instead of tree traversal |
| `has_value()` | O(1) | Memoized with cache invalidation |
| Cold start | ~0.5s | Loads pre-built ASTs from disk cache |
| Fill AST | O(K) | K = number of flat keys (was O(K×N)) |

## Quick Start

```bash
# Full installation
make install

# Start the server
make run

# Run tests
make test
```

## Installation

### Using Makefile (Recommended)

```bash
# Full setup: creates venv, installs deps, creates .env
make install
```

### Manual Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd schema_Transformer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp env.example .env
# Edit .env with your configuration
```

### Troubleshooting Installation

If you encounter build errors, try these solutions:

**Option 1: Use the Makefile**:
```bash
make install
```

**Option 2: Upgrade pip and build tools first**:
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**Option 3: Use the installation script**:
```bash
./install.sh
```

**Option 4: Install packages individually** (if specific package fails):
```bash
pip install fastapi "uvicorn[standard]" requests python-dotenv
pip install "pydantic>=2.12.0"
```

**Note**: The requirements.txt uses version ranges (>=) to ensure compatibility with Python 3.14. Python 3.12 or 3.13 are also fully supported.

## Configuration

Create a `.env` file with the following variables:

```env
GITHUB_REPO_OWNER=bhim
GITHUB_REPO_NAME=ubc-tsd
GITHUB_BRANCH=main
GITHUB_SCHEMA_PATH=Example-schemas
CACHE_DIR=cache
OUTPUT_DIR=output
API_HOST=0.0.0.0
API_PORT=8000
```

## Usage

### Using Makefile Commands

```bash
# See all available commands
make help

# Start the server
make run

# Start with auto-reload (development)
make run-dev

# Run tests
make test

# Run tests in strict mode
make test-strict

# Run a single test
make test-single T=transform_support

# Sync test payloads from schemas
make sync-schemas

# Generate expected responses from API
make generate-responses

# Check API health
make health

# List available schemas
make list-schemas

# Refresh schemas from GitHub
make refresh-schemas

# View cache statistics
make cache-stats

# Clear AST cache (force rebuild)
make clean-ast-cache

# Rebuild all ASTs
make rebuild-asts
```

### Manual Usage

#### Start the Server

```bash
python -m src.main
```

Or using uvicorn directly:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### POST /transform

Transform flat backend data to nested JSON structure.

**Request:**
```json
{
  "data": {
    "context.version": "2.0.0",
    "context.action": "support",
    "context.domain": "beckn.one:deg:ev-charging",
    "message.refId": "order-001",
    "message.support.name": "Ravi Kumar",
    "message.support.phone": "+91-9876543210",
    "message.support.channels[0]": "PHONE",
    "message.support.channels[1]": "WHATSAPP"
  },
  "schema_name": "optional-schema-name"
}
```

**Response:**
```json
{
  "result": {
    "context": {
      "version": "2.0.0",
      "action": "support",
      "domain": "beckn.one:deg:ev-charging"
    },
    "message": {
      "refId": "order-001",
      "support": {
        "name": "Ravi Kumar",
        "phone": "+91-9876543210",
        "channels": ["PHONE", "WHATSAPP"]
      }
    }
  },
  "schema_used": "ev-charging-support"
}
```

**Note**: Keys with no values (None, empty string, empty dict/list) are automatically excluded from the response.

### POST /refresh-schemas

Refresh schemas from GitHub (on-demand).

**Response:**
```json
{
  "message": "Schemas refreshed successfully",
  "schemas_count": 45
}
```

### GET /schemas

List all available schemas and actions.

**Response:**
```json
{
  "schemas": ["ev-charging-support", "ev-charging-init-bap", ...],
  "actions": ["support", "init", "confirm", ...]
}
```

### GET /schemas/{schema_name}

Get specific schema information.

**Response:**
```json
{
  "name": "ev-charging-support",
  "schema": { ... }
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "schemas_loaded": 45,
  "asts_built": 45
}
```

## Example Usage

### Using curl

```bash
curl -X POST "http://localhost:8000/transform" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "context.version": "2.0.0",
      "context.action": "support",
      "context.domain": "beckn.one:deg:ev-charging",
      "message.refId": "order-001",
      "message.support.name": "Ravi Kumar",
      "message.support.phone": "+91-9876543210"
    }
  }'
```

### Using Python

```python
import requests

url = "http://localhost:8000/transform"
payload = {
    "data": {
        "context.version": "2.0.0",
        "context.action": "support",
        "context.domain": "beckn.one:deg:ev-charging",
        "message.refId": "order-001",
        "message.support.name": "Ravi Kumar",
        "message.support.phone": "+91-9876543210"
    }
}

response = requests.post(url, json=payload)
result = response.json()
print(result)
```

## Value Filtering

The transformer automatically excludes keys with empty values:

- `None` values are excluded
- Empty strings `""` are excluded
- Empty dictionaries `{}` are excluded
- Empty lists `[]` are excluded

For example, if `message.support.email` is not provided or is empty, the `email` key will not appear in the final JSON.

## Caching

The system uses a two-level caching strategy for optimal performance:

### Schema Cache (`cache/schemas/`)
- Stores fetched JSON schemas from GitHub
- Allows offline operation
- Refreshed via `POST /refresh-schemas` or `make refresh-schemas`

### AST Cache (`cache/asts/`)
- Stores serialized AST structures
- Validated using schema hashes (auto-rebuilds if schema changes)
- Significantly reduces cold start time (~0.5s vs ~2-3s)
- Clear with `make clean-ast-cache` or `make rebuild-asts`

### Cache Management Commands

```bash
# View cache statistics
make cache-stats

# Clear AST cache only (ASTs rebuild on next start)
make clean-ast-cache

# Clear schema cache only
make clean-schema-cache

# Clear all caches
make clean-cache

# Force rebuild all ASTs
make rebuild-asts
```

## Project Structure

```
schema_Transformer/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── models/
│   │   ├── __init__.py
│   │   └── ast_node.py         # ASTNode with path indexing & memoization
│   ├── builders/
│   │   ├── __init__.py
│   │   └── ast_builder.py      # SchemaASTBuilder - builds AST with index
│   ├── processors/
│   │   ├── __init__.py
│   │   └── ast_filler.py       # ASTFiller - O(1) indexed fills
│   ├── fetchers/
│   │   ├── __init__.py
│   │   └── github_fetcher.py   # GitHubSchemaFetcher - fetches schemas
│   ├── services/
│   │   ├── __init__.py
│   │   └── transformer_service.py  # Main service with disk caching
│   └── api/
│       ├── __init__.py
│       └── routes.py           # FastAPI routes
├── integration_test/
│   ├── request_payloads/       # Test request JSON files
│   ├── responses/              # Expected response JSON files
│   ├── test_integration.py     # Integration test runner
│   ├── sync_from_schemas.py    # Sync payloads from cached schemas
│   ├── generate_response_templates.py  # Generate expected responses
│   └── README.md               # Test suite documentation
├── cache/
│   ├── schemas/                # Cached schema JSON files
│   └── asts/                   # Serialized AST cache (for fast startup)
├── output/                     # Generated payloads (optional)
├── Makefile                    # Build and run commands
├── requirements.txt
├── env.example
├── install.sh
└── README.md
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| **Setup** ||
| `make install` | Full setup (venv + dependencies + env file) |
| `make venv` | Create virtual environment |
| `make deps` | Install dependencies |
| `make setup-env` | Create .env from env.example |
| **Run** ||
| `make run` | Start the API server |
| `make run-dev` | Start server with auto-reload |
| **Testing** ||
| `make test` | Run all integration tests |
| `make test-strict` | Run tests in strict mode |
| `make test-single T=<name>` | Run single test |
| `make test-save` | Run tests and save results |
| **Schema Management** ||
| `make sync-schemas` | Sync test payloads from cached schemas |
| `make generate-responses` | Generate expected responses from API |
| `make refresh-schemas` | Refresh schemas from GitHub |
| `make list-schemas` | List available schemas |
| `make health` | Check API health |
| **Cache Management** ||
| `make cache-stats` | Show AST cache statistics |
| `make clean-ast-cache` | Clear AST cache only (force rebuild) |
| `make clean-schema-cache` | Clear schema cache only |
| `make rebuild-asts` | Force rebuild all ASTs |
| **Cleanup** ||
| `make clean` | Remove Python cache files |
| `make clean-cache` | Remove all caches (schemas + ASTs) |
| `make clean-responses` | Remove generated response files |
| `make clean-all` | Full cleanup |
| **Development** ||
| `make lint` | Check code with linters |
| `make format` | Format code |
| `make check` | Run all checks (lint + test) |

## Performance

### Time Complexity

| Operation | Before | After |
|-----------|--------|-------|
| `find_node_by_path` | O(N) tree traversal | O(1) hash lookup |
| `has_value()` | O(N) per call | O(1) memoized |
| `fill_ast` | O(K × N) | O(K) |
| Cold start | ~2-3s (rebuild all) | ~0.5s (from cache) |

Where:
- **N** = Total nodes in schema
- **K** = Number of flat key-value pairs from backend

### How It Works

1. **Path Indexing**: When an AST is built, a hash map is created mapping full paths (e.g., `context.version`) to their nodes. This enables O(1) lookups instead of O(N) tree traversal.

2. **Memoization**: The `has_value()` method caches its result. When a value is set via `fill_value()`, the cache is invalidated up to the root node.

3. **Disk Caching**: Serialized ASTs are saved to `cache/asts/`. On startup, the system loads cached ASTs if the schema hash matches, avoiding expensive rebuilds.

## Development

### Running Tests

```bash
# Run all tests
make test

# Run in strict mode
make test-strict

# Run specific test
make test-single T=transform_support
```

### Syncing Test Payloads

When schemas change, regenerate test payloads:

```bash
# Sync from cached schemas
make sync-schemas

# Then generate expected responses (API must be running)
make generate-responses
```

### Code Style

The project follows PEP 8 style guidelines. Consider using:
- `black` for code formatting
- `flake8` for linting
- `mypy` for type checking

## Troubleshooting

### Schemas not loading

- Check your internet connection (for GitHub fetch)
- Verify GitHub repository URL in `.env`
- Check `cache/schemas/` directory for cached schemas
- Use `make refresh-schemas` to manually refresh

### Transformation errors

- Verify flat data keys match schema structure
- Check that `context.action` is provided for auto-detection
- Review API error messages for specific issues

### Test failures

- Ensure API server is running: `make run`
- Regenerate expected responses: `make generate-responses`
- Check for schema changes and resync: `make sync-schemas`

### Slow startup

- Check if AST cache exists: `make cache-stats`
- If cache is empty, first startup builds all ASTs
- Subsequent startups load from cache (~0.5s)

### Cache issues

- Clear AST cache: `make clean-ast-cache`
- Clear all caches: `make clean-cache`
- Force rebuild: `make rebuild-asts`

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
