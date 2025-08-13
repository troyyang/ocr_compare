import json
import re
from typing import Any, Callable

from fastapi import Request
from jwt import PyJWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from core import security
from core.extends_logger import logger
from core.error_handle import AuthorizationException
from core.i18n import _
import traceback


# Helper functions for converting naming conventions
def to_snake_case(name: str) -> str:
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def to_camel_case(snake_str: str) -> str:
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def convert_keys(data: Any, converter: Callable) -> Any:
    """Recursively converts dictionary keys using the provided converter function."""
    if isinstance(data, dict):
        return {converter(key): convert_keys(value, converter) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_keys(item, converter) for item in data]
    else:
        return data


class NamingConventionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Handle incoming requests (optional: convert camelCase to snake_case)
        if 'application/json' in request.headers.get('content-type', ''):
            try:
                body = await request.json()
                transformed_body = convert_keys(body, to_snake_case)
                request._body = json.dumps(transformed_body).encode('utf-8')
            except json.JSONDecodeError:
                pass

        # Call the next middleware or route handler
        response = await call_next(request)

        # Handle outgoing responses
        if 'application/json' in response.headers.get('content-type', ''):
            # Create a streaming response
            async def transform_response_body():
                buffer = ""
                async for chunk in response.body_iterator:
                    buffer += chunk.decode('utf-8')
                    try:
                        # Attempt to parse the buffer as JSON
                        json_data = json.loads(buffer)
                        # Transform keys
                        transformed_data = convert_keys(json_data, to_camel_case)
                        # Yield the transformed JSON as bytes
                        yield json.dumps(transformed_data).encode('utf-8')
                        buffer = ""  # Clear the buffer after successful parsing
                    except json.JSONDecodeError:
                        # If the buffer is not yet a complete JSON, continue accumulating
                        continue

            # Return a new StreamingResponse with the transformed body
            transformed_response = StreamingResponse(
                content=transform_response_body(),
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )
            # Remove the Content-Length header to avoid conflicts
            if "Content-Length" in transformed_response.headers:
                del transformed_response.headers["Content-Length"]
            return transformed_response

        return response

async def login_required(request: Request):
    # Precompile regex patterns for ignoreURLs (with wildcard support) on first run
    if not hasattr(login_required, "_ignore_patterns"):
        ignore_urls = [
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/logout",
            "/api/llm/all",
            "/api/data_sources/analyze/callback",
            "/api/ws/**"
        ]
        patterns: List[Pattern] = []
        for url_pattern in ignore_urls:
            # Escape regex special chars except wildcards
            parts = re.split(r'(\*\*)', url_pattern)
            escaped_parts = [re.escape(part) if part != '**' else part for part in parts]
            # Convert '**' to regex '.*' (matches anything including slashes)
            pattern_str = ''.join(escaped_parts).replace('**', '.*')
            patterns.append(re.compile(f"^{pattern_str}$"))
        login_required._ignore_patterns = patterns

    request_url = request.url.path
    # Skip auth if URL matches any ignore pattern
    if any(pattern.match(request_url) for pattern in login_required._ignore_patterns):
        return

    # Skip auth for OPTIONS requests
    if request.method == "OPTIONS":
        return

    # Proceed with token validation for non-ignored URLs
    access_token = request.headers.get("Authorization", "")
    return await validate_token(access_token)

async def validate_token(access_token: str):
    try:
        if not access_token or not access_token.startswith('Bearer '):
            logger.error("Invalid Authorization header format")
            raise AuthorizationException(code=AuthorizationException.INVALID_TOKEN, msg=_("Invalid token format"))
            
        access_token = access_token.split(' ')[1].strip()
        if not access_token:
            logger.error("Empty token after Bearer")
            raise AuthorizationException(code=AuthorizationException.INVALID_TOKEN, msg=_("Token not provided"))
            
        payload = security.decode_access_token(access_token)
        return payload
        
    except PyJWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        if "expired" in str(e).lower():
            raise AuthorizationException(code=AuthorizationException.EXPIRED_TOKEN, msg=_("Token has expired"))
        raise AuthorizationException(code=AuthorizationException.INVALID_TOKEN, msg=_("Invalid token"))
    except Exception as e:
        logger.error(f"Unexpected error in login_required: {str(e)}")
        traceback.print_exc()
        raise AuthorizationException(code=AuthorizationException.INVALID_TOKEN, msg=_("Authentication failed"))

    raise AuthorizationException(code=AuthorizationException.INVALID_TOKEN, msg=_("Token not provided"))