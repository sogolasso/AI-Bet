#!/bin/bash
# Production Mode Launcher for AI Football Betting Advisor

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================================="
echo "              AI Football Betting Advisor - Production Mode"
echo -e "===================================================================${NC}"
echo

echo -e "${BLUE}This will run the AI Football Betting Advisor in production mode.${NC}"
echo
echo -e "${RED}WARNING: Production mode will place REAL bets if configured to do so."
echo -e "         Make sure you have set up your configuration correctly.${NC}"
echo

# Confirm with user
read -p "Are you sure you want to continue? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Operation cancelled by user.${NC}"
    exit 0
fi

echo
echo -e "${BLUE}Starting production mode...${NC}"
echo -e "${YELLOW}Press Ctrl+C at any time to exit.${NC}"
echo

# Make scripts executable
chmod +x all_in_one.py run_production.py 2>/dev/null

# Run the production mode launcher
./run_production.py "$@"
EXIT_CODE=$?

echo
if [ $EXIT_CODE -ne 0 ]; then
    echo -e "${RED}Production mode exited with errors. See logs for details.${NC}"
else
    echo -e "${GREEN}Production mode completed successfully.${NC}"
fi

echo
read -p "Press Enter to exit..." 