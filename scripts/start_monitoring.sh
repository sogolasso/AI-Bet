#!/bin/bash

# ANSI color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}    BETTING ADVISOR MONITORING PROXY        ${NC}"
echo -e "${BLUE}=============================================${NC}"
echo
echo -e "This script will start a web-based proxy to access Grafana and Prometheus."
echo
echo -e "Requirements:"
echo -e " - Python 3.6 or higher"
echo -e " - kubectl configured and accessible"
echo
echo -e "The web interface will open automatically in your browser."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 is not installed or not in PATH${NC}"
    echo -e "Please install Python 3.6 or higher and try again"
    exit 1
fi

# Make sure the proxy script is executable
chmod +x "$(dirname "$0")/monitoring_proxy.py"

# Run the monitoring proxy
python3 "$(dirname "$0")/monitoring_proxy.py" 