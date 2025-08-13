from fastapi import APIRouter

# Import all API modules
from api import (
    auth,
    user,
    document,
)

# Create main router
api = APIRouter()

# Authentication endpoints
api.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# User management endpoints
api.include_router(user.router, prefix="/users", tags=["User Management"])

# Document management endpoints
api.include_router(document.router, prefix="/documents", tags=["Documents"])