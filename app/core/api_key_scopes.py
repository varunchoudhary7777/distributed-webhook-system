from typing import Annotated
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from app.core.dependencies import CurrentAPIKey
from app.models.api_key import APIKey

def require_api_key_scope(scope: str) -> Callable:
    if not scope.strip():
        raise ValueError("Scope must not be empty")
    async def dependency(api_key: CurrentAPIKey) -> APIKey:
        if scope not in api_key.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key lacks the required scope"
            )
        return api_key
    return dependency
