"""
Authentication module for SEO MCP Server
"""
import os
import logging
from typing import Dict, Any, Optional, Set

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

# Environment variables
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "your-client-id")
GOOGLE_CLIENT_SECRET: str = os.getenv(
    "GOOGLE_CLIENT_SECRET", "your-client-secret")
BASE_URL: str = os.getenv("BASE_URL", "http://localhost:10000")

# Restrict access to specific Google Workspace domains, subs, or emails
ALLOWED_DOMAINS: Set[str] = {domain.strip() for domain in os.getenv(
    "ALLOWED_DOMAINS", "").split(",") if domain.strip()}
ALLOWED_SUB: Set[str] = {sub.strip() for sub in os.getenv(
    "ALLOWED_SUB", "").split(",") if sub.strip()}
ALLOWED_EMAILS: Set[str] = {email.strip().lower() for email in os.getenv(
    "ALLOWED_EMAILS", "").split(",") if email.strip()}


def authorize(claims: Dict[str, Any]) -> None:
    """
    Authorize a user based on their token claims

    Args:
        claims: The token claims containing user information

    Raises:
        ToolError: If the user is not authorized
    """
    email: Optional[str] = claims.get("email")
    hd: Optional[str] = claims.get("hd")  # Hosted domain
    sub: Optional[str] = claims.get("sub")  # Subject (user ID)

    if ALLOWED_EMAILS and email and email.lower() in ALLOWED_EMAILS:
        return

    if ALLOWED_DOMAINS and hd and hd in ALLOWED_DOMAINS:
        return

    if ALLOWED_SUB and sub and sub in ALLOWED_SUB:
        return

    logger.warning(
        f"Unauthorized access attempt by email: {email}, domain: {hd}, sub: {sub}")
    raise ToolError("Unauthorized access")


class AuthMiddleware(Middleware):
    """Middleware to restrict access based on allowed emails"""

    async def on_request(self, context: MiddlewareContext, call_next):
        """
        Process the request and check authorization

        Args:
            context: The middleware context
            call_next: The next middleware in the chain

        Returns:
            The response from the next middleware
        """

        token = get_access_token()
        if token:
            authorize(token.claims)

        # Allow the chain to continue
        return await call_next(context)


# The GoogleProvider handles Google's token format and validation
auth_provider = GoogleProvider(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    base_url=BASE_URL,
    required_scopes=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ],
)


def get_user_info() -> dict:
    """Returns information about the authenticated Google user."""
    token = get_access_token()
    if token:
        # Check authorization
        authorize(token.claims)

        # The GoogleProvider stores user data in token claims
        return {
            "google_id": token.claims.get("sub"),
            "email": token.claims.get("email"),
            "name": token.claims.get("name"),
            "picture": token.claims.get("picture"),
            "locale": token.claims.get("locale"),
        }
    return {"error": "Not authenticated"}


def setup_auth(mcp: FastMCP) -> None:
    """
    Set up authentication for the MCP server

    Args:
        mcp: The FastMCP instance
    """
    # Register the get_user_info tool
    mcp.tool(get_user_info)
