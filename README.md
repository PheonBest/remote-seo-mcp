# SEO MCP

A MCP (Model Control Protocol) SEO tool service based on Ahrefs data. Includes features such as backlink analysis, keyword research, traffic estimation, and more.

[中文](./README_CN.md)

## Overview

This service provides an API to retrieve SEO data from Ahrefs. It handles the entire process, including solving the CAPTCHA, authentication, and data retrieval. The results are cached to improve performance and reduce API costs.

> This MCP service is for educational purposes only. Please do not misuse it. This project is inspired by `@哥飞社群`.

## Features

- 🔍 Backlink Analysis

  - Get detailed backlink data for any domain
  - View domain rating, anchor text, and link attributes
  - Filter educational and government domains

- 🎯 Keyword Research

  - Generate keyword ideas from a seed keyword
  - Get keyword difficulty score
  - View search volume and trends

- 📊 Traffic Analysis

  - Estimate website traffic
  - View traffic history and trends
  - Analyze popular pages and country distribution
  - Track keyword rankings

- 🚀 Performance Optimization

  - Use CapSolver to automatically solve CAPTCHA
  - Response caching

## Installation

### Prerequisites

- Python 3.10 or higher
- CapSolver account and API key ([register here](https://dashboard.capsolver.com/passport/register?inviteCode=1dTH7WQSfHD0))
- Auth0 account (if using OAuth authentication)

### Install from PyPI

```bash
pip install seo-mcp
```

Or use `uv`:

```bash
uv pip install seo-mcp
```

### Manual Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/cnych/seo-mcp.git
   cd seo-mcp
   ```

2. Install dependencies:

   ```bash
   pip install -e .
   # Or
   uv pip install -e .
   ```

3. Set the required environment variables:

   ```bash
   # Required for Ahrefs data extraction
   export CAPSOLVER_API_KEY="your-capsolver-api-key"

   # Required for Auth0 OAuth (if using authentication)
   export AUTH0_DOMAIN="your-tenant.us.auth0.com"
   export AUTH0_AUDIENCE="https://your-api-identifier"
   export AUTH0_CLIENT_ID="your-client-id"
   export AUTH0_CLIENT_SECRET="your-client-secret"
   export RESOURCE_SERVER_URL="http://localhost:10000"
   ```

   Alternatively, create a `.env` file in the project root with these variables.

## Usage

### Run the service

You can run the service in the following ways:

#### Use in Cursor IDE

In the Cursor settings, switch to the MCP tab, click the `+Add new global MCP server` button, and then input:

```json
{
  "mcpServers": {
    "SEO MCP": {
      "command": "uvx",
      "args": ["--python", "3.10", "seo-mcp"],
      "env": {
        "CAPSOLVER_API_KEY": "CAP-xxxxxx"
      }
    }
  }
}
```

You can also create a `.cursor/mcp.json` file in the project root directory, with the same content.

### API Reference

The service provides the following MCP tools:

#### `get_backlinks_list(domain: str)`

Get the backlinks of a domain.

**Parameters:**

- `domain` (string): The domain to analyze (e.g. "example.com")

**Returns:**

```json
{
  "overview": {
    "domainRating": 76,
    "backlinks": 1500,
    "refDomains": 300
  },
  "backlinks": [
    {
      "anchor": "Example link",
      "domainRating": 76,
      "title": "Page title",
      "urlFrom": "https://referringsite.com/page",
      "urlTo": "https://example.com/page",
      "edu": false,
      "gov": false
    }
  ]
}
```

#### `keyword_generator(keyword: str, country: str = "us", search_engine: str = "Google")`

Generate keyword ideas.

**Parameters:**

- `keyword` (string): The seed keyword
- `country` (string): Country code (default: "us")
- `search_engine` (string): Search engine (default: "Google")

**Returns:**

```json
[
  {
    "keyword": "Example keyword",
    "volume": 1000,
    "difficulty": 45,
    "cpc": 2.5
  }
]
```

#### `get_traffic(domain_or_url: str, country: str = "None", mode: str = "subdomains")`

Get the traffic estimation.

**Parameters:**

- `domain_or_url` (string): The domain or URL to analyze
- `country` (string): Country filter (default: "None")
- `mode` (string): Analysis mode ("subdomains" or "exact")

**Returns:**

```json
{
  "traffic_history": [...],
  "traffic": {
    "trafficMonthlyAvg": 50000,
    "costMontlyAvg": 25000
  },
  "top_pages": [...],
  "top_countries": [...],
  "top_keywords": [...]
}
```

#### `keyword_difficulty(keyword: str, country: str = "us")`

Get the keyword difficulty score.

**Parameters:**

- `keyword` (string): The keyword to analyze
- `country` (string): Country code (default: "us")

**Returns:**

```json
{
  "difficulty": 45,
  "serp": [...],
  "related": [...]
}
```

## Development

For development:

```bash
git clone https://github.com/cnych/seo-mcp.git
cd seo-mcp
uv sync
uv run main.py
```

For testing:

```
npx @modelcontextprotocol/inspector --url http://localhost:10000
```

## Authentication with Google OAuth 2.0

This service supports OAuth 2.0 authentication with Auth0 without. Claude.ai compatibility is ensured by an OAuth proxy handled by fastmcp internally. To set up Google OAuth for your MCP server:

Create an OAuth 2.0 Client ID in your Google Cloud Console to get the credentials needed for authentication:

1. Navigate to OAuth Consent Screen
   Go to the Google Cloud Console and select your project (or create a new one).First, configure the OAuth consent screen by navigating to APIs & Services → OAuth consent screen. Choose “External” for testing or “Internal” for G Suite organizations.

2. Create OAuth 2.0 Client ID
   Navigate to APIs & Services → Credentials and click ”+ CREATE CREDENTIALS” → “OAuth client ID”.Configure your OAuth client:

- Application type: Web application
- Name: Choose a descriptive name (e.g., “FastMCP Server”)
- Authorized JavaScript origins: Add your server’s base URL (e.g., http://localhost:8000)
- Authorized redirect URIs: Add your server URL + /auth/callback (e.g., http://localhost:8000/auth/callback)

> The redirect URI must match exactly. The default path is /auth/callback, but you can customize it using the redirect_path parameter. For local development, Google allows http://localhost URLs with various ports. For production, you must use HTTPS.

> If you want to use a custom callback path (e.g., /auth/google/callback), make sure to set the same path in both your Google OAuth Client settings and the redirect_path parameter when configuring the GoogleProvider.

3. Save Your Credentials
   After creating the client, you’ll receive:

- Client ID: A string ending in .apps.googleusercontent.com
- Client Secret: A string starting with GOCSPX-

Download the JSON credentials or copy these values securely.

4. Configure environment variables in .env

## Deployment

You can deploy to Netlify or vercel. To deploy to render:

1. Create a new web service on Render
2. Connect your GitHub repository
3. Set build command to `uv sync --frozen && uv cache prune --ci`
4. Set start command to `uv run main.py`
5. Set health check path to `/health`
6. Add the required environment variables in the Render dashboard:

- ALLOWED_EMAILS or ALLOWED_DOMAINS or ALLOWED_SUB
- BASE_URL: https://your-render-service.onrender.com
- CAPSOLVER_API_KEY
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- IS_REMOTE: true
- OPENAI_API_KEY (if using sampling fallback)
- OPENAI_BASE_URL (if using sampling fallback)

## How it works

1. The user sends a request through MCP
2. The service uses CapSolver to solve the Cloudflare Turnstile CAPTCHA
3. The service gets the authentication token from Ahrefs
4. The service retrieves the requested SEO data
5. The service processes and returns the formatted results

## Troubleshooting

- **CapSolver API key error**：Check the `CAPSOLVER_API_KEY` environment variable
- **Rate limiting**：Reduce request frequency
- **No results**：The domain may not be indexed by Ahrefs
- **Other issues**：See [GitHub repository](https://github.com/cnych/seo-mcp)

## License

MIT License - See LICENSE file
