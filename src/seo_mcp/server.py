"""
SEO MCP Server: A free SEO tool MCP (Model Control Protocol) service based on Ahrefs data.
Includes features such as backlinks, keyword ideas, and more.
"""
import os
import time
import logging
import urllib.parse
from typing import Dict, List, Optional, Any, Literal

import requests
from dotenv import load_dotenv
from starlette.responses import JSONResponse

from openai import OpenAI
from fastmcp import FastMCP
from fastmcp.experimental.sampling.handlers.openai import OpenAISamplingHandler
from fastmcp.client.sampling import ServerSamplingHandler
from mcp.server.lowlevel.server import LifespanResultT

from seo_mcp.auth import auth_provider, AuthMiddleware, setup_auth
from seo_mcp.backlinks import get_backlinks, load_signature_from_cache, get_signature_and_overview
from seo_mcp.keywords import get_keyword_ideas, get_keyword_difficulty
from seo_mcp.traffic import check_traffic

Transport = Literal["stdio", "http", "sse", "streamable-http"]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment variables
IS_REMOTE: bool = os.getenv("IS_REMOTE", "false").lower() == "true"
CAPSOLVER_API_KEY: Optional[str] = os.getenv("CAPSOLVER_API_KEY")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "your-openrouter-api-key")
OPENAI_BASE_URL: str = os.getenv(
    "OPENAI_BASE_URL", "https://api.openai.com/v1")
HOST: str = os.getenv("HOST", "0.0.0.0")  # Bind to all interfaces by default
PORT: int = int(os.getenv("PORT", 10000))

sampling_handler: ServerSamplingHandler = OpenAISamplingHandler(
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
        sampling_handler=sampling_handler,
        auth=auth_provider,
        middleware=[AuthMiddleware()]
    )
else:
    transport: Transport = "stdio"
    mcp: FastMCP = FastMCP("SEO MCP", sampling_handler=sampling_handler)

# Set up authentication
setup_auth(mcp)


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
            logging.error(f"CAPSOLVER error: {resp}")
            return None


@mcp.tool()
def get_backlinks_list(domain: str) -> Optional[Dict[str, Any]]:
    signature, valid_until, overview_data = load_signature_from_cache(domain)

    if not signature or not valid_until:
        site_url: str = f"https://ahrefs.com/backlink-checker/?input={domain}&mode=subdomains"
        token: Optional[str] = get_capsolver_token(site_url)
        if not token:
            logging.error(f"Failed to get verification token for domain: {domain}")
            raise Exception(
                f"Failed to get verification token for domain: {domain}")

        signature, valid_until, overview_data = get_signature_and_overview(
            token, domain)
        if not signature or not valid_until:
            logging.error(f"Failed to get signature for domain: {domain}")
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
            f"Starting SEO MCP server in REMOTE mode on {HOST}:{PORT}")
        mcp.run(transport=transport, host=HOST, port=PORT)
    else:
        logger.info(f"Starting SEO MCP server in LOCAL mode on stdio")
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
