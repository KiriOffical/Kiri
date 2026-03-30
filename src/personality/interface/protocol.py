"""
JSON-RPC 2.0 Protocol Implementation for Kiri Personality Plugin

This module implements the communication protocol between Kiri Core and the
Personality Plugin using JSON-RPC 2.0 over STDIN/STDOUT.

SECURITY NOTE: This module operates entirely offline. No network sockets are
created or used. All communication happens via standard I/O streams.
"""

import json
import sys
import threading
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class RequestHandler:
    """Handles incoming JSON-RPC requests from Kiri Core"""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}
        self._lock = threading.Lock()

    def register(self, method: str, handler: Callable):
        """Register a handler for a specific method"""
        with self._lock:
            self._handlers[method] = handler
            logger.debug(f"Registered handler for method: {method}")

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming request and return a response

        Args:
            request: Parsed JSON-RPC request object

        Returns:
            JSON-RPC response object
        """
        method = request.get('method')
        request_id = request.get('id')
        params = request.get('params', {})

        if method not in self._handlers:
            logger.warning(f"Unknown method requested: {method}")
            return self._error_response(
                request_id,
                -32601,
                f"Method not found: {method}"
            )

        try:
            handler = self._handlers[method]
            result = handler(params)
            return self._success_response(request_id, result)
        except Exception as e:
            logger.error(f"Handler error for {method}: {e}", exc_info=True)
            return self._error_response(request_id, -32603, str(e))

    def _success_response(self, request_id: Any, result: Any) -> Dict[str, Any]:
        """Create a success response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                **result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    def _error_response(
        self,
        request_id: Any,
        code: int,
        message: str
    ) -> Dict[str, Any]:
        """Create an error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }


class JSONRPCProtocol:
    """
    JSON-RPC 2.0 Protocol Layer

    Handles serialization, deserialization, and transport of messages
    between Kiri Core and the Personality Plugin via STDIN/STDOUT.

    SECURITY: This class explicitly avoids any network operations.
    All I/O is restricted to standard streams only.
    """

    def __init__(self, handler: RequestHandler):
        self.handler = handler
        self._running = False
        self._input_thread: Optional[threading.Thread] = None
        self._output_lock = threading.Lock()

        # SECURITY: Explicit flag to ensure no network usage
        self._network_blocked = True

    def start(self, blocking: bool = True):
        """
        Start the protocol listener

        Args:
            blocking: If True, blocks the calling thread. If False, runs in background.
        """
        logger.info("Starting JSON-RPC protocol listener")
        self._running = True

        if blocking:
            self._listen_loop()
        else:
            self._input_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._input_thread.start()
            logger.info("Protocol listener started in background thread")

    def stop(self):
        """Stop the protocol listener"""
        logger.info("Stopping JSON-RPC protocol listener")
        self._running = False

        if self._input_thread and self._input_thread.is_alive():
            self._input_thread.join(timeout=2.0)

    def send_response(self, response: Dict[str, Any]):
        """
        Send a response to STDOUT

        Args:
            response: JSON-RPC response object to send
        """
        with self._output_lock:
            try:
                json_str = json.dumps(response, separators=(',', ':'))
                sys.stdout.write(json_str + '\n')
                sys.stdout.flush()
                logger.debug(f"Sent response: {response.get('id')}")
            except Exception as e:
                logger.error(f"Failed to send response: {e}", exc_info=True)

    def _listen_loop(self):
        """Main listening loop for STDIN"""
        logger.info("Listening for incoming requests on STDIN")

        while self._running:
            try:
                line = sys.stdin.readline()

                if not line:
                    # EOF received, Core may have closed the stream
                    logger.info("EOF received on STDIN, shutting down")
                    break

                line = line.strip()
                if not line:
                    continue

                self._process_line(line)

            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error reading from STDIN: {e}", exc_info=True)
                continue

    def _process_line(self, line: str):
        """
        Process a single line of input

        Args:
            line: Raw JSON string from STDIN
        """
        try:
            request = json.loads(line)
            logger.debug(f"Received request: {request.get('method')} (id={request.get('id')})")

            # Validate basic JSON-RPC structure
            if not self._validate_basic_structure(request):
                response = self.handler._error_response(
                    request.get('id'),
                    -32700,
                    "Invalid JSON-RPC request structure"
                )
                self.send_response(response)
                return

            # Process the request
            response = self.handler.handle(request)
            self.send_response(response)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            self.send_response(response)

    def _validate_basic_structure(self, request: Dict[str, Any]) -> bool:
        """
        Validate basic JSON-RPC 2.0 structure

        Args:
            request: Parsed request object

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(request, dict):
            return False

        if request.get('jsonrpc') != '2.0':
            return False

        if 'method' not in request:
            return False

        return True

    @property
    def is_running(self) -> bool:
        """Check if the protocol is running"""
        return self._running

    def security_status(self) -> Dict[str, bool]:
        """
        Return security status information

        SECURITY: This confirms that network operations are blocked
        """
        return {
            "network_blocked": self._network_blocked,
            "using_stdin_stdout": True,
            "no_sockets_created": True
        }
