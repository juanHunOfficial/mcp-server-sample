import os
import aiohttp
import sqlite3
import csv
from typing import Optional, Dict
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

load_dotenv()

# Get the directory of the current script (backend folder)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct and normalize the path to the database (../data/incidents.db)
DB_PATH = os.path.normpath(os.path.join(current_dir, '..', 'data', 'incidents.db'))

# Create a FastMCP server instance
mcp = FastMCP(name="SimpleMCPServer")

# ================================================ SCHEMAS ================================================================================

class StockPriceResponse(BaseModel):
    """Stock price response details."""
    ticker: str = Field(description="Stock ticker symbol")
    name: str = Field(description="Name of the company")
    price: float = Field(description="Current stock price in USD")
    exchange: str = Field(description="The market hosting the stock")
    currency: str = Field(description="The currency used to trade this stock")

class ErrorResponse(BaseModel):
    """Structured error response for failed API calls."""
    status: str = Field(description="Status of the request", default="error")
    error_code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error description")
    suggested_resolutions: list[str] = Field(description="List of suggested actions to resolve the error")

class KnowledgeBaseResponse(BaseModel):
    ticket_id: str = Field(description="This is a placeholder for the database connection")
    short_description: str = Field(description="This is a placeholder for the database connection")
    description: str = Field(description="This is a placeholder for the database connection")
    priority: str = Field(description="This is a placeholder for the database connection")
    close_notes: Optional[str] = Field(description="This is a placeholder for the database connection", default=None) 
    known_solution: Optional[str] = Field(description="This is a placeholder for the database connection", default=None)
    root_cause: Optional[str] = Field(description="This is a placeholder for the database connection", default=None)
    sys_created_on: Optional[datetime] = Field(description="This is a placeholder for the database connection", default=None)

# ================================================ TOOLS =================================================================================

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
            
# ================================================ RESOURCES ================================================================================

# Define a simple resource
@mcp.resource("info://sop")
def get_sop_document() -> str:
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
def get_knowledge_base() -> str:
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

# ================================================ PROMPTS ==================================================================================

# Define a simple prompt
@mcp.prompt(title="Knowledge Base Query")
def knowledge_base_query(context: str, supporting_docs: str, knowledge_base: str) -> str:
    """Generate the prompt for a Solutions Expert"""
    return f"""
        # Role
            You are a world class solutions expert, helping businesses solve complex problems quick and effectively.

        # Tasks
            - Given the following context, help the user by providing step-by-step instructions to their problems. 
            - If the user has an issue that is close to a description in our knowledge base then use that ticket_id to call the get_incident_by_id tool
              use the information that that tool provides to help the user with their issue.

        # Context
            {context}

        # Supporting Documents
            ## Documents
                {supporting_docs}

            ## Knowledge base data from ServiceNow
                {knowledge_base}

        # Notes
            - It is CRITICAL not to site any fabricated past incidents outside of the context and supporting documents you were given.
            - If there is nothing in the supporting documentation that can aid you then give the best solution that 
              you are aware of related to the context. 
            - List the steps of your solution in numerical order. 
            - **IMPORTANT** When calling the get_incident_by_id tool you MUST match the ticket_id you got from the knowledge base with the ticket_id parameter you send
              for example "KB00015" is the one you want, then pass "KB00015" as the parameter.
    """
