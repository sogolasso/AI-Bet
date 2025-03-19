#!/usr/bin/env python3
"""
Health Check for AI Football Betting Advisor

This script provides a simple HTTP server that responds to health check requests.
It is used by Docker's HEALTHCHECK instruction to verify that the application
is still running and responsive.
"""

import os
import sys
import json
import logging
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health check endpoints."""
    
    def _set_headers(self, status_code=200):
        """Set response headers."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health':
            # Basic health check
            self._set_headers()
            response = {
                'status': 'ok',
                'timestamp': datetime.now().isoformat(),
                'service': 'ai-football-betting-advisor'
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
        elif self.path == '/health/detailed':
            # More detailed health check with component status
            try:
                # Check if main services are running
                from main import check_advisor_status
                status = check_advisor_status()
                
                self._set_headers()
                response = {
                    'status': 'ok' if status['healthy'] else 'degraded',
                    'timestamp': datetime.now().isoformat(),
                    'service': 'ai-football-betting-advisor',
                    'components': status['components'],
                    'uptime': status['uptime']
                }
            except ImportError:
                # Fallback if main module can't be imported
                self._set_headers(status_code=500)
                response = {
                    'status': 'error',
                    'timestamp': datetime.now().isoformat(),
                    'service': 'ai-football-betting-advisor',
                    'error': 'Could not import main module'
                }
            except Exception as e:
                self._set_headers(status_code=500)
                response = {
                    'status': 'error',
                    'timestamp': datetime.now().isoformat(),
                    'service': 'ai-football-betting-advisor',
                    'error': str(e)
                }
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            # 404 for all other paths
            self._set_headers(status_code=404)
            response = {
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'service': 'ai-football-betting-advisor',
                'error': 'Not found'
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override log message to use our logger."""
        logger.debug(f"{self.client_address[0]} - {args[0]}")


def run_server(host='0.0.0.0', port=8080):
    """Run the health check server."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    logger.info(f"Starting health check server on {host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping health check server")
        httpd.server_close()


def main():
    """Main entry point for health check server."""
    parser = argparse.ArgumentParser(description='AI Football Betting Advisor Health Check Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    
    args = parser.parse_args()
    
    # Configure logging
    if os.environ.get('DEBUG') == 'true':
        logging.getLogger().setLevel(logging.DEBUG)
    
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main() 