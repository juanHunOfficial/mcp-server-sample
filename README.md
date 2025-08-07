# MCP Server Sample

## Description
This project is a sample implementation of a Model Context Protocol (MCP) server that integrates with an OpenAI model (GPT-4o) to process user prompts. It provides tools for tasks like retrieving stock prices, querying a knowledge base for incident details, and performing simple calculations (e.g., multiplication). The server also serves resources like a knowledge base (`short_incidents.csv`) and a standard operating procedure (SOP) document (`sample_sop.txt`). The backend script interacts with the MCP server to execute tools based on user prompts and prints the results to the terminal.

## Prerequisites
Before setting up the project, ensure you have the following installed:
- **Git**: To clone the repository. Download from [git-scm.com](https://git-scm.com/downloads).
- **Python 3.8+**: Required to run the scripts. Download from [python.org](https://www.python.org/downloads/).
- A code editor like [Visual Studio Code](https://code.visualstudio.com/) (recommended for ease of use).
- An **OpenAI API key**: Required for the backend to communicate with GPT-4o. Sign up at [platform.openai.com](https://platform.openai.com/).
- An **API-Ninjas Stock Price API key**: Required for the stock price tool. Sign up at [api-ninjas.com](https://api-ninjas.com/).

## Installation
Follow these steps to set up the project on your local machine:

1. **Clone the Repository**:
   Open a terminal and run the following command to download the project:
   ```bash
   git clone https://github.com/juanHunOfficial/mcp-server-sample.git
   ```

2. **Navigate to the Project Directory**:
   Move into the project folder:
   ```bash
   cd mcp-server-sample
   ```

3. **Set Up a Virtual Environment**:
   Create and activate a virtual environment to manage dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
   ```

4. **Install Dependencies**:
   Install the required Python packages listed in the `requirements.txt` file:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
1. **Set Up Environment Variables**:
   Create a `.env` file in the `backend` directory to store your OpenAI API key:
   ```bash
   cd backend
   touch .env
   ```
   Add the following lines to the `.env` file, replacing the placeholders with your actual API keys:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   ```

   Create a `.env` file in the `mcp-server` directory to store your OpenAI API key:
   ```bash
   cd mcp-server
   touch .env
   ```
   Add the following lines to the `.env` file, replacing the placeholders with your actual API keys:
   ```bash
   STOCK_API_KEY=your_api_ninjas_stock_key_here
   ```

2. **Verify Data Files**:
   Ensure the `data` directory exists in the project root and contains:
   - `incidents.db`: A SQLite database with an `incidents` table for the `get_incident_by_id` tool.
   - `short_incidents.csv`: A CSV file for the knowledge base resource.
   - `sample_sop.txt`: A text file for the SOP resource.
   If these files are missing, the program may fail to read resources. Contact the repository owner for these files or create placeholder versions (e.g., an empty `sample_sop.txt` or a minimal `short_incidents.csv`).

## Running the Program
The project consists of two components: the MCP server and the backend script. Both must be running simultaneously in separate terminal windows.

1. **Start the MCP Server**:
   In one terminal, navigate to the `mcp-server` directory and run the server:
   ```bash
   cd mcp-server
   python main.py
   ```
   This starts the MCP server on `http://localhost:8000/mcp`. You should see output indicating the server is running.

2. **Run the Backend Script**:
   In a second terminal, navigate to the `backend` directory and run the backend script:
   ```bash
   cd backend
   python main.py
   ```
   The script will:
   - Connect to the MCP server.
   - Retrieve available tools and resources.
   - Process a sample user prompt (e.g., "I have a database sever crash, has anyone dealt with this before?").
   - Call the appropriate tools (e.g., `get_incident_by_id` for database issues) and print results to the terminal.

3. **Verify Output**:
   The backend script will print:
   - The list of available tools.
   - The tools chosen by the LLM based on the prompt.
   - The results of tool calls (e.g., incident details, stock prices, or calculations).
   - A mock final LLM response combining the prompt and tool results.

## Usage
- **Running with Different Prompts**:
  The backend script includes three example prompts:
  - `"I have a database sever crash, has anyone dealt with this before?"`: Triggers the `get_incident_by_id` tool to query the knowledge base.
  - `"What is the current stock price for TSLA?"`: Triggers the `get_stock_price_data` tool to fetch stock data.
  - `"What is 5 * 10?"`: Triggers the `multiply` tool for a simple calculation.
  To test a different prompt, modify the `user_prompts` list in `backend/main.py` and change the index in `asyncio.run(test(user_prompts[0]))` to `1` or `2`, or add your own prompt.

- **Example Output**:
  For the prompt `"I have a database sever crash, has anyone dealt with this before?"`, you might see:
  ```
  Retrieved the following tools:
  {
      "type": "function",
      "function": {
          "name": "get_incident_by_id",
          ...
      }
  }

  Tools chosen:
  {
      "function": {
          "name": "get_incident_by_id",
          "arguments": "{\"ticket_id\": \"KB00001\"}"
      }
  }

  Tool Called: get_incident_by_id
  Arguments Passed: {"ticket_id": "KB00001"}
  Result: {"ticket_id": "KB00001", "short_description": "Database crash", ...}
  ```

## Troubleshooting
- **Error: “Module not found”**:
  Ensure all dependencies are installed (`pip install -r requirements.txt`). Verify the `mcp` library is available; it may be a custom or private package. Contact the repository owner if `mcp` is not found on PyPI.
- **Error: “Connection refused” on `http://localhost:8000/mcp`**:
  Confirm the MCP server is running (`python mcp-server/main.py`) before starting the backend script.
- **Error: “API key for stock price service is not set”**:
  Verify the `STOCK_API_KEY` is set in the `.env` file and loaded correctly.
- **Error: “File not found” for `incidents.db`, `short_incidents.csv`, or `sample_sop.txt`**:
  Ensure the `data` directory contains these files. Create placeholder files if necessary (e.g., `touch data/sample_sop.txt`).
- **Error: “Invalid API key” for OpenAI**:
  Check that your `OPENAI_API_KEY` is valid and has access to the GPT-4o model.
