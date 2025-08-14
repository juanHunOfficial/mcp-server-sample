from dotenv import load_dotenv

from server import mcp
from core import tools, resources, prompts


# Load environment variables from .env file
load_dotenv()

if __name__ == "__main__":
    mcp.run(transport="stdio")
