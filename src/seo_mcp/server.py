"""
SEO MCP Server: A free SEO tool MCP (Model Control Protocol) service based on Ahrefs data.
Includes features such as backlinks, keyword ideas, and more.
"""
from fastmcp.server.auth.providers.google import GoogleProvider
import os
import time
import logging
import urllib.parse
from typing import Dict, List, Optional, Any

import requests
from dotenv import load_dotenv
from starlette.responses import JSONResponse

from fastmcp import FastMCP

from seo_mcp.backlinks import get_backlinks, load_signature_from_cache, get_signature_and_overview
from seo_mcp.keywords import get_keyword_ideas, get_keyword_difficulty
from seo_mcp.traffic import check_traffic

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment variables
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "your-client-id")
GOOGLE_CLIENT_SECRET: str = os.getenv(
    "GOOGLE_CLIENT_SECRET", "your-client-secret")
BASE_URL: str = os.getenv("BASE_URL", "http://localhost:10000")
CAPSOLVER_API_KEY: Optional[str] = os.getenv("CAPSOLVER_API_KEY")
PORT: int = int(os.getenv("PORT", 10000))


# The GoogleProvider handles Google's token format and validation
auth_provider = GoogleProvider(
    client_id=GOOGLE_CLIENT_ID,  # Your Google OAuth Client ID
    client_secret=GOOGLE_CLIENT_SECRET,  # Your Google OAuth Client Secret
    base_url=BASE_URL,  # Must match your OAuth configuration
    required_scopes=[  # Request user information
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ],
    # redirect_path="/auth/callback" # Default value, customize if needed
)

# MCP instance
mcp: FastMCP = FastMCP("SEO MCP", auth=auth_provider)

# Add a protected tool to test authentication


@mcp.tool
async def get_user_info() -> dict:
    """Returns information about the authenticated Google user."""
    from fastmcp.server.dependencies import get_access_token

    token = get_access_token()
    # The GoogleProvider stores user data in token claims
    return {
        "google_id": token.claims.get("sub"),
        "email": token.claims.get("email"),
        "name": token.claims.get("name"),
        "picture": token.claims.get("picture"),
        "locale": token.claims.get("locale")
    }


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
async def health_check(_) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "mcp-server"})


def main():
    """Run the MCP server"""
    mcp.run(transport="http", port=PORT)


if __name__ == "__main__":
    main()
