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
```

## Authentication with Auth0

This service supports OAuth 2.0 authentication with Auth0 and Dynamic Client Registration (DCR) for Claude.ai compatibility. To set up Auth0 for your MCP server:

1. **Create an Auth0 Account**
   - Sign up at [auth0.com](https://auth0.com)

2. **Enable OIDC Dynamic Application Registration**
   - Navigate to Auth0 Dashboard → Tenant Settings
   - Go to Advanced Settings tab
   - Find "Enable OIDC Dynamic Application Registration" and enable it

3. **Configure Auth0 API**
   - Create a new API in the Auth0 dashboard
   - Set a meaningful name and identifier (this will be your `AUTH0_AUDIENCE`)
   - Enable RBAC and Add Permissions in the Access Token

4. **Create Auth0 Application**
   - Create a new "Regular Web Application"
   - In Settings, note the Domain, Client ID, and Client Secret
   - Add `http://localhost:10000/callback` to the Allowed Callback URLs
   - Add `http://localhost:10000` to the Allowed Web Origins

5. **Grant Management API Permissions** (For promoting connections to domain-level)
   - Create a Machine to Machine Application
   - Authorize it for the Auth0 Management API with `read:connections` and `update:connections` scopes
   - Use the Management API to promote connections to domain-level for third-party authentication

6. **Set Environment Variables**
   - Set environment variables as shown in the Installation section
   - The server will require authentication for all MCP endpoints

When Claude.ai connects to your MCP server, it will automatically:
1. Discover OAuth endpoints via `/.well-known/oauth-authorization-server`
2. Register as a dynamic client via `/register`
3. Create an Auth0 application automatically
4. Initiate the OAuth flow for user authentication

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
