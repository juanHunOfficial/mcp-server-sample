from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
from mcp import ClientSession
from mcp.types import Tool
from mcp.client.streamable_http import streamablehttp_client
from openai import AzureOpenAI
from openai.types.chat import ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import Function
import json
import os
from rich import print_json
from dotenv import load_dotenv
import asyncio

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'mcp-server', '.env'))


# Instantiate the backend server
app = FastAPI(title="Simple AI Agent API")

# Instantiate the AI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
)

MCP_SERVER_URL = "http://localhost:8000/mcp" # Testing

def format_tools(tools: list[Tool]) -> list[dict]:
    """Convert a list of MCP tools to an openai format. LLM models have a particular format for how they want to access the tool object.
    
        This is OpenAI's format.
    """

    # Format tools information into an openai readable format
    openai_toolkit = [{
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        }
    } for tool in tools]

    return openai_toolkit

async def llm_call(client: AzureOpenAI, prompt: str, tools: list[dict] = None) -> tuple:
    """Sends a prompt and tool list to openai and returns the tool choices"""

    if tools:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'user', 'content': prompt}
            ],
            tools=tools,
            tool_choice='auto' # [Options]: 'required', 'auto', and 'none' NOTE: when the tools param contains tools 'auto' is the default, if not then 'none' is the default
        )
        return response.choices[0].message.tool_calls
    else:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'user', 'content': prompt}
            ]
        )
        return response.choices[0].message.content

async def test(user_prompt: str) -> None:
    # Start an MCP Client Session
    async with streamablehttp_client(MCP_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:

            # Initialize the session
            await session.initialize()

            # Retrieve the list of tools from the MCP Server
            list_tools_result = await session.list_tools()
            tools = format_tools(list_tools_result.tools)

            print("\n\nRetrieved the following tools:\n")
            for tool in tools:
                print_json(json.dumps(tool))

            # Pass that list of tools to the llm and capture the tool choices
            tool_choices = await llm_call(client, user_prompt, tools)

            print(f'\n\nTools chosen:\n')
            for tool in tool_choices:
                print_json(tool.model_dump_json())

            # Initialize a follow up prompt with the original prompt
            follow_up_prompt = f"User's Prompt:\n\n{user_prompt}\n\nResults of Tool Calls:\n"


            # Call each tool in the tool_choices returned by the LLM
            for call in tool_choices:

                # Retrieve tool name and arguments
                tool_name = call.function.name
                args_json = json.loads(call.function.arguments)

                # Call the tool by name, passing the arguments
                result = await session.call_tool(tool_name, args_json)

                # This parsing assumes that the return type was list[mcp.types.TextContent] of length 1
                response_text = result.content[0].text

                # Format and wrap in markdown ticks if JSON data
                try:
                    data = json.loads(response_text)
                    response_text = f"\nTool returned {json.dumps(data, indent=4)}"
                except Exception:
                    pass

                # Append the tool call result to the follow up prompt
                tool_call_result = f"\n\nTool Called: {tool_name}\nArguments Passed: {call.function.arguments}\nResult: {response_text}\n"
                print(tool_call_result)
                follow_up_prompt += tool_call_result

            print(f"\nAll tools called, sending the follow up prompt to LLM:\n\n{follow_up_prompt}\n")

            # ------ This is where you would send the follow up prompt to the LLM ------ #
            response = await llm_call(client, follow_up_prompt)
            # -------------------------------------------------------------------------- #

            print('Mock LLM Final Response:\n')
            print(f"{response}\n")


if __name__ == '__main__':

    user_prompts = [
        "I have a database sever crash, how do i fix it?", # Should retrieve the knowledge base tool
        "What is the current stock price for TSLA?", # Should retrieve the stock price tool
        "What is 5 * 10?" # Should call the multiply tool
    ]

    asyncio.run(test(user_prompts[0]))
