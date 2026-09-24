"""HTTP Service exposing /solve and /health endpoints."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from service.agent.solver import AutonomousSolver
from service.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("autonomous_service.app")


class ServiceHandler(BaseHTTPRequestHandler):
    solver = AutonomousSolver()

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/solve":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_error(400, "Empty request body")
                return

            try:
                body = self.rfile.read(content_length).decode("utf-8")
                payload: dict[str, Any] = json.loads(body)
            except Exception as e:
                self.send_error(400, f"Invalid JSON: {e}")
                return

            request_id = payload.get("request_id", "req-unknown")
            repo_archive_b64 = payload.get("repo_archive_b64", "")
            task_description = payload.get("task", "")
            deadline_seconds = float(payload.get("deadline_seconds", 240.0))

            if not repo_archive_b64:
                self.send_error(400, "Missing 'repo_archive_b64'")
                return

            try:
                result = self.solver.solve(
                    request_id=request_id,
                    repo_archive_b64=repo_archive_b64,
                    task_description=task_description,
                    deadline_seconds=deadline_seconds
                )
                response_bytes = json.dumps(result).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response_bytes)))
                self.end_headers()
                self.wfile.write(response_bytes)
            except Exception as e:
                logger.exception(f"Error handling /solve for {request_id}")
                self.send_error(500, f"Internal error: {e}")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        logger.info(f"{self.address_string()} - {format % args}")


def run_server(host: str = config.host, port: int = config.port) -> None:
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, ServiceHandler)
    logger.info(f"Starting autonomous code-change service on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous Code-Change Service")
    parser.add_argument("--host", default=config.host, help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=config.port, help="Bind port (default: 8000)")
    args = parser.parse_args()
    run_server(args.host, args.port)
