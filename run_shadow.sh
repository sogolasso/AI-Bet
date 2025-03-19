#!/bin/bash
# Shadow Mode Launcher for AI Football Betting Advisor

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================================="
echo "              AI Football Betting Advisor - Shadow Mode"
echo -e "===================================================================${NC}"
echo

echo -e "${BLUE}This will run the AI Football Betting Advisor in shadow mode."
echo -e "Shadow mode simulates betting without risking real money.${NC}"
echo
echo -e "${YELLOW}Press Ctrl+C at any time to exit.${NC}"
echo

# Make scripts executable
chmod +x all_in_one.py run_shadow.py 2>/dev/null

# Run the shadow mode launcher
./run_shadow.py "$@"
EXIT_CODE=$?

echo
if [ $EXIT_CODE -ne 0 ]; then
    echo -e "${RED}Shadow mode exited with errors. See logs for details.${NC}"
else
    echo -e "${GREEN}Shadow mode completed successfully.${NC}"
fi

echo
read -p "Press Enter to exit..." 