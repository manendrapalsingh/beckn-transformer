"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from src.api.routes import router, set_transformer_service
from src.services.transformer_service import SchemaTransformerService

# Load environment variables
load_dotenv()

# Initialize transformer service
transformer_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global transformer_service
    
    # Startup
    # Get configuration from environment
    repo_owner = os.getenv("GITHUB_REPO_OWNER", "bhim")
    repo_name = os.getenv("GITHUB_REPO_NAME", "ubc-tsd")
    branch = os.getenv("GITHUB_BRANCH", "main")
    schema_path = os.getenv("GITHUB_SCHEMA_PATH", "Example-schemas")
    
    # Initialize transformer service
    transformer_service = SchemaTransformerService(
        repo_owner=repo_owner,
        repo_name=repo_name,
        branch=branch,
        schema_path=schema_path
    )
    
    # Load cached schemas and build ASTs
    print("🚀 Starting Schema Transformer Service...")
    print("📥 Loading schemas from cache...")
    transformer_service.fetch_and_build_asts()
    
    # Set service in routes
    set_transformer_service(transformer_service)
    
    print("✅ Service ready!")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Schema Transformer Service...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Schema Transformer API",
    description="Transform flat backend data to nested JSON using AST-based schema transformation",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Schema Transformer API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=True
    )

