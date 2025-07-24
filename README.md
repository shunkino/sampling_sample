# MCP Poetry Server
A Model Context Protocol (MCP) server that demonstrates the sampling capability by generating creative poems based on user input. This server showcases how to implement asynchronous tool responses using MCP's sampling feature.

## Features
- **Poem Generation Tool**: Analyzes input text and generates poetic expressions
- **Asynchronous Response**: Uses MCP sampling to provide responses after LLM processing
- **Unified User Experience**: Returns the generated poem directly as the tool response
- **Error Handling**: Proper error responses for failed sampling requests

## How It Works
1. User calls the `generate_poem` tool with text input
2. Server triggers a sampling request to the LLM
3. LLM generates a creative poem based on the input
4. Server returns the poem as the tool response (no intermediate messages)

This demonstrates a key MCP pattern: using sampling to enhance tool capabilities with LLM-generated content.

## Installation
### Prerequisites
- Python 3.7+
- An MCP-compatible client that supports tool calls and sampling (Method call to "sampling/createMessage" must be supported)

### Setup
1. Clone or download this repository
2. No additional dependencies required - uses only Python standard library

## Usage
Once configured, you can use the `generate_poem` tool in your MCP client:

### Example 1: Simple Theme
```
Input: "sunset"
Output: Poem based on 'sunset':

Golden rays fade to amber light,
Day surrenders to gentle night.
Colors dance across the sky,
As another day waves goodbye.
```

### Example 2: Abstract Concept
```
Input: "freedom"
Output: Poem based on 'freedom':

Unbound spirit soars on high,
Breaking chains that held it tight.
Wings of hope spread wide and free,
Dancing with infinity.
```

## Tool Specification
### `generate_poem`

**Description**: Analyzes the received text and requests sampling to generate poetic expressions based on it using LLM.

**Parameters**:
- `text_to_analyze` (string, required): Text to analyze and express poetically.

**Response**: Returns a formatted poem based on the input theme.

## Architecture
The server implements a unique asynchronous pattern:

1. **Tool Call Reception**: Stores the original request without immediate response
2. **Sampling Trigger**: Sends a sampling request to the LLM with creative prompts
3. **Response Correlation**: Links sampling responses back to original tool requests
4. **Unified Response**: Sends the final poem as the tool call response

This pattern ensures users get a seamless experience where the tool call completes only when the actual work (poem generation) is finished.

## Key Components
- **MCPServer Class**: Main server implementation
- **Request Correlation**: Maps sampling requests to original tool calls
- **Error Handling**: Graceful handling of sampling failures
- **Logging**: Comprehensive logging for debugging

## Logging
The server logs all activities to `mcp_server.log`:
- Request/response messages
- Sampling request triggers
- Generated poems
- Error conditions

## Development
### Running Locally
```bash
python mcp_server.py
```

The server reads from stdin and writes to stdout, following the MCP protocol.

### Testing
You can test the server by sending JSON-RPC messages via stdin. Example initialization:

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}}}
```

## Customization
### Modifying the Prompt
Edit the `trigger_sampling` method to customize the poem generation prompt:

```python
prompt = f"Please create a short, poetic verse based on the theme '{text_from_tool}'."
```

### Adjusting LLM Parameters
Modify the sampling request parameters:

```python
"maxTokens": 100,        # Adjust poem length
"temperature": 0.7       # Control creativity level
```

## License
This project is open source and available under the MIT License.
