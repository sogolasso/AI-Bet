#!/bin/bash
# Run the Telegram Shadow Mode with specified parameters

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================================="
echo "              AI Football Betting Advisor - Telegram Shadow Mode"
echo -e "===================================================================${NC}"
echo

# Check if Python is installed with correct version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8 or later and try again${NC}"
    exit 1
fi

# Check Python version
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if (( $(echo "$PY_VERSION < 3.8" | bc -l) )); then
    echo -e "${YELLOW}Warning: Python 3.8 or later is recommended. Current version: $PY_VERSION${NC}"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for required directories
mkdir -p logs
mkdir -p data/shadow
mkdir -p utils

# Check for required files
if [[ ! -f ".env" ]]; then
    echo -e "${YELLOW}Warning: .env file not found. Configuration may be incomplete."
    echo -e "You should run setup.py first to initialize the environment.${NC}"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check for the Telegram bot token in .env
if [[ -f ".env" ]] && grep -q "TELEGRAM_BOT_TOKEN=your_bot_token_here" .env; then
    echo -e "${YELLOW}Warning: Telegram bot token not set in .env file."
    echo -e "You need to update the TELEGRAM_BOT_TOKEN value in the .env file.${NC}"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Default parameters
DURATION=14
BANKROLL=100
QUICK=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --duration|-d)
            DURATION="$2"
            shift 2
            ;;
        --bankroll|-b)
            BANKROLL="$2"
            shift 2
            ;;
        --quick|-q)
            QUICK="--quick"
            shift
            ;;
        --help|-h)
            echo "Usage: ./run_telegram_shadow.sh [OPTIONS]"
            echo
            echo "Options:"
            echo "  -d, --duration NUMBER  Simulation duration in days (default: 14)"
            echo "  -b, --bankroll NUMBER  Initial bankroll amount (default: 100)"
            echo "  -q, --quick            Enable quick mode (faster simulation)"
            echo "  -h, --help             Show this help message"
            echo
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown parameter: $1${NC}"
            shift
            ;;
    esac
done

echo -e "${GREEN}Starting Telegram Shadow Mode with:${NC}"
echo "  🕒 Duration: $DURATION days"
echo "  💰 Bankroll: \$$BANKROLL"
[[ -n "$QUICK" ]] && echo "  ⚡ Quick mode: Enabled"

echo
echo "Press Ctrl+C to stop the simulation at any time"
echo
echo "This terminal will display the simulation progress..."
echo

# Install any missing requirements
python3 -c "import telegram" &> /dev/null
if [[ $? -ne 0 ]]; then
    echo -e "${BLUE}Installing required packages...${NC}"
    pip3 install python-telegram-bot==13.7 python-dotenv
fi

# Make scripts executable if needed
chmod +x ./run_telegram_shadow.py
chmod +x ./get_telegram_id.py 2>/dev/null

# Run the shadow mode
python3 run_telegram_shadow.py --duration "$DURATION" --bankroll "$BANKROLL" $QUICK

if [[ $? -ne 0 ]]; then
    echo
    echo -e "${RED}❌ Shadow mode exited with errors. Check the logs for details."
    echo -e "   See logs/telegram_shadow_mode.log for more information.${NC}"
    exit 1
else
    echo
    echo -e "${GREEN}✅ Shadow mode completed successfully."
    echo -e "   Results saved to data/shadow/ directory.${NC}"
    exit 0
fi 