from fastapi import FastAPI
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from .agent import invoke


# Instantiate the FastAPI app
app = FastAPI()

REQUEST_COUNT = Counter('request_count', 'Total request count')


@app.post("/chat")
async def chat(payload: dict):
    """Endpoint to handle chat requests.

    Payload Structure:
    ```
    {
        "prompt": "Your question or command here"
    }
    ```
    
    Example Prompts:
    - "I have a database sever crash, has anyone dealt with this before?" # Should retrieve the knowledge base tool
    - "What is the current stock price for TSLA?" # Should retrieve the stock price tool
    - "What is 5 * 10?" # Should call the multiply tool
    - "What is the current status of the backend service?" # Should call the prometheus metrics tool
    
    """
    # Send the user prompt to the LLM and get the response
    result = await invoke(payload['prompt'])

    # Write the response to a markdown file
    with open("response.md", "w") as f:
        f.write(result)

    # Return the result
    return {"message": result}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/status")
def status():
    REQUEST_COUNT.inc()
    return {"status": "ok"}
