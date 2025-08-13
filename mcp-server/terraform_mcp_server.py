import os
import httpx
import csv
import hcl2
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field
from mcp.server.fastmcp import FastMCP, Context

mcp = FastMCP("MCP Server Demo")

# ================================== SCHEMAS =============================================
# Utilizing pydantic schemas is vital for type safety and clearly defining your input and output

# Terraform tool
class EnvRequest(BaseModel):
    path: str = Field(description="Path to the Terraform file to analyze")

class EnvResponse(BaseModel):
    variables: List[str] = Field(description="List of variable names defined in the Terraform file")
    providers: List[str] = Field(description="List of provider names used in the Terraform file")
    resources: List[str] = Field(description="List of resources in the format type.name found in the Terraform file")
    outputs: List[str] = Field(description="List of output names defined in the Terraform file")

# Code reviewer tool
class Reviewer(BaseModel):
    name: str
    email: str
    role: str

class ReviewerList(BaseModel):
    reviewers: List[Reviewer]

# Coding standards resource
class CodingStandard(BaseModel):
    section: str
    description: str
    link: HttpUrl

class CodingStandardsResponse(BaseModel):
    standards: List[CodingStandard]

# Changelog tool
class ChangelogEntry(BaseModel):
    title: str
    summary: str
    breaking_changes: Optional[str]
    links: list[str]
    markdown: str


# ================================== TOOLS ===============================================

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


# ================================== RESOURCES =============================================


@mcp.resource("reviewers://list")
def get_code_reviewers() -> ReviewerList:
    reviewers = []
    with open("./code_reviewers.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            reviewers.append(Reviewer(**row))
    return ReviewerList(reviewers=reviewers)


# The intent was to have github copilot reference this
@mcp.resource("info://coding_standards")
def get_coding_standards() -> CodingStandardsResponse:
    """
        This resource should be returning this project particular coding standards, which include:

            - Naming conventions
            - Formatting rules
            - Docstring requirements
            - Security guidelines
            - Links to internal style guides or linters
    """
    standards = []
    with open("./coding_standards.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            standards.append(CodingStandard(**row))
    return CodingStandardsResponse(standards=standards)



@mcp.resource("guidelines://api/{section}")
def get_api_guidelines(section: str = "overview") -> str:
    """
    Return organization API design guidance for a given section.
    Resource URIs are read-only and should not have side effects.

    Args:
        section: One of ["overview", "naming", "versioning", "errors"]

    Returns:
        A short plaintext guideline snippet appropriate for chat/context.
    """
    sections = {
        "overview": (
            "API Guidelines Overview:\n"
            "- Use resource-oriented URLs.\n"
            "- Prefer nouns over verbs.\n"
            "- Be consistent with pagination and filtering."
        ),
        "naming": (
            "Naming:\n"
            "- kebab-case in paths (e.g., /user-profiles).\n"
            "- snake_case for query keys.\n"
            "- Use plural resources (e.g., /users)."
        ),
        "versioning": (
            "Versioning:\n"
            "- Use URI prefix (e.g., /v1/...).\n"
            "- Avoid breaking changes in patch/minor.\n"
            "- Sunset with deprecation headers."
        ),
        "errors": (
            "Errors:\n"
            "- JSON problem details format.\n"
            "- Stable error codes.\n"
            "- Useful, non-sensitive messages."
        ),
    }
    return sections.get(section, sections["overview"])


# ================================== PROMPTS ===============================================

# NOTE: These examples are for GitHub Copilot use not for use in a production level program
@mcp.prompt(title="Deployment Readiness Check")
def pre_deployment_prompt() -> str:
    return """
        Use Case:
            A developer finishes a feature and asks GitHub Copilot:
                "Am I ready to deploy this?"

        Purpose:
            This prompt guides the developer through a structured readiness checklist
            before deployment. It dynamically adapts based on responses and can invoke
            external tools to fetch missing data.

        Prompt Flow:
            1. Ask clarifying questions:
                - Have all automated tests passed?
                - Is the Jira ticket linked to the PR?
                - Has the security scan been completed?
            2. Dynamically adapt follow-up questions based on answers.
            3. Optionally invoke actions to retrieve or trigger missing steps.

        Questions:
            - tests_passed (boolean, required): "Have all automated tests passed?"
            - jira_linked (boolean, required): "Is the Jira ticket linked to the PR?"
            - security_scan (boolean, required): "Has the security scan been completed?"
            - additional_notes (string, optional): "Any additional notes or blockers?"

        Dynamic Logic:
            if not tests_passed:
                ask("Would you like me to fetch the latest test results?")
            if not jira_linked:
                ask("Should I check the Jira ticket status for you?")
            if not security_scan:
                ask("Do you want me to trigger a security scan now?")

        Actions:
            - fetch_test_results: Fetch latest CI/CD test results (endpoint: /ci/tests/latest)
            - check_jira_status: Check Jira ticket status linked to PR (endpoint: /jira/status)
            - run_security_scan: Trigger or verify security scan (endpoint: /security/scan)
    """


@mcp.prompt(title="Pre-Merge Checklist")
def another_prompt() -> str:
    return """
    Use Case:
        A developer asks: "Can I merge this PR?"

    Purpose:
        Guides the developer through a pre-merge checklist to ensure quality and compliance.

    Questions:
        - "Has the PR been approved by at least one reviewer?"
        - "Are all CI checks green?"
        - "Is the branch up to date with main?"
        - "Have you updated the changelog?"

    Dynamic Logic:
        if not approved:
            ask("Would you like me to suggest reviewers?")
        if not ci_green:
            ask("Should I fetch the latest CI status?")
        if not up_to_date:
            ask("Do you want me to rebase this branch?")

    Actions:
        - get_code_reviewers
        - fetch_ci_status
        - trigger_rebase
    """


if __name__ == "__main__":
    mcp.run(transport="stdio")
