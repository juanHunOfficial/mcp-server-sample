import asyncio
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
import aiohttp

load_dotenv()

# Create a FastMCP server instance
mcp = FastMCP(name="SimpleMCPServer")

class StockPriceResponse(BaseModel):
    """Stock price response details."""
    ticker: str = Field(description="Stock ticker symbol")
    name: str = Field(descriptionn="Name of the company")
    price: float = Field(description="Current stock price in USD")

class ErrorResponse(BaseModel):
    """Structured error response for failed API calls."""
    status: str = Field(description="Status of the request", default="error")
    error_code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error description")
    suggested_resolutions: list[str] = Field(description="List of suggested actions to resolve the error")

# Define a simple tool
@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

@mcp.tool()
async def get_weather(city: str = "London") -> dict[str, str]:
    """Get weather data for a city"""
    return {
        "city": city,
        "temperature": "22",
        "condition": "Partly cloudy",
        "humidity": "65%",
    }

@mcp.tool()
async def get_stock_price_data(ticker: str = "AAPL"):
    """Fetch the current stock price for a given ticker symbol asynchronously."""
    api_key = os.getenv("STOCK_API_KEY")
    if not api_key:
        return ErrorResponse(
            status="error",
            error_code="MISSING_API_KEY",
            message="API key for stock price service is not set",
            suggested_resolutions=["Set the STOCK_API_KEY environment variable"]

        ).dict()

    url = "https://api.api-ninjas.com/v1/stockprice"
    params = {"ticker": ticker}
    headers = {"X-Api-Key": api_key}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return {"status": "success", "result": StockPriceResponse(**data).dict()}
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
                ).dict()

# Define a simple resource
@mcp.resource("info://welcome")
def get_welcome_message() -> str:
    """Get a welcome message."""
    return "Welcome to the Simple MCP Server!"

# Define a simple prompt
@mcp.prompt(title="Simple Greeting")
def generate_greeting(name: str) -> str:
    """Generate a personalized greeting prompt."""
    return f"Please generate a friendly greeting for {name}."

def main():
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()