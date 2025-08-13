from server import mcp
from core import tools, resources, prompts


def main():
    """Run the MCP server with streamable-http transport."""
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()