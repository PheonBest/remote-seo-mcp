"""
SEO MCP Server: A free SEO tool MCP (Model Control Protocol) service based on Ahrefs data.
Includes features such as backlinks, keyword ideas, and more.
"""
import os
import re
import time
import logging
import urllib.parse
from typing import Dict, List, Optional, Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
import uvicorn

from fastmcp import FastMCP
from mcpauth import MCPAuth
from mcpauth.config import AuthServerType
from mcpauth.utils import fetch_server_config

from seo_mcp.backlinks import get_backlinks, load_signature_from_cache, get_signature_and_overview
from seo_mcp.keywords import get_keyword_ideas, get_keyword_difficulty
from seo_mcp.traffic import check_traffic

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment variables
AUTH0_DOMAIN: str = os.getenv("AUTH0_DOMAIN", "your-tenant.us.auth0.com")
AUTH0_AUDIENCE: str = os.getenv(
    "AUTH0_AUDIENCE", "https://your-api-identifier")
AUTH0_CLIENT_ID: str = os.getenv("AUTH0_CLIENT_ID", "your-client-id")
AUTH0_CLIENT_SECRET: str = os.getenv(
    "AUTH0_CLIENT_SECRET", "your-client-secret")
RESOURCE_SERVER_URL: str = os.getenv(
    "RESOURCE_SERVER_URL", "http://localhost:10000")
CAPSOLVER_API_KEY: Optional[str] = os.getenv("CAPSOLVER_API_KEY")

# Clean domain
AUTH0_DOMAIN = re.sub(r"^https?://", "", AUTH0_DOMAIN.strip().rstrip("/"))
AUTH0_BASE_URL: str = f"https://{AUTH0_DOMAIN}"

# Initialize MCPAuth
mcp_auth: MCPAuth = MCPAuth(
    server=fetch_server_config(
        f"{AUTH0_BASE_URL}/",
        type=AuthServerType.OAUTH
    )
)

# MCP instance
mcp: FastMCP = FastMCP("SEO MCP")


def get_capsolver_token(site_url: str) -> Optional[str]:
    """Solve captcha using CapSolver and return verification token"""
    if not CAPSOLVER_API_KEY:
        return None

    payload: Dict[str, Any] = {
        "clientKey": CAPSOLVER_API_KEY,
        "task": {
            "type": "AntiTurnstileTaskProxyLess",
            "websiteKey": "0x4AAAAAAAAzi9ITzSN9xKMi",
            "websiteURL": site_url,
            "metadata": {"action": ""}
        }
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
async def health_check(_: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "mcp-server"})


def main() -> None:
    """Run the MCP server with OAuth support"""
    app: FastAPI = FastAPI(title="SEO MCP Server")
    api_mcp: FastMCP = FastMCP.from_fastapi(app=app, name="SEO MCP")

    bearer_auth = mcp_auth.bearer_auth_middleware(
        "jwt", required_scopes=["openid", "profile", "email"]
    )

    mcp_app = api_mcp.http_app(path="/mcp")
    mcp_app.dependency_overrides = getattr(mcp_app, "dependency_overrides", {})
    mcp_app.dependency_overrides[None] = bearer_auth

    app.mount("/mcp", mcp_app)

    # CORS
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_endpoint() -> Dict[str, str]:
        return {"status": "healthy", "service": "mcp-server"}

    # OAuth metadata route
    app.add_route("/.well-known/oauth-authorization-server",
                  mcp_auth.metadata_route(), methods=["GET"])

    @app.post("/register")
    async def register(request: Request) -> JSONResponse:
        return await mcp_auth.register(request)

    uvicorn.run(app, host="0.0.0.0", port=10000)


if __name__ == "__main__":
    main()
