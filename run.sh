#!/bin/bash
# ====================================================================
# AI Football Betting Advisor - One-Click Runner
# ====================================================================
# This script provides easy commands to start, stop, and manage your
# AI Football Betting Advisor system.
# ====================================================================

# Colors for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
echo "  █████╗ ██╗    ███████╗ ██████╗  ██████╗ ████████╗██████╗  █████╗ ██╗     ██╗     "
echo " ██╔══██╗██║    ██╔════╝██╔═══██╗██╔═══██╗╚══██╔══╝██╔══██╗██╔══██╗██║     ██║     "
echo " ███████║██║    █████╗  ██║   ██║██║   ██║   ██║   ██████╔╝███████║██║     ██║     "
echo " ██╔══██║██║    ██╔══╝  ██║   ██║██║   ██║   ██║   ██╔══██╗██╔══██║██║     ██║     "
echo " ██║  ██║██║    ██║     ╚██████╔╝╚██████╔╝   ██║   ██████╔╝██║  ██║███████╗███████╗"
echo " ╚═╝  ╚═╝╚═╝    ╚═╝      ╚═════╝  ╚═════╝    ╚═╝   ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝"
echo -e "${GREEN}       BETTING ADVISOR${NC}"
echo -e "${YELLOW}       Value-Based Football Betting Recommendations${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed. Please install docker-compose first.${NC}"
    exit 1
fi

# Functions
start_system() {
    echo -e "${BLUE}Starting AI Football Betting Advisor...${NC}"
    docker-compose up -d
    echo -e "${GREEN}System is now running!${NC}"
    check_status
}

stop_system() {
    echo -e "${YELLOW}Stopping AI Football Betting Advisor...${NC}"
    docker-compose down
    echo -e "${GREEN}System stopped.${NC}"
}

restart_system() {
    echo -e "${YELLOW}Restarting AI Football Betting Advisor...${NC}"
    docker-compose restart
    echo -e "${GREEN}System restarted!${NC}"
    check_status
}

check_status() {
    echo -e "${BLUE}Checking system status...${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E 'football-betting|redis'
    
    # Check if advisor container is running
    if [ $(docker ps -q -f name=football-betting-advisor) ]; then
        echo -e "${GREEN}✓ Advisor is running${NC}"
        
        # Get health status
        health=$(docker inspect --format='{{.State.Health.Status}}' football-betting-advisor)
        echo -e "${BLUE}Health status: ${health}${NC}"
        
        # Show logs snippet
        echo -e "${BLUE}Recent logs:${NC}"
        docker logs --tail 5 football-betting-advisor
    else
        echo -e "${RED}✗ Advisor is not running${NC}"
    fi
}

view_logs() {
    echo -e "${BLUE}Showing logs for AI Football Betting Advisor...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to exit logs${NC}"
    docker logs -f football-betting-advisor
}

run_shadow_mode() {
    echo -e "${BLUE}Running in shadow mode (no real bets)...${NC}"
    echo -e "${YELLOW}This will simulate betting without risking real money${NC}"
    
    days=14
    bankroll=1000
    
    echo -e "Days to simulate: $days"
    echo -e "Virtual bankroll: $bankroll"
    
    docker exec football-betting-advisor python shadow_mode.py --days $days --bankroll $bankroll
    
    echo -e "${GREEN}Shadow mode started. Check Telegram for updates or use 'view_logs' to monitor progress.${NC}"
}

display_help() {
    echo -e "${BLUE}AI Football Betting Advisor - Command Options:${NC}"
    echo ""
    echo -e "${GREEN}./run.sh${NC}               - Show this menu"
    echo -e "${GREEN}./run.sh start${NC}         - Start the system"
    echo -e "${GREEN}./run.sh stop${NC}          - Stop the system"
    echo -e "${GREEN}./run.sh restart${NC}       - Restart the system"
    echo -e "${GREEN}./run.sh status${NC}        - Check system status"
    echo -e "${GREEN}./run.sh logs${NC}          - View system logs"
    echo -e "${GREEN}./run.sh shadow${NC}        - Run in shadow mode (test without real money)"
    echo -e "${GREEN}./run.sh menu${NC}          - Show interactive menu"
    echo ""
}

show_menu() {
    clear
    echo -e "${BLUE}AI Football Betting Advisor - Management Menu${NC}"
    echo ""
    echo -e "${GREEN}1)${NC} Start system"
    echo -e "${GREEN}2)${NC} Stop system"
    echo -e "${GREEN}3)${NC} Restart system"
    echo -e "${GREEN}4)${NC} Check system status"
    echo -e "${GREEN}5)${NC} View logs"
    echo -e "${GREEN}6)${NC} Run in shadow mode"
    echo -e "${GREEN}7)${NC} Generate performance report"
    echo -e "${GREEN}8)${NC} Re-train ML model"
    echo -e "${GREEN}9)${NC} Exit"
    echo ""
    echo -e "Enter your choice: "
    read -r choice
    
    case $choice in
        1) start_system ;;
        2) stop_system ;;
        3) restart_system ;;
        4) check_status ;;
        5) view_logs ;;
        6) run_shadow_mode ;;
        7) docker exec football-betting-advisor python main.py --report ;;
        8) docker exec football-betting-advisor python main.py --retrain ;;
        9) exit 0 ;;
        *) echo -e "${RED}Invalid option${NC}" ;;
    esac
    
    echo ""
    echo -e "${YELLOW}Press ENTER to return to menu${NC}"
    read -r
    show_menu
}

# Check for arguments
if [ $# -eq 0 ]; then
    # No arguments provided, either show menu (if running interactively) or start the system
    if [ -t 0 ]; then
        show_menu
    else
        start_system
    fi
else
    case "$1" in
        start)
            start_system
            ;;
        stop)
            stop_system
            ;;
        restart)
            restart_system
            ;;
        status)
            check_status
            ;;
        logs)
            view_logs
            ;;
        shadow)
            run_shadow_mode
            ;;
        menu)
            show_menu
            ;;
        help)
            display_help
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            display_help
            ;;
    esac
fi 