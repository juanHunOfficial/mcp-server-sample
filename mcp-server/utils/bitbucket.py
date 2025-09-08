from typing import Optional, Any
from datetime import datetime
import httpx
import os

async def request(method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
    """Make an authenticated request to Bitbucket API"""
    BASE_URL = "https://api.bitbucket.org/2.0"
    
    url = f"{BASE_URL}{endpoint}"
    headers = kwargs.pop("headers", {})
    headers["Authorization"] =f"Bearer {os.getenv("BITBUCKET_TOKEN", "")}" 
    headers["Accept"] = "application/json"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.request(method, url, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json()



def iso(dt: Optional[str]) -> Optional[str]:
    """Normalize Bitbucket ISO timestamps to Python ISO strings (or None)."""
    if not dt:
        return None
    return datetime.fromisoformat(dt.replace("Z", "+00:00")).isoformat()