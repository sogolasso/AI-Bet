#!/usr/bin/env python3
"""
Setup Scheduler Script for AI Football Betting Advisor

This script configures automatic daily execution of the AI Football Betting Advisor
using cron jobs (Linux/macOS) or Task Scheduler (Windows).
"""

import os
import sys
import platform
import subprocess
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def get_project_root():
    """Get the project root directory."""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent

def setup_linux_cron(hour, minute):
    """Set up a cron job for Linux or macOS.
    
    Args:
        hour: Hour to run the job (0-23)
        minute: Minute to run the job (0-59)
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Setting up cron job to run daily at {hour:02d}:{minute:02d}")
    
    project_root = get_project_root()
    run_script = project_root / "run.sh"
    
    if not run_script.exists():
        logger.error(f"Run script not found at {run_script}")
        return False
    
    # Make sure run.sh is executable
    try:
        os.chmod(run_script, 0o755)
        logger.info(f"Made {run_script} executable")
    except Exception as e:
        logger.error(f"Failed to make run script executable: {e}")
        return False
    
    # Create cron command
    cron_cmd = f"{minute} {hour} * * * cd {project_root} && ./run.sh start > {project_root}/logs/cron_run.log 2>&1"
    
    # Create temporary file for crontab
    temp_cron_path = project_root / "temp_cron"
    
    try:
        # Get current crontab
        result = subprocess.run(
            "crontab -l", 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Write to temporary file
        with open(temp_cron_path, "w") as f:
            if result.returncode == 0:
                f.write(result.stdout)
            
            # Check if we already have a job for this
            if "AI Football Betting Advisor" in result.stdout:
                logger.info("Updating existing cron job")
                lines = result.stdout.splitlines()
                new_lines = []
                for line in lines:
                    if "AI Football Betting Advisor" not in line and "run.sh start" not in line:
                        new_lines.append(line)
                f.write("\n".join(new_lines))
                f.write("\n")
            
            # Add our new job
            f.write(f"\n# AI Football Betting Advisor Daily Run - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"{cron_cmd}\n")
        
        # Install new crontab
        subprocess.run(f"crontab {temp_cron_path}", shell=True, check=True)
        
        # Remove temporary file
        os.remove(temp_cron_path)
        
        logger.info(f"Cron job successfully set up to run daily at {hour:02d}:{minute:02d}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to set up cron job: {e}")
        return False

def setup_windows_task(hour, minute):
    """Set up a scheduled task for Windows.
    
    Args:
        hour: Hour to run the job (0-23)
        minute: Minute to run the job (0-59)
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Setting up Windows Task Scheduler job to run daily at {hour:02d}:{minute:02d}")
    
    project_root = get_project_root()
    run_script = project_root / "run.bat"
    
    if not run_script.exists():
        logger.error(f"Run script not found at {run_script}")
        return False
    
    # Create batch file that will be run by the task
    task_batch_path = project_root / "run_scheduled_task.bat"
    
    try:
        with open(task_batch_path, "w") as f:
            f.write("@echo off\n")
            f.write(f"cd /d {project_root}\n")
            f.write("run.bat start\n")
        
        logger.info(f"Created task batch file at {task_batch_path}")
        
        # Delete existing task if it exists
        subprocess.run(
            'schtasks /delete /tn "AI Football Betting Advisor Daily Run" /f',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Create the task
        task_cmd = (
            f'schtasks /create /tn "AI Football Betting Advisor Daily Run" '
            f'/tr "{task_batch_path}" /sc DAILY /st {hour:02d}:{minute:02d} '
            f'/ru SYSTEM /rl HIGHEST /f'
        )
        
        result = subprocess.run(
            task_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to create scheduled task: {result.stderr}")
            
            # Try again without SYSTEM privileges
            logger.info("Trying again with current user privileges")
            task_cmd = (
                f'schtasks /create /tn "AI Football Betting Advisor Daily Run" '
                f'/tr "{task_batch_path}" /sc DAILY /st {hour:02d}:{minute:02d} /f'
            )
            
            result = subprocess.run(
                task_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to create scheduled task with current user privileges: {result.stderr}")
                return False
        
        logger.info(f"Windows scheduled task successfully set up to run daily at {hour:02d}:{minute:02d}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to set up Windows scheduled task: {e}")
        return False

def show_current_schedule():
    """Show current scheduled jobs."""
    logger.info("Checking current schedule...")
    
    if platform.system() == "Windows":
        logger.info("Current Windows scheduled tasks:")
        subprocess.run(
            'schtasks /query /fo LIST /tn "AI Football Betting Advisor Daily Run"',
            shell=True
        )
    else:
        logger.info("Current cron jobs:")
        subprocess.run(
            "crontab -l | grep -E 'AI Football Betting Advisor|run.sh'",
            shell=True
        )

def remove_scheduled_job():
    """Remove existing scheduled jobs."""
    logger.info("Removing scheduled jobs...")
    
    if platform.system() == "Windows":
        logger.info("Removing Windows scheduled task")
        subprocess.run(
            'schtasks /delete /tn "AI Football Betting Advisor Daily Run" /f',
            shell=True
        )
    else:
        logger.info("Removing cron job")
        
        project_root = get_project_root()
        temp_cron_path = project_root / "temp_cron"
        
        try:
            # Get current crontab
            result = subprocess.run(
                "crontab -l", 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                logger.warning("No existing crontab found")
                return
            
            # Filter out our jobs
            lines = result.stdout.splitlines()
            filtered_lines = [
                line for line in lines 
                if "AI Football Betting Advisor" not in line and "run.sh start" not in line
            ]
            
            # Write to temporary file
            with open(temp_cron_path, "w") as f:
                f.write("\n".join(filtered_lines))
                if filtered_lines and not filtered_lines[-1].endswith("\n"):
                    f.write("\n")
            
            # Install new crontab
            subprocess.run(f"crontab {temp_cron_path}", shell=True, check=True)
            
            # Remove temporary file
            os.remove(temp_cron_path)
            
            logger.info("Cron job successfully removed")
        
        except Exception as e:
            logger.error(f"Failed to remove cron job: {e}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Setup scheduler for AI Football Betting Advisor")
    parser.add_argument("--hour", type=int, default=10, help="Hour to run daily (0-23)")
    parser.add_argument("--minute", type=int, default=0, help="Minute to run daily (0-59)")
    parser.add_argument("--show", action="store_true", help="Show current scheduled jobs")
    parser.add_argument("--remove", action="store_true", help="Remove scheduled jobs")
    
    args = parser.parse_args()
    
    # Validate time
    if args.hour < 0 or args.hour > 23:
        logger.error(f"Invalid hour: {args.hour}. Must be between 0 and 23.")
        return 1
    
    if args.minute < 0 or args.minute > 59:
        logger.error(f"Invalid minute: {args.minute}. Must be between 0 and 59.")
        return 1
    
    # Show current schedule if requested
    if args.show:
        show_current_schedule()
        return 0
    
    # Remove scheduled job if requested
    if args.remove:
        remove_scheduled_job()
        return 0
    
    # Set up scheduler based on platform
    if platform.system() == "Windows":
        success = setup_windows_task(args.hour, args.minute)
    else:
        success = setup_linux_cron(args.hour, args.minute)
    
    if success:
        logger.info("Scheduler setup completed successfully")
        return 0
    else:
        logger.error("Scheduler setup failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 