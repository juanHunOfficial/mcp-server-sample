from server import mcp

def main():
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()