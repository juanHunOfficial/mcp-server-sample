from server import mcp
import os
import csv

from .schemas import (
    CodingStandard,
    CodingStandardsResponse,
    Reviewer,
    ReviewerList
)


# Define a simple resource
@mcp.resource("info://sop")
def get_sop_document() -> str | None:
    """
    Read the contents of sample_sop.txt from the data folder.
    
    Returns:
        Optional[str]: File contents as a string, None if an error occurs
    """
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'sample_sop.txt'))
    
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        print(f"File not found at: {file_path}")
        return None
    except IOError as e:
        print(f"Error reading file: {e}")
        return None
    

# Define a resource that gets the knowledge base data
@mcp.resource("info://knowledge_base")
def get_knowledge_base() -> list[str]:
    """
    Read the contents of sample_sop.txt from the data folder.
    
    Returns:
        Optional[str]: File contents as a string, None if an error occurs
    """
    file_path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'short_incidents.csv'))
    
    data = []
    with open(file_path, 'r', newline='') as file:
        reader = csv.reader(file)
        for row in reader:
            data.append(row)

    return data


# Switch yto sqlite
@mcp.resource("reviewers://list")
def get_code_reviewers() -> ReviewerList:
    reviewers = []
    with open("./data/code_reviewers.csv", newline="", encoding="utf-8") as csvfile:
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
    with open("./data/coding_standards.csv", newline="", encoding="utf-8") as csvfile:
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
