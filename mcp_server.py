import sys
import json
import logging
import select

# Logging configuration
logging.basicConfig(filename='mcp_server.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class MCPServer:
    def __init__(self):
        self.request_id_counter = 1000
        self.sampling_requests = {}
        self.pending_tool_requests = {}  # Store pending tool requests

    def run(self):
        """Main server loop with efficient input handling"""
        logging.info("Server started. Waiting for requests...")
        while True:
            try:
                # Use select to wait for input availability (efficient, non-blocking)
                if self._wait_for_input():
                    request = self._read_message()
                    if request is None:
                        continue

                    method = request.get("method")
                    request_id = request.get("id")
                    
                    if method:
                        logging.info(f"Received request: {request}")
                        handler = self.get_handler(method)
                        if handler:
                            handler(request)
                        elif "id" in request:
                            logging.warning(f"No handler for method: {method}")
                    elif request_id in self.sampling_requests:
                        logging.info(f"Received sampling response: {request}")
                        self.handle_sampling_response(request)
                    else:
                        logging.warning(f"Received a response with no method and unknown id: {request}")

            except KeyboardInterrupt:
                logging.info("Server shutdown requested")
                break
            except Exception as e:
                logging.error(f"An error occurred: {e}", exc_info=True)

    def get_handler(self, method):
        """Return handler corresponding to method name"""
        handlers = {
            "initialize": self.handle_initialize,
            "notifications/initialized": self.handle_initialized,
            "tools/list": self.handle_tools_list,
            "tools/call": self.handle_tools_call,
            "prompts/list": self.handle_empty_list,
            "resources/list": self.handle_empty_list,
            "resources/templates/list": self.handle_empty_list
        }
        return handlers.get(method)

    def _send_message(self, message):
        """Send JSON-RPC message to standard output"""
        json_message = json.dumps(message, ensure_ascii=False)
        response_str = json_message + "\n"
        
        logging.info(f"SEND: {response_str}")
        
        sys.stdout.write(response_str)
        sys.stdout.flush()

    def _wait_for_input(self, timeout=1.0):
        """Wait for input to be available on stdin using select"""
        try:
            # Use select to wait for input with timeout
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            return bool(ready)
        except select.error:
            # Fallback for systems where select doesn't work with stdin
            return True

    def _read_message(self):
        """Read JSON-RPC message from standard input"""
        try:
            line = sys.stdin.readline()
            if not line:
                return None
            
            logging.info(f"RECV: {line.strip()}")
            
            return json.loads(line)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON: {line}. Error: {e}")
            return None
        except EOFError:
            logging.info("EOF received, client disconnected")
            return None

    def handle_initialize(self, request):
        """Handle initialize request and return server capabilities"""
        response = {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "protocolVersion": "2025-06-18",
                "serverInfo": {
                    "name": "Python Sampler Server",
                    "version": "0.0.1"
                },
                "capabilities": {
                    "tools": { "listChanged": False },
                    "prompts": None,
                    "resources": None,
                    "sampling": None
                }
            }
        }
        self._send_message(response)

    def handle_initialized(self, request):
        logging.info("Handshake complete.")

    def handle_empty_list(self, request):
        """Common handler that returns empty list"""
        response = {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": None
        }
        self._send_message(response)

    def handle_tools_list(self, request):
        """Return list of available tools"""
        tool_definition = {
            "name": "generate_poem",
            "description": "Analyzes the received text and requests sampling to generate poetic expressions based on it using LLM.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text_to_analyze": {
                        "type": "string",
                        "description": "Text to analyze and express poetically."
                    }
                },
                "required": ["text_to_analyze"]
            }
        }
        response = {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "tools": [tool_definition]
            }
        }
        self._send_message(response)

    def handle_tools_call(self, request):
        """Handle tool calls and trigger sampling"""
        tool_name = request["params"]["name"]
        
        if tool_name == "generate_poem":
            # Store the request to send response later
            text = request["params"]["arguments"]["text_to_analyze"]
            sampling_request_id = self.trigger_sampling(text)
            
            # Associate sampling request ID with original tool request
            self.pending_tool_requests[sampling_request_id] = request

    def handle_sampling_response(self, response):
        """Handle sampling request response and send tool response"""
        request_id = response.get("id")
        if request_id in self.sampling_requests:
            original_text = self.sampling_requests.pop(request_id)
            original_tool_request = self.pending_tool_requests.pop(request_id, None)
            
            if original_tool_request:
                if "result" in response and "content" in response["result"]:
                    content = response["result"]["content"]
                    if content.get("type") == "text":
                        poetic_text = content.get("text")
                        logging.info(f"Poetic expression for '{original_text}':\n{poetic_text}")
                        
                        # Send tool response when poem generation succeeds
                        tool_response = {
                            "jsonrpc": "2.0",
                            "id": original_tool_request["id"],
                            "result": {
                                "content": [{
                                    "type": "text",
                                    "text": f"Poem based on '{original_text}':\n\n{poetic_text}"
                                }]
                            }
                        }
                        self._send_message(tool_response)
                    else:
                        # Content is not in expected format
                        self._send_tool_error_response(original_tool_request, "Unexpected response format from sampling")
                elif "error" in response:
                    logging.error(f"Sampling request failed for '{original_text}': {response['error']}")
                    # Send tool error response for sampling errors
                    self._send_tool_error_response(original_tool_request, f"Sampling failed: {response['error']}")
                else:
                    # Unexpected response format
                    self._send_tool_error_response(original_tool_request, "Unexpected sampling response format")
            else:
                logging.warning(f"Received sampling response but no corresponding tool request found for id: {request_id}")
        else:
            logging.warning(f"Received response for an unknown or already handled sampling request: {response}")

    def _send_tool_error_response(self, original_request, error_message):
        """Send tool error response"""
        error_response = {
            "jsonrpc": "2.0",
            "id": original_request["id"],
            "error": {
                "code": -32603,
                "message": error_message
            }
        }
        self._send_message(error_response)

    def trigger_sampling(self, text_from_tool):
        """Send sampling request to client and return request ID"""
        prompt = f"Please create a short, poetic verse based on the theme '{text_from_tool}'."
        
        request_id = self.request_id_counter
        self.request_id_counter += 1

        sampling_request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "sampling/createMessage",
            "params": {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": prompt
                        }
                    }
                ],
                "systemPrompt": "You are a creative and imaginative poet.",
                "maxTokens": 100,
                "temperature": 0.7
            }
        }
        
        self.sampling_requests[request_id] = text_from_tool
        self._send_message(sampling_request)
        logging.info(f"Sent sampling request for text: '{text_from_tool}' with id: {request_id}")
        
        return request_id  # Return request ID

if __name__ == "__main__":
    server = MCPServer()
    server.run()
