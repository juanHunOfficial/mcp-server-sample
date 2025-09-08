import os
import json
import hcl2
import httpx
import sqlite3
import requests
from server import mcp
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import Context
from datetime import datetime

from config.constants import DB_PATH
from utils.bitbucket import request, iso
from .schemas import (
    EnvRequest,
    EnvResponse,
    ChangelogEntry
)

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
    """Generate a changelog entry based on recent commits or PR description.

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

@mcp.tool()
async def list_repositories(
    workspace: str | None = None,
    project: str | None = None,
    limit: int = 25,
    start: int = 0,
) -> list[dict[str, Any]]:
    """List repositories in a workspace or project."""
    workspace = workspace or os.getenv("BITBUCKET_DEFAULT_WORKSPACE")
    if not workspace:
        raise ValueError("Workspace is required (set BITBUCKET_DEFAULT_WORKSPACE or pass as arg)")

    endpoint = f"/repositories/{workspace}"
    params = {"pagelen": limit, "page": start // limit + 1}
    if project:
        params["q"] = f'project.key="{project}"'

    data = await request("GET", endpoint, params=params)

    repos = []
    for item in data.get("values", []):
        repos.append(
            {
                "uuid": item.get("uuid"),
                "name": item.get("name"),
                "full_name": item.get("full_name"),
                "description": item.get("description"),
                "is_private": item.get("is_private", False),
                "clone_links": item.get("links", {}).get("clone", []),
                "size": item.get("size"),
                "language": item.get("language"),
                "created_on": (
                    datetime.fromisoformat(item["created_on"].replace("Z", "+00:00")).isoformat()
                    if item.get("created_on") else None
                ),
                "updated_on": (
                    datetime.fromisoformat(item["updated_on"].replace("Z", "+00:00")).isoformat()
                    if item.get("updated_on") else None
                ),
            }
        )
    return repos


@mcp.tool()
async def list_pullrequests(
    repository: str,
    workspace: Optional[str] = None,
    state: str = "OPEN",
    limit: int = 25,
    start: int = 0,
) -> List[Dict[str, Any]]:
    """
    List pull requests in a repository.

    Args:
        repository: Repository slug
        workspace: Workspace name (defaults to BITBUCKET_DEFAULT_WORKSPACE)
        state: PR state (OPEN, MERGED, DECLINED, SUPERSEDED)
        limit: Page size (default: 25; Bitbucket max is typically 100)
        start: 0-based offset; converted to Bitbucket's 1-based 'page'
    """
    ws = workspace or os.getenv("BITBUCKET_DEFAULT_WORKSPACE")
    if not ws:
        raise ValueError(
            "Workspace is required (set BITBUCKET_DEFAULT_WORKSPACE or pass workspace=...)."
        )

    print(f"Listing pull requests for repo '{repository}' in workspace '{ws}', state='{state}'")

    endpoint = f"/repositories/{ws}/{repository}/pullrequests"
    limit = max(1, min(limit, 100))
    params: Dict[str, Any] = {
        "state": state,
        "pagelen": limit,
        "page": (start // limit) + 1,
    }

    try:
        data = await request("GET", endpoint, params=params)

        result: List[Dict[str, Any]] = []
        for item in data.get("values", []):
            author = item.get("author") or {}
            src_branch = (item.get("source") or {}).get("branch") or {}
            dst_branch = (item.get("destination") or {}).get("branch") or {}

            result.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "description": item.get("description"),
                    "state": item.get("state"),
                    "author": (
                        {
                            "uuid": author.get("uuid"),
                            "username": author.get("username"),
                            "display_name": author.get("display_name"),
                            "account_id": author.get("account_id"),
                            "nickname": author.get("nickname"),
                        }
                        if author
                        else None
                    ),
                    "source": {"name": src_branch.get("name")} if src_branch else None,
                    "destination": {"name": dst_branch.get("name")} if dst_branch else None,
                    "created_on": iso(item.get("created_on")),
                    "updated_on": iso(item.get("updated_on")),
                    "close_source_branch": item.get("close_source_branch", False),
                    "reviewers": item.get("reviewers", []),
                    "participants": item.get("participants", []),
                }
            )

        print(f"Found {len(result)} pull requests")
        return result

    except Exception as e:
        print(f"Error listing pull requests: {e}")
        raise


@mcp.tool()
async def create_pull_request(
    repository: str,
    title: str,
    source_branch: str,
    target_branch: str = "main",
    description: str = "",
    workspace: str | None = None,
    close_source_branch: bool = False,
    reviewers: list[str] | None = None,
) -> dict[str, Any]:
    """
    Create a new pull request in Bitbucket.

    Args:
        repository: Repository slug
        title: Pull request title
        source_branch: Source branch name
        target_branch: Target branch name (default: main)
        description: Pull request description (optional)
        workspace: Workspace name (optional, defaults to env)
        close_source_branch: Whether to close source branch after merge
        reviewers: List of reviewer UUIDs (optional)

    Returns:
        Dictionary with pull request details
    """
    ws = workspace or os.getenv("BITBUCKET_DEFAULT_WORKSPACE")
    if not ws:
        raise ValueError("Workspace is required (set BITBUCKET_DEFAULT_WORKSPACE or pass workspace=...).")

    print(f"Creating pull request in repo '{repository}': {source_branch} -> {target_branch}")

    endpoint = f"/repositories/{ws}/{repository}/pullrequests"

    data = {
        "title": title,
        "description": description,
        "source": {"branch": {"name": source_branch}},
        "destination": {"branch": {"name": target_branch}},
        "close_source_branch": close_source_branch,
    }

    if reviewers:
        data["reviewers"] = [{"uuid": r} for r in reviewers]

    try:
        item = await request("POST", endpoint, json=data)

        result = {
            "id": item.get("id"),
            "title": item.get("title"),
            "description": item.get("description"),
            "state": item.get("state"),
            "author": item.get("author", {}),
            "created_on": iso(item.get("created_on")),
            "updated_on": iso(item.get("updated_on")),
        }

        print(f"Pull request created successfully: #{result['id']} - {result['title']}")
        return result

    except Exception as e:
        print(f"Error creating pull request: {e}")
        raise


@mcp.tool()
async def approve_pull_request(
    repository: str,
    pr_id: int,
    workspace: str | None = None,
) -> dict[str, Any]:
    """
    Approve a pull request.
    """
    ws = workspace or os.getenv("BITBUCKET_DEFAULT_WORKSPACE")
    if not ws:
        raise ValueError("Workspace is required (set BITBUCKET_DEFAULT_WORKSPACE or pass workspace=...).")

    print(f"Approving pull request #{pr_id} in repo '{repository}'")

    endpoint = f"/repositories/{ws}/{repository}/pullrequests/{pr_id}/approve"

    try:
        result = await request("POST", endpoint)
        print(f"Pull request #{pr_id} approved successfully.")
        return result
    except Exception as e:
        print(f"Error approving pull request: {e}")
        raise


@mcp.tool()
async def decline_pull_request(
    repository: str,
    pr_id: int,
    workspace: str | None = None,
) -> dict[str, Any]:
    """
    Decline a pull request.
    """
    ws = workspace or os.getenv("BITBUCKET_DEFAULT_WORKSPACE")
    if not ws:
        raise ValueError("Workspace is required (set BITBUCKET_DEFAULT_WORKSPACE or pass workspace=...).")

    print(f"Declining pull request #{pr_id} in repo '{repository}'")

    endpoint = f"/repositories/{ws}/{repository}/pullrequests/{pr_id}/decline"

    try:
        result = await request("POST", endpoint)
        print(f"Pull request #{pr_id} declined successfully.")
        return result
    except Exception as e:
        print(f"Error declining pull request: {e}")
        raise


@mcp.tool()
async def merge_pull_request(
    repository: str,
    pr_id: int,
    merge_strategy: str = "merge_commit",
    workspace: str | None = None,
) -> dict[str, Any]:
    """
    Merge an approved pull request.
    """
    ws = workspace or os.getenv("BITBUCKET_DEFAULT_WORKSPACE")
    if not ws:
        raise ValueError("Workspace is required (set BITBUCKET_DEFAULT_WORKSPACE or pass workspace=...).")

    print(f"Merging pull request #{pr_id} in repo '{repository}' using strategy '{merge_strategy}'")

    endpoint = f"/repositories/{ws}/{repository}/pullrequests/{pr_id}/merge"
    data = {"merge_strategy": merge_strategy}

    try:
        result = await request("POST", endpoint, json=data)
        print(f"Pull request #{pr_id} merged successfully.")
        return result
    except Exception as e:
        print(f"Error merging pull request: {e}")
        raise


@mcp.tool()
async def update_pull_request(
    repository: str,
    pr_id: int,
    title: str | None = None,
    description: str | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    """
    Update pull request title and/or description.
    """
    ws = workspace or os.getenv("BITBUCKET_DEFAULT_WORKSPACE")
    if not ws:
        raise ValueError("Workspace is required (set BITBUCKET_DEFAULT_WORKSPACE or pass workspace=...).")

    if not title and not description:
        raise ValueError("At least one of title or description must be provided.")

    print(f"Updating pull request #{pr_id} in repo '{repository}'")

    endpoint = f"/repositories/{ws}/{repository}/pullrequests/{pr_id}"
    data: dict[str, Any] = {}
    if title:
        data["title"] = title
    if description:
        data["description"] = description

    try:
        item = await request("PUT", endpoint, json=data)

        result = {
            "id": item.get("id"),
            "title": item.get("title"),
            "description": item.get("description"),
            "state": item.get("state"),
            "author": item.get("author", {}),
            "source": (item.get("source") or {}).get("branch", {}),
            "destination": (item.get("destination") or {}).get("branch", {}),
            "created_on": iso(item.get("created_on")),
            "updated_on": iso(item.get("updated_on")),
            "close_source_branch": item.get("close_source_branch", False),
            "reviewers": item.get("reviewers", []),
            "participants": item.get("participants", []),
        }

        print(f"Pull request #{pr_id} updated successfully.")
        return result
    except Exception as e:
        print(f"Error updating pull request: {e}")
        raise
