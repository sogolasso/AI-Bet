#!/usr/bin/env python3
"""
Cleanup Script for AI Football Betting Advisor

This script helps manage disk space by cleaning up old log files, reports,
and other data that accumulates over time. It can be scheduled to run
periodically to prevent running out of disk space.
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_project_root():
    """Get the project root directory."""
    current_file = Path(__file__).resolve()
    return current_file.parent.parent

def cleanup_logs(days_old=30, dry_run=False):
    """Clean up log files older than specified days.
    
    Args:
        days_old (int): Remove files older than this many days
        dry_run (bool): If True, only print what would be deleted without deleting
    
    Returns:
        int: Number of files deleted
    """
    logger.info(f"Cleaning up log files older than {days_old} days")
    
    # Locations to check for log files
    log_locations = [
        "logs",
        "data/logs",
    ]
    
    # Extensions to consider as log files
    log_extensions = [".log", ".log.1", ".log.2"]
    
    files_deleted = 0
    bytes_freed = 0
    cutoff_time = time.time() - (days_old * 86400)  # Convert days to seconds
    
    for log_location in log_locations:
        log_dir = get_project_root() / log_location
        if not log_dir.exists():
            logger.debug(f"Directory {log_dir} does not exist, skipping")
            continue
            
        logger.info(f"Checking {log_dir} for old log files")
        
        # Search for log files
        for log_file in log_dir.glob("**/*"):
            if not log_file.is_file():
                continue
                
            # Check if it's a log file
            if log_file.suffix not in log_extensions and not any(str(log_file).endswith(ext) for ext in log_extensions):
                continue
                
            # Check file age
            file_time = log_file.stat().st_mtime
            if file_time < cutoff_time:
                file_size = log_file.stat().st_size
                logger.info(f"Found old log file: {log_file} ({file_size / 1024:.1f} KB)")
                
                if not dry_run:
                    try:
                        log_file.unlink()
                        logger.info(f"Deleted: {log_file}")
                        files_deleted += 1
                        bytes_freed += file_size
                    except Exception as e:
                        logger.error(f"Failed to delete {log_file}: {e}")
                else:
                    logger.info(f"Would delete: {log_file} (dry run)")
                    files_deleted += 1
                    bytes_freed += file_size
    
    mb_freed = bytes_freed / (1024 * 1024)
    logger.info(f"Log cleanup complete. {'Would delete' if dry_run else 'Deleted'} {files_deleted} files ({mb_freed:.2f} MB)")
    return files_deleted

def cleanup_reports(days_old=90, dry_run=False):
    """Clean up old report files.
    
    Args:
        days_old (int): Remove files older than this many days
        dry_run (bool): If True, only print what would be deleted without deleting
    
    Returns:
        int: Number of files deleted
    """
    logger.info(f"Cleaning up report files older than {days_old} days")
    
    # Locations to check for report files
    report_locations = [
        "data/reports",
        "data/shadow/reports",
    ]
    
    files_deleted = 0
    bytes_freed = 0
    cutoff_time = time.time() - (days_old * 86400)  # Convert days to seconds
    
    for report_location in report_locations:
        report_dir = get_project_root() / report_location
        if not report_dir.exists():
            logger.debug(f"Directory {report_dir} does not exist, skipping")
            continue
            
        logger.info(f"Checking {report_dir} for old report files")
        
        # Search for report files (json and csv)
        for report_file in report_dir.glob("**/*"):
            if not report_file.is_file():
                continue
                
            # Check if it's a report file
            if report_file.suffix not in [".json", ".csv"]:
                continue
                
            # Check file age
            file_time = report_file.stat().st_mtime
            if file_time < cutoff_time:
                file_size = report_file.stat().st_size
                logger.info(f"Found old report file: {report_file} ({file_size / 1024:.1f} KB)")
                
                if not dry_run:
                    try:
                        report_file.unlink()
                        logger.info(f"Deleted: {report_file}")
                        files_deleted += 1
                        bytes_freed += file_size
                    except Exception as e:
                        logger.error(f"Failed to delete {report_file}: {e}")
                else:
                    logger.info(f"Would delete: {report_file} (dry run)")
                    files_deleted += 1
                    bytes_freed += file_size
    
    mb_freed = bytes_freed / (1024 * 1024)
    logger.info(f"Report cleanup complete. {'Would delete' if dry_run else 'Deleted'} {files_deleted} files ({mb_freed:.2f} MB)")
    return files_deleted

def cleanup_cached_data(days_old=7, dry_run=False):
    """Clean up old cached data.
    
    Args:
        days_old (int): Remove files older than this many days
        dry_run (bool): If True, only print what would be deleted without deleting
    
    Returns:
        int: Number of files deleted
    """
    logger.info(f"Cleaning up cached data older than {days_old} days")
    
    # Locations to check for cached data
    cache_locations = [
        "data/cache",
    ]
    
    files_deleted = 0
    bytes_freed = 0
    cutoff_time = time.time() - (days_old * 86400)  # Convert days to seconds
    
    for cache_location in cache_locations:
        cache_dir = get_project_root() / cache_location
        if not cache_dir.exists():
            logger.debug(f"Directory {cache_dir} does not exist, skipping")
            continue
            
        logger.info(f"Checking {cache_dir} for old cached data")
        
        # Search for all files in cache directories
        for cache_file in cache_dir.glob("**/*"):
            if not cache_file.is_file():
                continue
                
            # Check file age
            file_time = cache_file.stat().st_mtime
            if file_time < cutoff_time:
                file_size = cache_file.stat().st_size
                logger.info(f"Found old cached file: {cache_file} ({file_size / 1024:.1f} KB)")
                
                if not dry_run:
                    try:
                        cache_file.unlink()
                        logger.info(f"Deleted: {cache_file}")
                        files_deleted += 1
                        bytes_freed += file_size
                    except Exception as e:
                        logger.error(f"Failed to delete {cache_file}: {e}")
                else:
                    logger.info(f"Would delete: {cache_file} (dry run)")
                    files_deleted += 1
                    bytes_freed += file_size
    
    mb_freed = bytes_freed / (1024 * 1024)
    logger.info(f"Cache cleanup complete. {'Would delete' if dry_run else 'Deleted'} {files_deleted} files ({mb_freed:.2f} MB)")
    return files_deleted

def ensure_directory_exists(directory):
    """Ensure the specified directory exists, creating it if necessary."""
    directory = get_project_root() / directory
    if not directory.exists():
        logger.info(f"Creating directory {directory}")
        directory.mkdir(parents=True, exist_ok=True)
    return directory

def main():
    """Main entry point for cleanup script."""
    parser = argparse.ArgumentParser(description='AI Football Betting Advisor Cleanup Utility')
    parser.add_argument('--logs', type=int, default=30, help='Remove log files older than this many days')
    parser.add_argument('--reports', type=int, default=90, help='Remove report files older than this many days')
    parser.add_argument('--cache', type=int, default=7, help='Remove cached data older than this many days')
    parser.add_argument('--dry-run', action='store_true', help='Only show what would be deleted without actually deleting')
    parser.add_argument('--create-dirs', action='store_true', help='Create standard directories if they do not exist')
    
    args = parser.parse_args()
    
    # Optionally create standard directories
    if args.create_dirs:
        ensure_directory_exists("data")
        ensure_directory_exists("data/logs")
        ensure_directory_exists("data/reports")
        ensure_directory_exists("data/cache")
        ensure_directory_exists("data/shadow")
        ensure_directory_exists("data/shadow/reports")
    
    # Perform cleanup operations
    total_deleted = 0
    
    if args.logs >= 0:
        total_deleted += cleanup_logs(days_old=args.logs, dry_run=args.dry_run)
    
    if args.reports >= 0:
        total_deleted += cleanup_reports(days_old=args.reports, dry_run=args.dry_run)
    
    if args.cache >= 0:
        total_deleted += cleanup_cached_data(days_old=args.cache, dry_run=args.dry_run)
    
    action = "Would delete" if args.dry_run else "Deleted"
    logger.info(f"Cleanup complete. {action} {total_deleted} files in total.")

if __name__ == "__main__":
    main() 