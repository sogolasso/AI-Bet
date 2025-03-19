#!/usr/bin/env python3
"""
Betting Advisor Monitoring Proxy

This script creates a simple web proxy that forwards requests to Grafana and Prometheus
running in Kubernetes, making them accessible through a regular HTTP server.
"""

import os
import sys
import time
import argparse
import threading
import subprocess
import http.server
import socketserver
import urllib.request
import urllib.error
from http import HTTPStatus
import webbrowser

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_colored(text, color):
    """Print colored text to terminal."""
    print(f"{color}{text}{Colors.ENDC}")

def check_kubectl():
    """Check if kubectl is installed and accessible."""
    try:
        subprocess.run(["kubectl", "version", "--client"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def check_kubernetes_connection():
    """Check if connected to a Kubernetes cluster."""
    try:
        result = subprocess.run(["kubectl", "get", "nodes"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               check=True)
        return True
    except subprocess.SubprocessError:
        return False

def get_namespaces():
    """Get list of available namespaces."""
    try:
        result = subprocess.run(["kubectl", "get", "namespaces", "-o", "name"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True,
                               check=True)
        namespaces = [ns.replace('namespace/', '') for ns in result.stdout.strip().split('\n')]
        return namespaces
    except subprocess.SubprocessError:
        return []

def check_service_exists(service, namespace):
    """Check if a Kubernetes service exists."""
    try:
        result = subprocess.run(["kubectl", "get", "service", service, "-n", namespace], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               check=True)
        return True
    except subprocess.SubprocessError:
        return False

def start_port_forward(service, namespace, local_port, service_port):
    """Start kubectl port-forward as a background process."""
    # Kill any existing process using the port
    try:
        if sys.platform == 'win32':
            subprocess.run(f"FOR /F \"tokens=5\" %P IN ('netstat -aon ^| find \":{local_port}\"') DO taskkill /F /PID %P",
                          shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            subprocess.run(f"lsof -i :{local_port} | awk 'NR>1 {{print $2}}' | xargs -r kill -9",
                          shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.SubprocessError:
        pass
    
    # Start port forwarding
    cmd = ["kubectl", "port-forward", f"svc/{service}", f"{local_port}:{service_port}", "-n", namespace]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for the port-forward to start
    time.sleep(2)
    
    # Check if port-forward is running
    if process.poll() is not None:
        return None
    
    return process

def is_port_available(port):
    """Check if a port is available for use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for proxying requests to Kubernetes services."""
    
    def __init__(self, *args, **kwargs):
        self.grafana_port = int(os.environ.get("GRAFANA_PORT", 3000))
        self.prometheus_port = int(os.environ.get("PROMETHEUS_PORT", 9090))
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path.startswith('/grafana'):
            target_path = self.path[8:] or '/'
            self.proxy_request(f"http://localhost:{self.grafana_port}{target_path}", "grafana")
        elif self.path.startswith('/prometheus'):
            target_path = self.path[11:] or '/'
            self.proxy_request(f"http://localhost:{self.prometheus_port}{target_path}", "prometheus")
        elif self.path == '/':
            self.send_dashboard()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Path not found")
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path.startswith('/grafana'):
            target_path = self.path[8:] or '/'
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            self.proxy_request(f"http://localhost:{self.grafana_port}{target_path}", "grafana", post_data)
        elif self.path.startswith('/prometheus'):
            target_path = self.path[11:] or '/'
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            self.proxy_request(f"http://localhost:{self.prometheus_port}{target_path}", "prometheus", post_data)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Path not found")
    
    def proxy_request(self, target_url, service, post_data=None):
        """Proxy a request to a target URL."""
        try:
            # Create the request
            request = urllib.request.Request(target_url)
            
            # Copy headers from the original request
            for header in self.headers:
                if header.lower() not in ('host', 'connection'):
                    request.add_header(header, self.headers[header])
            
            # Add POST data if provided
            if post_data:
                request.data = post_data
            
            # Make the request
            with urllib.request.urlopen(request) as response:
                # Copy response status and headers
                self.send_response(response.status)
                for header in response.headers:
                    if header.lower() not in ('connection', 'transfer-encoding'):
                        self.send_header(header, response.headers[header])
                self.end_headers()
                
                # Copy response body
                self.wfile.write(response.read())
        
        except urllib.error.URLError as e:
            if service == "grafana":
                self.send_error(HTTPStatus.BAD_GATEWAY, f"Error connecting to Grafana: {str(e)}")
            else:
                self.send_error(HTTPStatus.BAD_GATEWAY, f"Error connecting to Prometheus: {str(e)}")
    
    def send_dashboard(self):
        """Send the dashboard HTML page."""
        dashboard_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Betting Advisor Monitoring</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f7fc;
                }}
                .header {{
                    background-color: #1a2c42;
                    color: white;
                    padding: 1rem;
                    text-align: center;
                }}
                .container {{
                    max-width: 800px;
                    margin: 2rem auto;
                    padding: 1rem;
                }}
                .card {{
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    padding: 1.5rem;
                    margin-bottom: 1.5rem;
                    transition: transform 0.3s ease;
                }}
                .card:hover {{
                    transform: translateY(-5px);
                }}
                .card h2 {{
                    margin-top: 0;
                    color: #1a2c42;
                }}
                .btn {{
                    display: inline-block;
                    background-color: #2c6ecf;
                    color: white;
                    padding: 0.75rem 1.5rem;
                    border-radius: 4px;
                    text-decoration: none;
                    font-weight: bold;
                    transition: background-color 0.3s ease;
                }}
                .btn:hover {{
                    background-color: #1a53a9;
                }}
                .status {{
                    display: inline-block;
                    padding: 0.25rem 0.5rem;
                    border-radius: 4px;
                    margin-left: 1rem;
                }}
                .status.online {{
                    background-color: #d4edda;
                    color: #155724;
                }}
                .status.offline {{
                    background-color: #f8d7da;
                    color: #721c24;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 2rem;
                    padding: 1rem;
                    color: #6c757d;
                    font-size: 0.9rem;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Betting Advisor Monitoring</h1>
            </div>
            <div class="container">
                <div class="card">
                    <h2>Grafana <span id="grafana-status" class="status">Checking...</span></h2>
                    <p>Access Grafana dashboards for visualizing betting performance metrics, ROI by league, and model accuracy.</p>
                    <a href="/grafana" class="btn" target="_blank">Open Grafana</a>
                </div>
                <div class="card">
                    <h2>Prometheus <span id="prometheus-status" class="status">Checking...</span></h2>
                    <p>Access Prometheus for querying raw metrics, setting up alerts, and monitoring system performance.</p>
                    <a href="/prometheus" class="btn" target="_blank">Open Prometheus</a>
                </div>
                <div class="card">
                    <h2>Instructions</h2>
                    <p>This proxy provides access to your Kubernetes monitoring services through a local web interface.</p>
                    <ul>
                        <li>Click on the buttons above to access each service</li>
                        <li>The services are proxied through this web server</li>
                        <li>Keep this window open to maintain access</li>
                    </ul>
                </div>
            </div>
            <div class="footer">
                <p>Betting Advisor Monitoring Proxy | Port {self.server.server_port}</p>
            </div>
            <script>
                function checkService(service, port) {{
                    fetch(`http://localhost:${{port}}`)
                        .then(response => {{
                            const statusElem = document.getElementById(`${{service}}-status`);
                            statusElem.innerText = "Online";
                            statusElem.className = "status online";
                        }})
                        .catch(error => {{
                            const statusElem = document.getElementById(`${{service}}-status`);
                            statusElem.innerText = "Offline";
                            statusElem.className = "status offline";
                        }});
                }}
                
                // Check services status periodically
                setInterval(() => {{
                    checkService('grafana', {self.grafana_port});
                    checkService('prometheus', {self.prometheus_port});
                }}, 5000);
                
                // Initial check
                checkService('grafana', {self.grafana_port});
                checkService('prometheus', {self.prometheus_port});
            </script>
        </body>
        </html>
        """
        
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(dashboard_html))
        self.end_headers()
        self.wfile.write(dashboard_html.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to suppress logging."""
        return


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Betting Advisor Monitoring Proxy')
    parser.add_argument('--port', type=int, default=8080, help='Port for the proxy server (default: 8080)')
    parser.add_argument('--grafana-port', type=int, default=3000, help='Local port for Grafana (default: 3000)')
    parser.add_argument('--prometheus-port', type=int, default=9090, help='Local port for Prometheus (default: 9090)')
    parser.add_argument('--namespace', type=str, default='', help='Kubernetes namespace (default: auto-detect)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser automatically')
    args = parser.parse_args()
    
    print_colored("\n===============================================", Colors.BLUE)
    print_colored("    BETTING ADVISOR MONITORING PROXY", Colors.BLUE)
    print_colored("===============================================\n", Colors.BLUE)
    
    # Check kubectl installation
    print_colored("Checking kubectl installation...", Colors.YELLOW)
    if not check_kubectl():
        print_colored("❌ kubectl not found! Please install kubectl first.", Colors.RED)
        sys.exit(1)
    print_colored("✅ kubectl found", Colors.GREEN)
    
    # Check Kubernetes connection
    print_colored("\nChecking Kubernetes connection...", Colors.YELLOW)
    if not check_kubernetes_connection():
        print_colored("❌ Not connected to a Kubernetes cluster!", Colors.RED)
        sys.exit(1)
    print_colored("✅ Connected to Kubernetes cluster", Colors.GREEN)
    
    # Determine namespace
    namespace = args.namespace
    if not namespace:
        print_colored("\nDetecting monitoring namespace...", Colors.YELLOW)
        namespaces = get_namespaces()
        
        if 'monitoring' in namespaces:
            namespace = 'monitoring'
            print_colored(f"✅ Found monitoring namespace: {namespace}", Colors.GREEN)
        elif 'betting-advisor' in namespaces:
            namespace = 'betting-advisor'
            print_colored(f"✅ Found betting-advisor namespace: {namespace}", Colors.GREEN)
        else:
            print_colored("❌ Could not auto-detect namespace", Colors.RED)
            print_colored("\nAvailable namespaces:", Colors.YELLOW)
            for ns in namespaces:
                print(f"  - {ns}")
            
            namespace = input("\nPlease enter the namespace to use: ")
            if not namespace:
                print_colored("No namespace provided. Exiting.", Colors.RED)
                sys.exit(1)
    
    # Check if services exist
    print_colored(f"\nChecking for Grafana in namespace '{namespace}'...", Colors.YELLOW)
    grafana_exists = check_service_exists('grafana', namespace)
    if grafana_exists:
        print_colored("✅ Grafana service found", Colors.GREEN)
    else:
        print_colored("❌ Grafana service not found!", Colors.RED)
    
    print_colored(f"\nChecking for Prometheus in namespace '{namespace}'...", Colors.YELLOW)
    prometheus_exists = check_service_exists('prometheus', namespace)
    if prometheus_exists:
        print_colored("✅ Prometheus service found", Colors.GREEN)
    else:
        print_colored("❌ Prometheus service not found!", Colors.RED)
    
    if not grafana_exists and not prometheus_exists:
        print_colored("\n❌ Neither Grafana nor Prometheus services found in the namespace!", Colors.RED)
        print_colored("Please check the namespace and try again.", Colors.RED)
        sys.exit(1)
    
    # Start port forwarding
    print_colored("\n===============================================", Colors.BLUE)
    print_colored("    STARTING PORT FORWARDING", Colors.BLUE)
    print_colored("===============================================\n", Colors.BLUE)
    
    processes = []
    
    if grafana_exists:
        print_colored(f"Starting port forwarding for Grafana on port {args.grafana_port}...", Colors.YELLOW)
        grafana_process = start_port_forward('grafana', namespace, args.grafana_port, 3000)
        if grafana_process and grafana_process.poll() is None:
            print_colored(f"✅ Grafana port forwarding started (port {args.grafana_port})", Colors.GREEN)
            processes.append(grafana_process)
        else:
            print_colored(f"❌ Failed to start Grafana port forwarding!", Colors.RED)
    
    if prometheus_exists:
        print_colored(f"Starting port forwarding for Prometheus on port {args.prometheus_port}...", Colors.YELLOW)
        prometheus_process = start_port_forward('prometheus', namespace, args.prometheus_port, 9090)
        if prometheus_process and prometheus_process.poll() is None:
            print_colored(f"✅ Prometheus port forwarding started (port {args.prometheus_port})", Colors.GREEN)
            processes.append(prometheus_process)
        else:
            print_colored(f"❌ Failed to start Prometheus port forwarding!", Colors.RED)
    
    if not processes:
        print_colored("\n❌ Failed to start any port forwarding processes!", Colors.RED)
        sys.exit(1)
    
    # Set environment variables for the handler
    os.environ["GRAFANA_PORT"] = str(args.grafana_port)
    os.environ["PROMETHEUS_PORT"] = str(args.prometheus_port)
    
    # Start HTTP server
    print_colored("\n===============================================", Colors.BLUE)
    print_colored("    STARTING WEB PROXY", Colors.BLUE)
    print_colored("===============================================\n", Colors.BLUE)
    
    server_port = args.port
    while not is_port_available(server_port):
        print_colored(f"Port {server_port} is already in use. Trying next port...", Colors.YELLOW)
        server_port += 1
    
    try:
        with socketserver.TCPServer(("", server_port), ProxyHandler) as httpd:
            print_colored(f"✅ Web proxy started on port {server_port}", Colors.GREEN)
            print_colored(f"\n🌐 Access dashboard at: http://localhost:{server_port}", Colors.CYAN)
            print_colored(f"🌐 Access Grafana at: http://localhost:{server_port}/grafana", Colors.CYAN)
            print_colored(f"🌐 Access Prometheus at: http://localhost:{server_port}/prometheus", Colors.CYAN)
            print_colored("\n📋 Keep this window open to maintain access", Colors.YELLOW)
            print_colored("📋 Press Ctrl+C to stop the proxy\n", Colors.YELLOW)
            
            # Open browser automatically
            if not args.no_browser:
                webbrowser.open(f"http://localhost:{server_port}")
            
            # Run the server until interrupted
            httpd.serve_forever()
    
    except KeyboardInterrupt:
        print_colored("\nShutting down the proxy...", Colors.YELLOW)
    
    finally:
        # Terminate port forwarding processes
        for process in processes:
            process.terminate()
        
        print_colored("✅ All services terminated. Goodbye!", Colors.GREEN)


if __name__ == "__main__":
    main() 