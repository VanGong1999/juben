"""
Authentication Middleware for FastAPI

Provides middleware for protecting routes with JWT authentication
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Optional, List, Callable
import re

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import JubenLogger
from utils.jwt_auth import decode_token
from utils.token_blacklist_manager import get_token_blacklist_manager

logger = JubenLogger("auth_middleware")


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for FastAPI

    Validates JWT tokens for protected routes
    """

    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[List[str]] = None,
        token_header: str = "Authorization"
    ):
        """
        Initialize authentication middleware

        Args:
            app: ASGI application
            exclude_paths: List of paths to exclude from authentication (regex patterns)
            token_header: Header name containing the token
        """
        super().__init__(app)

        # Default paths to exclude
        default_excludes = [
            r"^/health$",
            r"^/metrics$",
            r"^/docs$",
            r"^/redoc$",
            r"^/openapi\.json$",
            r"^/juben/health$",
            r"^/juben/agents$",
            r"^/auth/login$",
            r"^/auth/register$",
            r"^/auth/refresh$",
        ]

        self.exclude_paths = exclude_paths or default_excludes
        self.token_header = token_header

        # Compile regex patterns
        self.exclude_patterns = [re.compile(pattern) for pattern in self.exclude_paths]

        logger.info(f"✅ AuthMiddleware initialized")
        logger.info(f"   Excluding {len(self.exclude_paths)} paths from authentication")

    def is_excluded_path(self, path: str) -> bool:
        """
        Check if path is excluded from authentication

        Args:
            path: Request path

        Returns:
            bool: True if path is excluded
        """
        for pattern in self.exclude_patterns:
            if pattern.match(path):
                return True
        return False

    async def dispatch(self, request: Request, call_next):
        """
        Process request and validate authentication

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response: Response from next handler or error response
        """
        path = request.url.path

        # Skip authentication for excluded paths
        if self.is_excluded_path(path):
            logger.debug(f"⏭️  Skipping auth for: {path}")
            return await call_next(request)

        # Extract token from header
        token = self.extract_token(request)

        if token is None:
            logger.warning(f"⚠️ No token provided for: {path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "message": "Authentication required",
                    "error_code": "NO_TOKEN"
                }
            )

        # Validate token
        try:
            payload = decode_token(token)

            # Check if token is blacklisted (使用带缓存的管理器)
            blacklist_manager = await get_token_blacklist_manager()
            if await blacklist_manager.is_blacklisted(token):
                logger.warning(f"⚠️ Blacklisted token used for: {path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "success": False,
                        "message": "Token has been revoked",
                        "error_code": "TOKEN_REVOKED"
                    }
                )

            # Add user info to request state
            request.state.user_id = payload.sub
            request.state.permissions = payload.permissions
            request.state.token_payload = payload

            logger.debug(f"✅ Authenticated user {payload.sub} for: {path}")

        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "success": False,
                    "message": e.detail,
                    "error_code": "INVALID_TOKEN"
                }
            )

        # Continue to next handler
        return await call_next(request)

    def extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from request headers

        Args:
            request: Incoming request

        Returns:
            str: Token string or None
        """
        auth_header = request.headers.get(self.token_header)

        if auth_header is None:
            return None

        # Remove "Bearer " prefix if present
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

        # 只接受 Bearer 前缀，拒绝裸 token（收紧令牌误用面）
        return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware

    Basic rate limiting by user ID
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        exclude_paths: Optional[List[str]] = None
    ):
        """
        Initialize rate limit middleware

        Args:
            app: ASGI application
            requests_per_minute: Maximum requests per minute per user
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)

        self.requests_per_minute = requests_per_minute
        self.user_requests = {}  # user_id -> [(timestamp, count)]

        default_excludes = [
            r"^/health$",
            r"^/metrics$",
            r"^/docs$",
            r"^/redoc$",
        ]

        exclude_patterns = exclude_paths or default_excludes
        self.exclude_patterns = [re.compile(pattern) for pattern in exclude_patterns]

        logger.info(f"✅ RateLimitMiddleware initialized: {requests_per_minute} req/min")

    def is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from rate limiting"""
        for pattern in self.exclude_patterns:
            if pattern.match(path):
                return True
        return False

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        from datetime import datetime
        path = request.url.path

        # Skip for excluded paths
        if self.is_excluded_path(path):
            return await call_next(request)

        # Get user ID from request state (set by AuthMiddleware)
        user_id = getattr(request.state, "user_id", None)

        # If no user_id, use IP address
        if user_id is None:
            user_id = request.client.host

        # Check rate limit
        now = datetime.now()

        # Clean old requests
        self.cleanup_old_requests(user_id, now)

        # Get current request count
        user_data = self.user_requests.get(user_id, {"count": 0, "window_start": now})

        # Reset window if needed
        time_diff = (now - user_data["window_start"]).total_seconds()
        if time_diff >= 60:
            user_data = {"count": 0, "window_start": now}

        # Check limit
        if user_data["count"] >= self.requests_per_minute:
            logger.warning(f"⚠️ Rate limit exceeded for user: {user_id}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "message": "Rate limit exceeded. Please try again later.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                }
            )

        # Increment counter
        user_data["count"] += 1
        self.user_requests[user_id] = user_data

        # Continue
        return await call_next(request)

    def cleanup_old_requests(self, user_id: str, now):
        """Clean up old request records"""
        if user_id in self.user_requests:
            time_diff = (now - self.user_requests[user_id]["window_start"]).total_seconds()
            if time_diff >= 60:
                del self.user_requests[user_id]


class CORSMiddleware(BaseHTTPMiddleware):
    """
    CORS middleware for cross-origin requests

    Note: FastAPI has built-in CORSMiddleware, this is a custom implementation
    for additional control if needed
    """

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = True
    ):
        """
        Initialize CORS middleware

        Args:
            app: ASGI application
            allow_origins: Allowed origins
            allow_methods: Allowed HTTP methods
            allow_headers: Allowed headers
            allow_credentials: Allow credentials
        """
        super().__init__(app)

        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials

        logger.info(f"✅ CORSMiddleware initialized")

    async def dispatch(self, request: Request, call_next):
        """Process request with CORS headers"""
        origin = request.headers.get("origin")

        # Handle preflight requests
        if request.method == "OPTIONS":
            response = JSONResponse(content={"status": "ok"})
        else:
            response = await call_next(request)

        # Add CORS headers
        response.headers["Access-Control-Allow-Origin"] = (
            origin if origin in self.allow_origins or "*" in self.allow_origins else "*"
        )

        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)

        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Request logging middleware

    Logs all incoming requests with timing information
    """

    def __init__(self, app: ASGIApp):
        """Initialize request logging middleware"""
        super().__init__(app)
        logger.info("✅ RequestLoggingMiddleware initialized")

    async def dispatch(self, request: Request, call_next):
        """Log request with timing"""
        import time
        from datetime import datetime

        start_time = time.time()

        # Log request
        logger.info(f"📥 {request.method} {request.url.path} from {request.client.host}")

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"📤 {request.method} {request.url.path} -> "
                f"{response.status_code} ({duration*1000:.2f}ms)"
            )

            # Add timing header
            response.headers["X-Process-Time"] = str(duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ {request.method} {request.url.path} -> Error: {e} ({duration*1000:.2f}ms)")
            raise


def get_user_id_from_request(request: Request) -> Optional[str]:
    """
    Extract user ID from request state

    Args:
        request: FastAPI request

    Returns:
        str: User ID or None
    """
    return getattr(request.state, "user_id", None)


def get_user_permissions(request: Request) -> List[str]:
    """
    Extract user permissions from request state

    Args:
        request: FastAPI request

    Returns:
        List[str]: User permissions
    """
    return getattr(request.state, "permissions", [])


# Dependency to get current user from request state
async def get_current_user_from_middleware(request: Request) -> Optional[str]:
    """
    FastAPI dependency to get current user from middleware

    Args:
        request: FastAPI request

    Returns:
        str: User ID or None
    """
    return get_user_id_from_request(request)
