"""FastAPI routes for schema transformation."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from src.services.transformer_service import SchemaTransformerService

router = APIRouter()

# Global service instance (will be initialized in main.py)
transformer_service: Optional[SchemaTransformerService] = None


def set_transformer_service(service: SchemaTransformerService):
    """Set the transformer service instance."""
    global transformer_service
    transformer_service = service


class TransformRequest(BaseModel):
    """Request model for transform endpoint."""
    data: Dict[str, Any]
    schema_name: Optional[str] = None


class TransformResponse(BaseModel):
    """Response model for transform endpoint."""
    result: Dict[str, Any]
    schema_used: Optional[str] = None


class RefreshResponse(BaseModel):
    """Response model for refresh endpoint."""
    message: str
    schemas_count: int


class SchemaListResponse(BaseModel):
    """Response model for schema list endpoint."""
    schemas: List[str]
    actions: List[str]


@router.post("/transform", response_model=TransformResponse, status_code=status.HTTP_200_OK)
async def transform(request: TransformRequest):
    """
    Transform flat backend data to nested JSON structure.
    
    Args:
        request: Transform request with flat data and optional schema name
        
    Returns:
        Nested JSON structure matching schema
    """
    if transformer_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transformer service not initialized"
        )
    
    try:
        result = transformer_service.process_backend_data(
            request.data,
            request.schema_name
        )
        
        # Determine which schema was used
        schema_used = request.schema_name
        if not schema_used:
            action = request.data.get('context.action')
            if action and action in transformer_service.schema_index:
                schema_used = transformer_service.schema_index[action][0]
        
        return TransformResponse(
            result=result,
            schema_used=schema_used
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transformation failed: {str(e)}"
        )


@router.post("/refresh-schemas", response_model=RefreshResponse, status_code=status.HTTP_200_OK)
async def refresh_schemas():
    """
    Refresh schemas from GitHub (on-demand).
    
    Returns:
        Refresh status and schema count
    """
    if transformer_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transformer service not initialized"
        )
    
    try:
        transformer_service.fetch_and_build_asts()
        schemas_count = len(transformer_service.schemas)
        
        return RefreshResponse(
            message="Schemas refreshed successfully",
            schemas_count=schemas_count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schema refresh failed: {str(e)}"
        )


@router.get("/schemas", response_model=SchemaListResponse, status_code=status.HTTP_200_OK)
async def list_schemas():
    """
    List all available schemas and actions.
    
    Returns:
        List of schema names and actions
    """
    if transformer_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transformer service not initialized"
        )
    
    try:
        schemas = transformer_service.list_available_schemas()
        actions = transformer_service.list_available_actions()
        
        return SchemaListResponse(
            schemas=schemas,
            actions=actions
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list schemas: {str(e)}"
        )


@router.get("/schemas/{schema_name}", status_code=status.HTTP_200_OK)
async def get_schema(schema_name: str):
    """
    Get specific schema information.
    
    Args:
        schema_name: Name of the schema
        
    Returns:
        Schema information
    """
    if transformer_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transformer service not initialized"
        )
    
    schema = transformer_service.get_schema_by_name(schema_name)
    
    if schema is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema '{schema_name}' not found"
        )
    
    return {
        "name": schema_name,
        "schema": schema
    }


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    if transformer_service is None:
        return {
            "status": "unhealthy",
            "message": "Transformer service not initialized"
        }
    
    return {
        "status": "healthy",
        "schemas_loaded": len(transformer_service.schemas),
        "asts_built": len(transformer_service.asts)
    }

