from server import mcp
from typing import Optional, Dict
import sqlite3
import os
import aiohttp
import requests
import json
import httpx
import hcl2
from mcp.server.fastmcp import Context

from constants import DB_PATH
from .schemas import (
    StockPriceResponse,
    ErrorResponse,
    EnvRequest,
    EnvResponse,
    ChangelogEntry
)


# Define a simple tool
@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


# Define the database retrieval tool that fetches data from a database
@mcp.tool(title="Query KB by ticket_id", description="Call this tool to get a better more information about an incident that will help the user")
def get_incident_by_id(ticket_id: str) -> Optional[Dict]:
    """
    Retrieve a specific ticket from the SQLite database by ticket_id.
    
    Args:
        ticket_id (str): The ticket ID to retrieve (e.g., 'KB00001') which MUST match the knowledge base ticket_id
    
    Returns:
        Optional[Dict]: Dictionary containing ticket details if found, None otherwise
    """
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Execute query to fetch ticket by ID
        query = """
        SELECT * 
        FROM incidents 
        WHERE ticket_id = ?
        """
        cursor.execute(query, (ticket_id,))
        
        # Fetch the result
        result = cursor.fetchone()
        
        # If ticket is found, convert to dictionary
        if result:
            return {
                'ticket_id': result[0],
                'short_description': result[1],
                'description': result[2],
                'priority': result[3],
                'close_notes': result[4],
                'known_solution': result[5],
                'root_cause': result[6]
            }
        
        return None
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
        
    finally:
        if conn:
            conn.close()


# Define a tool for making an API call to the api-ninja Stock Price API
@mcp.tool()
async def get_stock_price_data(ticker: str = "AAPL") -> dict:
    """Fetch the current stock price for a given ticker symbol asynchronously."""
    api_key = os.getenv("STOCK_API_KEY")
    if not api_key:
        return ErrorResponse(
            status="error",
            error_code="MISSING_API_KEY",
            message="API key for stock price service is not set",
            suggested_resolutions=["Set the STOCK_API_KEY environment variable"]

        ).model_dump()

    url = "https://api.api-ninjas.com/v1/stockprice"
    params = {"ticker": ticker}
    headers = {"X-Api-Key": api_key}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return {"status": "success", "result": StockPriceResponse(**data).model_dump()}
            else:
                return ErrorResponse(
                    status="error",
                    error_code=f"HTTP_{response.status}",
                    message=f"Failed to fetch stock price: {await response.text()}",
                    suggested_resolutions=[
                        "Check if the ticker symbol is valid",
                        "Verify the API key is correct",
                        "Try again later"
                    ]
                ).model_dump()


@mcp.tool()
def get_backend_status() -> str:
    """Retrieve backend system health from the prometheus server.
    
    Returns:
        str: Metrics in JSON format
    """
    try:
        response = requests.get("http://localhost:9090/api/v1/query?query=up{job=\"backend\"}")
        content = json.dumps(response.json(), indent=4)
        return content
    except Exception as e:
        return f"Error retrieving metrics: {str(e)}"
      


# NOTE: the params are the inputSchema
# When testing in MCP Inspector type this into the box that is asking for the request: " {"path" : "./main.tf"} "
@mcp.tool()
def get_terraform_env(request: EnvRequest) -> EnvResponse:
    """Return variables, providers, resources, and outputs from a Terraform file."""
    with open(request.path, "r") as f:
        data = hcl2.load(f)

    # Collect variable names
    variables = [list(d.keys())[0] for d in data.get("variable", [])]

    # Collect provider names
    providers = [list(d.keys())[0] for d in data.get("provider", [])]

    # Collect resources as type.name
    resources = []
    for r in data.get("resource", []):
        for rtype, rbody in r.items():
            for name in rbody.keys():
                resources.append(f"{rtype}.{name}")

    # Collect outputs if present
    outputs = [list(d.keys())[0] for d in data.get("output", [])]
    
    # NOTE: This structure is the outputSchema
    return EnvResponse(
        variables=variables,
        providers=providers,
        resources=resources,
        outputs=outputs
    )


@mcp.tool()
async def generate_changelog(
    repo: str,
    pr_number: Optional[int] = None,
    branch: Optional[str] = None,
    ctx: Optional[Context] = None
) -> ChangelogEntry:
    """
    Generate a changelog entry based on recent commits or PR description.

    Args:
        repo: Repository name (e.g., 'acme/service')
        pr_number: Pull request number (optional)
        branch: Branch name (optional)
    """
    if ctx:
        await ctx.info(f"Generating changelog for {repo}")
        await ctx.report_progress(progress=0.2, total=1.0, message="Fetching PR or commit data")

    # -------------------------------
    # Fetch PR or commit info (GitHub API example)
    # -------------------------------
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

    if pr_number:
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    elif branch:
        url = f"https://api.github.com/repos/{repo}/commits?sha={branch}&per_page=5"
    else:
        raise ValueError("Either pr_number or branch must be provided")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    if ctx:
        await ctx.report_progress(progress=0.6, total=1.0, message="Building changelog entry")

    # -------------------------------
    # Extract details
    # -------------------------------
    if pr_number:
        title = data.get("title", "Update")
        summary = data.get("body", "").split("\n")[0] or "No description provided."
        links = [data.get("html_url")]
    else:
        commits = data if isinstance(data, list) else []
        title = f"Updates from branch {branch}"
        summary = "; ".join([c["commit"]["message"].split("\n")[0] for c in commits[:3]])
        links = [c["html_url"] for c in commits]

    # Detect breaking changes
    breaking_changes = None
    if "BREAKING CHANGE" in summary.upper():
        breaking_changes = summary

    markdown = f"""
    ### {title}

    - **Summary:** {summary}
    {f"- **Breaking Changes:** {breaking_changes}" if breaking_changes else ""}
    - **Links:** {' '.join(links)}
    """.strip()

    if ctx:
        await ctx.report_progress(progress=1.0, total=1.0, message="Changelog generated")

    return ChangelogEntry(
        title=title,
        summary=summary,
        breaking_changes=breaking_changes,
        links=links,
        markdown=markdown
    )
