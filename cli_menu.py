#!/usr/bin/env python3
"""
Interactive CLI Menu for AI Football Betting Advisor

This script provides an easy-to-use command-line interface for managing the
AI Football Betting Advisor without needing to know specific commands.
"""

import os
import sys
import subprocess
import platform
import time
import json
from datetime import datetime
import argparse
import shutil

# Terminal colors
class Colors:
    """Terminal colors for better UI."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def is_supported():
        """Check if colors are supported in the terminal."""
        return platform.system() != "Windows" or "WT_SESSION" in os.environ

# Clear screen function
def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if platform.system() == 'Windows' else 'clear')

# Format text with color
def colorize(text, color):
    """Apply color to text if supported."""
    if Colors.is_supported():
        return f"{color}{text}{Colors.ENDC}"
    return text

# Get terminal width
def get_terminal_width():
    """Get the width of the terminal."""
    try:
        return shutil.get_terminal_size().columns
    except (AttributeError, ValueError, OSError):
        return 80

# Docker command executor
def run_docker_command(command, capture_output=False):
    """Run a Docker command and optionally capture output."""
    try:
        full_command = f"docker {command}"
        if capture_output:
            result = subprocess.run(
                full_command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            return result
        else:
            subprocess.run(full_command, shell=True)
            return None
    except subprocess.SubprocessError as e:
        print(colorize(f"Error executing command: {e}", Colors.RED))
        return None

# Docker Compose command executor
def run_docker_compose_command(command, capture_output=False):
    """Run a Docker Compose command and optionally capture output."""
    try:
        full_command = f"docker-compose {command}"
        if capture_output:
            result = subprocess.run(
                full_command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            return result
        else:
            subprocess.run(full_command, shell=True)
            return None
    except subprocess.SubprocessError as e:
        print(colorize(f"Error executing command: {e}", Colors.RED))
        return None

# Application status check
def check_status():
    """Check the status of the AI Football Betting Advisor."""
    clear_screen()
    print_header()
    
    print(colorize("Checking system status...", Colors.BLUE))
    
    # Check if advisor container is running
    result = run_docker_command("ps -q -f name=football-betting-advisor", capture_output=True)
    if result and result.stdout.strip():
        print(colorize("✅ Advisor container is running", Colors.GREEN))
        
        # Get health status
        health_result = run_docker_command(
            "inspect --format='{{.State.Health.Status}}' football-betting-advisor",
            capture_output=True
        )
        if health_result and health_result.stdout.strip():
            health_status = health_result.stdout.strip()
            color = Colors.GREEN if health_status == 'healthy' else Colors.YELLOW
            print(colorize(f"Health status: {health_status}", color))
        
        # Check Redis
        redis_result = run_docker_command("ps -q -f name=football-betting-redis", capture_output=True)
        if redis_result and redis_result.stdout.strip():
            print(colorize("✅ Redis container is running", Colors.GREEN))
        else:
            print(colorize("❌ Redis container is not running", Colors.RED))
        
        # Show detailed application status
        print(colorize("\nDetailed application status:", Colors.BLUE))
        run_docker_command("exec football-betting-advisor python main.py --status")
    else:
        print(colorize("❌ Advisor container is not running", Colors.RED))
    
    # Show running containers
    print(colorize("\nRunning containers:", Colors.BLUE))
    run_docker_command("ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'football-betting|redis'")
    
    input(colorize("\nPress Enter to continue...", Colors.YELLOW))

# Start the system
def start_system():
    """Start the AI Football Betting Advisor."""
    clear_screen()
    print_header()
    
    print(colorize("Starting AI Football Betting Advisor...", Colors.BLUE))
    run_docker_compose_command("up -d")
    print(colorize("System started!", Colors.GREEN))
    
    time.sleep(2)
    check_status()

# Stop the system
def stop_system():
    """Stop the AI Football Betting Advisor."""
    clear_screen()
    print_header()
    
    print(colorize("Stopping AI Football Betting Advisor...", Colors.YELLOW))
    run_docker_compose_command("down")
    print(colorize("System stopped.", Colors.GREEN))
    
    input(colorize("\nPress Enter to continue...", Colors.YELLOW))

# Restart the system
def restart_system():
    """Restart the AI Football Betting Advisor."""
    clear_screen()
    print_header()
    
    print(colorize("Restarting AI Football Betting Advisor...", Colors.YELLOW))
    run_docker_compose_command("restart")
    print(colorize("System restarted!", Colors.GREEN))
    
    time.sleep(2)
    check_status()

# View logs
def view_logs():
    """View the logs of the AI Football Betting Advisor."""
    clear_screen()
    print_header()
    
    print(colorize("Showing logs for AI Football Betting Advisor...", Colors.BLUE))
    print(colorize("Press Ctrl+C to exit logs", Colors.YELLOW))
    try:
        run_docker_command("logs -f football-betting-advisor")
    except KeyboardInterrupt:
        pass
    
    input(colorize("\nPress Enter to continue...", Colors.YELLOW))

# Run in shadow mode
def run_shadow_mode():
    """Run the AI Football Betting Advisor in shadow mode."""
    clear_screen()
    print_header()
    
    print(colorize("Running in shadow mode (no real bets)...", Colors.BLUE))
    
    # Get user input for shadow mode parameters
    try:
        days = int(input(colorize("Number of days to simulate [14]: ", Colors.YELLOW)) or "14")
        bankroll = float(input(colorize("Virtual bankroll to simulate with [1000.0]: ", Colors.YELLOW)) or "1000.0")
    except ValueError as e:
        print(colorize(f"Invalid input: {e}. Using default values.", Colors.RED))
        days = 14
        bankroll = 1000.0
    
    print(colorize(f"\nStarting shadow mode with parameters:", Colors.BLUE))
    print(colorize(f"- Days: {days}", Colors.BLUE))
    print(colorize(f"- Bankroll: {bankroll}", Colors.BLUE))
    
    run_docker_command(f"exec football-betting-advisor python shadow_mode.py --days {days} --bankroll {bankroll}")
    
    print(colorize("\nShadow mode started. Check Telegram for updates or view logs to monitor progress.", Colors.GREEN))
    
    input(colorize("\nPress Enter to continue...", Colors.YELLOW))

# Generate performance report
def generate_report():
    """Generate a performance report."""
    clear_screen()
    print_header()
    
    print(colorize("Generating performance report...", Colors.BLUE))
    run_docker_command("exec football-betting-advisor python main.py --report")
    
    input(colorize("\nPress Enter to continue...", Colors.YELLOW))

# Retrain ML model
def retrain_model():
    """Retrain the ML prediction model."""
    clear_screen()
    print_header()
    
    print(colorize("Retraining the prediction model...", Colors.BLUE))
    print(colorize("This may take several minutes depending on the amount of historical data.", Colors.YELLOW))
    run_docker_command("exec football-betting-advisor python main.py --retrain")
    
    input(colorize("\nPress Enter to continue...", Colors.YELLOW))

# Update the system
def update_system():
    """Update the AI Football Betting Advisor."""
    clear_screen()
    print_header()
    
    print(colorize("Updating AI Football Betting Advisor...", Colors.BLUE))
    
    # Ask for confirmation
    confirm = input(colorize("This will pull the latest changes and rebuild the system. Continue? (y/n): ", Colors.YELLOW))
    if confirm.lower() != 'y':
        print(colorize("Update cancelled.", Colors.YELLOW))
        input(colorize("\nPress Enter to continue...", Colors.YELLOW))
        return
    
    # Stop containers
    print(colorize("Stopping containers...", Colors.YELLOW))
    run_docker_compose_command("down")
    
    # Pull latest changes
    print(colorize("Pulling latest changes...", Colors.BLUE))
    subprocess.run("git pull", shell=True)
    
    # Rebuild and start
    print(colorize("Rebuilding containers...", Colors.BLUE))
    run_docker_compose_command("build")
    
    print(colorize("Starting updated system...", Colors.GREEN))
    run_docker_compose_command("up -d")
    
    print(colorize("Update complete!", Colors.GREEN))
    
    time.sleep(2)
    check_status()

# Configure environment variables
def configure_system():
    """Configure the system environment variables."""
    clear_screen()
    print_header()
    
    print(colorize("Configuring AI Football Betting Advisor...", Colors.BLUE))
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        print(colorize("No .env file found. Creating one from .env.example...", Colors.YELLOW))
        if os.path.exists(".env.example"):
            with open(".env.example", "r") as example_file:
                example_content = example_file.read()
            
            with open(".env", "w") as env_file:
                env_file.write(example_content)
        else:
            print(colorize("No .env.example file found. Creating a basic .env file...", Colors.RED))
            with open(".env", "w") as env_file:
                env_file.write("""# AI Football Betting Advisor Configuration

# Bankroll settings
BANKROLL=1000.0
MAX_STAKE_PERCENT=5.0
MIN_STAKE_PERCENT=0.5

# Betting parameters
DAYS_AHEAD=1
MIN_ODDS=1.5
MAX_ODDS=10.0
MIN_EV_THRESHOLD=0.05

# Telegram Bot settings
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Redis settings (optional)
REDIS_HOST=redis
REDIS_PORT=6379

# Operation mode
DRY_RUN=true
""")
    
    # Open editor for .env file
    print(colorize("Opening .env file for editing...", Colors.BLUE))
    if platform.system() == "Windows":
        os.system("notepad .env")
    else:
        editor = os.environ.get("EDITOR", "nano")
        os.system(f"{editor} .env")
    
    # Ask if user wants to restart the system with new configuration
    restart = input(colorize("Restart the system with the new configuration? (y/n): ", Colors.YELLOW))
    if restart.lower() == 'y':
        restart_system()
    else:
        input(colorize("\nPress Enter to continue...", Colors.YELLOW))

# Schedule automatic execution
def schedule_execution():
    """Set up scheduled execution of the betting advisor."""
    clear_screen()
    print_header()
    
    print(colorize("Setting up scheduled execution...", Colors.BLUE))
    print(colorize("This will configure the system to run automatically at a specific time each day.", Colors.YELLOW))
    
    # Show current schedule
    if platform.system() == "Windows":
        print(colorize("\nCurrent scheduled tasks (Windows):", Colors.BLUE))
        subprocess.run("schtasks /query /tn \"AI Football Betting Advisor*\"", shell=True)
    else:
        print(colorize("\nCurrent cron jobs:", Colors.BLUE))
        subprocess.run("crontab -l | grep -E 'betting|football'", shell=True)
    
    # Ask for time to run
    try:
        hour = int(input(colorize("\nHour to run daily (0-23) [10]: ", Colors.YELLOW)) or "10")
        minute = int(input(colorize("Minute to run daily (0-59) [0]: ", Colors.YELLOW)) or "0")
        
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("Invalid time")
    except ValueError:
        print(colorize("Invalid time. Using default (10:00).", Colors.RED))
        hour = 10
        minute = 0
    
    # Schedule the job
    if platform.system() == "Windows":
        # Create a batch file for the task
        with open("run_advisor.bat", "w") as batch_file:
            batch_file.write("@echo off\n")
            batch_file.write("cd %~dp0\n")
            batch_file.write("run.bat start\n")
        
        # Create the scheduled task
        task_command = f'schtasks /create /tn "AI Football Betting Advisor Daily Run" /tr "{os.path.abspath("run_advisor.bat")}" /sc DAILY /st {hour:02d}:{minute:02d} /f'
        subprocess.run(task_command, shell=True)
        print(colorize(f"\nScheduled task created to run daily at {hour:02d}:{minute:02d}", Colors.GREEN))
    else:
        # Create cron job
        cron_cmd = f"{minute} {hour} * * * cd {os.getcwd()} && ./run.sh start > /dev/null 2>&1"
        
        # Write to temporary file
        with open("temp_cron", "w") as temp_file:
            subprocess.run("crontab -l", shell=True, stdout=temp_file)
            temp_file.write(f"\n# AI Football Betting Advisor Daily Run\n")
            temp_file.write(f"{cron_cmd}\n")
        
        # Install new crontab
        subprocess.run("crontab temp_cron", shell=True)
        os.remove("temp_cron")
        print(colorize(f"\nCron job created to run daily at {hour:02d}:{minute:02d}", Colors.GREEN))
    
    input(colorize("\nPress Enter to continue...", Colors.YELLOW))

# Print application header
def print_header():
    """Print the application header."""
    width = get_terminal_width()
    
    # Calculate padding for centered text
    def center_text(text, fill_char=" "):
        text_len = len(text.replace("\033[94m", "").replace("\033[92m", "").replace("\033[0m", ""))
        padding = (width - text_len) // 2
        return fill_char * padding + text + fill_char * (width - text_len - padding)
    
    # Banner
    print(colorize(center_text("", "="), Colors.BLUE))
    print(colorize("  █████╗ ██╗    ███████╗ ██████╗  ██████╗ ████████╗██████╗  █████╗ ██╗     ██╗     ", Colors.BLUE))
    print(colorize(" ██╔══██╗██║    ██╔════╝██╔═══██╗██╔═══██╗╚══██╔══╝██╔══██╗██╔══██╗██║     ██║     ", Colors.BLUE))
    print(colorize(" ███████║██║    █████╗  ██║   ██║██║   ██║   ██║   ██████╔╝███████║██║     ██║     ", Colors.BLUE))
    print(colorize(" ██╔══██║██║    ██╔══╝  ██║   ██║██║   ██║   ██║   ██╔══██╗██╔══██║██║     ██║     ", Colors.BLUE))
    print(colorize(" ██║  ██║██║    ██║     ╚██████╔╝╚██████╔╝   ██║   ██████╔╝██║  ██║███████╗███████╗", Colors.BLUE))
    print(colorize(" ╚═╝  ╚═╝╚═╝    ╚═╝      ╚═════╝  ╚═════╝    ╚═╝   ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝", Colors.BLUE))
    print(colorize(center_text("BETTING ADVISOR", " "), Colors.GREEN))
    print(colorize(center_text("Value-Based Football Betting Recommendations", " "), Colors.YELLOW))
    print(colorize(center_text("", "="), Colors.BLUE))
    print()

# Display main menu
def show_menu():
    """Display the main menu and handle user input."""
    while True:
        clear_screen()
        print_header()
        
        # Menu options
        print(colorize("  MAIN MENU", Colors.BOLD))
        print()
        print(colorize("  1)", Colors.GREEN) + " Start System")
        print(colorize("  2)", Colors.RED) + " Stop System")
        print(colorize("  3)", Colors.YELLOW) + " Restart System")
        print(colorize("  4)", Colors.BLUE) + " Check System Status")
        print(colorize("  5)", Colors.BLUE) + " View Logs")
        print()
        print(colorize("  6)", Colors.GREEN) + " Run in Shadow Mode (Test without real money)")
        print(colorize("  7)", Colors.GREEN) + " Generate Performance Report")
        print(colorize("  8)", Colors.GREEN) + " Retrain ML Model")
        print()
        print(colorize("  9)", Colors.YELLOW) + " Configure System")
        print(colorize(" 10)", Colors.YELLOW) + " Schedule Automatic Execution")
        print(colorize(" 11)", Colors.YELLOW) + " Update System")
        print()
        print(colorize("  0)", Colors.RED) + " Exit")
        print()
        
        # Get user choice
        try:
            choice = input(colorize("Enter your choice [0-11]: ", Colors.BLUE))
            choice = int(choice) if choice else 0
        except ValueError:
            choice = -1
        
        # Process user choice
        if choice == 0:
            clear_screen()
            print(colorize("Thank you for using AI Football Betting Advisor!", Colors.GREEN))
            print(colorize("Goodbye!", Colors.BLUE))
            sys.exit(0)
        elif choice == 1:
            start_system()
        elif choice == 2:
            stop_system()
        elif choice == 3:
            restart_system()
        elif choice == 4:
            check_status()
        elif choice == 5:
            view_logs()
        elif choice == 6:
            run_shadow_mode()
        elif choice == 7:
            generate_report()
        elif choice == 8:
            retrain_model()
        elif choice == 9:
            configure_system()
        elif choice == 10:
            schedule_execution()
        elif choice == 11:
            update_system()
        else:
            print(colorize("Invalid choice. Please try again.", Colors.RED))
            time.sleep(1)

def main():
    """Main entry point for the CLI menu."""
    parser = argparse.ArgumentParser(description='AI Football Betting Advisor CLI Menu')
    parser.add_argument('command', nargs='?', help='Command to run (start, stop, status, etc.)')
    args = parser.parse_args()
    
    if args.command:
        if args.command == 'start':
            start_system()
        elif args.command == 'stop':
            stop_system()
        elif args.command == 'restart':
            restart_system()
        elif args.command == 'status':
            check_status()
        elif args.command == 'logs':
            view_logs()
        elif args.command == 'shadow':
            run_shadow_mode()
        elif args.command == 'report':
            generate_report()
        elif args.command == 'retrain':
            retrain_model()
        elif args.command == 'update':
            update_system()
        elif args.command == 'configure':
            configure_system()
        else:
            print(colorize(f"Unknown command: {args.command}", Colors.RED))
            sys.exit(1)
    else:
        show_menu()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print(colorize("Program interrupted by user. Exiting...", Colors.YELLOW))
        sys.exit(0) 