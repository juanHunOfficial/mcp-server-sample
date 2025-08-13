import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP


# Load environment variables from .env file
load_dotenv()

# Create a FastMCP server instance
mcp = FastMCP(name="SimpleMCPServer", port=8000)
