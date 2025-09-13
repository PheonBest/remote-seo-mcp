"""
SEO MCP Server: A free SEO tool MCP (Model Control Protocol) service based on Ahrefs data.
Includes features such as backlinks, keyword ideas, and more.
"""
from fastmcp.server.auth.providers.google import GoogleProvider
from fastmcp.server.dependencies import get_access_token
import os
import time
import logging
import urllib.parse
from typing import Dict, List, Optional, Any, Literal

import requests
from dotenv import load_dotenv
from starlette.responses import JSONResponse
from starlette.requests import Request

from openai import OpenAI
from fastmcp import FastMCP
from fastmcp.experimental.sampling.handlers.openai import OpenAISamplingHandler
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ToolError

from seo_mcp.backlinks import get_backlinks, load_signature_from_cache, get_signature_and_overview
from seo_mcp.keywords import get_keyword_ideas, get_keyword_difficulty
from seo_mcp.traffic import check_traffic
from fastmcp.client.sampling import ServerSamplingHandler
from mcp.server.lowlevel.server import LifespanResultT

Transport = Literal["stdio", "http", "sse", "streamable-http"]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment variables
IS_REMOTE: bool = os.getenv("IS_REMOTE", "false").lower() == "true"
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "your-client-id")
GOOGLE_CLIENT_SECRET: str = os.getenv(
    "GOOGLE_CLIENT_SECRET", "your-client-secret")
BASE_URL: str = os.getenv("BASE_URL", "http://localhost:10000")
CAPSOLVER_API_KEY: Optional[str] = os.getenv("CAPSOLVER_API_KEY")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "your-openrouter-api-key")
OPENAI_BASE_URL: str = os.getenv(
    "OPENAI_BASE_URL", "https://api.openai.com/v1")
PORT: int = int(os.getenv("PORT", 10000))

# Restrict access to specific Google Workspace domains, subs, or emails
ALLOWED_DOMAINS: set[str] = {domain.strip() for domain in os.getenv(
    "ALLOWED_DOMAINS", "").split(",") if domain.strip()}
ALLOWED_SUB: set[str] = {sub.strip() for sub in os.getenv(
    "ALLOWED_SUB", "").split(",") if sub.strip()}
ALLOWED_EMAILS: set[str] = {email.strip().lower() for email in os.getenv(
    "ALLOWED_EMAILS", "").split(",") if email.strip()}


# Middleware to restrict access based on allowed emails
class AuthMiddleware(Middleware):
    async def on_request(self, context: MiddlewareContext, call_next):
        # Extract email from your access token
        token = get_access_token()
        if token:
            authorize(token.claims)

        # Allow the chain to continue
        return await call_next(context)


def authorize(claims: Dict[str, Any]) -> None:
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

sampling_handller: ServerSamplingHandler[LifespanResultT] = OpenAISamplingHandler(
    default_model="google/gemini-2.5-flash",
    client=OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL
    )
)

if IS_REMOTE:
    transport: Transport = "streamable-http"
    mcp: FastMCP = FastMCP(
        "SEO MCP",
        sampling_handler=sampling_handller,
        auth=auth_provider,
        middleware=[AuthMiddleware()]
    )
else:
    transport: Transport = "stdio"
    mcp: FastMCP = FastMCP("SEO MCP", sampling_handler=sampling_handller)


@mcp.tool
async def get_user_info() -> dict:
    """Returns information about the authenticated Google user."""

    token = get_access_token()
    # The GoogleProvider stores user data in token claims
    return {
        "google_id": token.claims.get("sub"),
        "email": token.claims.get("email"),
        "name": token.claims.get("name"),
        "picture": token.claims.get("picture"),
        "locale": token.claims.get("locale"),
    }


def get_capsolver_token(site_url: str) -> Optional[str]:
    if not CAPSOLVER_API_KEY:
        return None

    payload: Dict[str, Any] = {
        "clientKey": CAPSOLVER_API_KEY,
        "task": {
            "type": "AntiTurnstileTaskProxyLess",
            "websiteKey": "0x4AAAAAAAAzi9ITzSN9xKMi",
            "websiteURL": site_url,
            "metadata": {"action": ""},
        },
    }

    res: requests.Response = requests.post(
        "https://api.capsolver.com/createTask", json=payload)
    resp: Dict[str, Any] = res.json()
    task_id: Optional[str] = resp.get("taskId")
    if not task_id:
        return None

    while True:
        time.sleep(1)
        res = requests.post("https://api.capsolver.com/getTaskResult",
                            json={"clientKey": CAPSOLVER_API_KEY, "taskId": task_id})
        resp = res.json()
        status: str = resp.get("status", "")
        if status == "ready":
            return resp.get("solution", {}).get("token")
        if status == "failed" or resp.get("errorId"):
            return None


@mcp.tool()
def get_backlinks_list(domain: str) -> Optional[Dict[str, Any]]:
    signature, valid_until, overview_data = load_signature_from_cache(domain)

    if not signature or not valid_until:
        site_url: str = f"https://ahrefs.com/backlink-checker/?input={domain}&mode=subdomains"
        token: Optional[str] = get_capsolver_token(site_url)
        if not token:
            raise Exception(
                f"Failed to get verification token for domain: {domain}")

        signature, valid_until, overview_data = get_signature_and_overview(
            token, domain)
        if not signature or not valid_until:
            raise Exception(f"Failed to get signature for domain: {domain}")

    backlinks: List[Dict[str, Any]] = get_backlinks(
        signature, valid_until, domain)
    return {"overview": overview_data, "backlinks": backlinks}


@mcp.tool()
def keyword_generator(keyword: str, country: str = "us", search_engine: str = "Google") -> Optional[List[str]]:
    site_url: str = f"https://ahrefs.com/keyword-generator/?country={country}&input={urllib.parse.quote(keyword)}"
    token: Optional[str] = get_capsolver_token(site_url)
    if not token:
        raise Exception(
            f"Failed to get verification token for keyword: {keyword}")
    return get_keyword_ideas(token, keyword, country, search_engine)


@mcp.tool()
def get_traffic(domain_or_url: str, country: str = "None", mode: str = "subdomains") -> Optional[Dict[str, Any]]:
    site_url: str = f"https://ahrefs.com/traffic-checker/?input={domain_or_url}&mode={mode}"
    token: Optional[str] = get_capsolver_token(site_url)
    if not token:
        raise Exception(
            f"Failed to get verification token for domain: {domain_or_url}")
    return check_traffic(token, domain_or_url, mode, country)


@mcp.tool()
def keyword_difficulty(keyword: str, country: str = "us") -> Optional[Dict[str, Any]]:
    site_url: str = f"https://ahrefs.com/keyword-difficulty/?country={country}&input={urllib.parse.quote(keyword)}"
    token: Optional[str] = get_capsolver_token(site_url)
    if not token:
        raise Exception(
            f"Failed to get verification token for keyword: {keyword}")
    return get_keyword_difficulty(token, keyword, country)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "mcp-server"})


def main():
    """Run the MCP server"""
    if IS_REMOTE:
        logger.info(
            f"Starting SEO MCP server in REMOTE mode on port {PORT}")
        mcp.run(transport=transport, port=PORT)
    else:
        logger.info(f"Starting SEO MCP server in LOCAL mode on stdio")
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
