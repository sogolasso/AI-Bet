#!/usr/bin/env python3
"""
Shadow Mode Launcher for AI Football Betting Advisor

This script is a simple launcher for the shadow mode of the AI Football Betting Advisor.
It's a convenience wrapper around the all_in_one.py script.
"""

import sys
import os
import subprocess
import platform

def main():
    """Launch all_in_one.py in shadow mode."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    all_in_one_path = os.path.join(script_dir, "all_in_one.py")
    
    # Make sure all_in_one.py exists
    if not os.path.exists(all_in_one_path):
        print("Error: all_in_one.py not found. Make sure it exists in the same directory.")
        return 1
    
    # Make script executable on Unix systems
    if platform.system() != "Windows":
        try:
            os.chmod(all_in_one_path, 0o755)
        except:
            pass
    
    # Pass through any command-line arguments
    args = ["--shadow"] + sys.argv[1:]
    
    # Execute all_in_one.py with the shadow argument
    try:
        if platform.system() == "Windows":
            return subprocess.call([sys.executable, all_in_one_path] + args)
        else:
            return subprocess.call([all_in_one_path] + args)
    except Exception as e:
        print(f"Error launching shadow mode: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 