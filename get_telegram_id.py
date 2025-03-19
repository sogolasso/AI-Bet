#!/usr/bin/env python3
"""
Telegram User ID Finder

This script helps users find their Telegram user ID by providing instructions
on how to get it directly from Telegram.
"""

def print_header():
    """Print the header for the script."""
    print("\n" + "=" * 70)
    print("🔍 AI Football Betting Advisor - Telegram User ID Finder")
    print("=" * 70)

def print_instructions():
    """Print instructions for finding Telegram user ID."""
    print("\nTo find your Telegram user ID, follow these steps:")
    print("\n1️⃣ Open Telegram and search for '@userinfobot'")
    print("2️⃣ Start a chat with this bot by clicking on it")
    print("3️⃣ Send any message to the bot (e.g., '/start' or 'hi')")
    print("4️⃣ The bot will reply with your user information, including your ID")
    print("5️⃣ Copy your ID and add it to your .env file as TELEGRAM_ADMIN_IDS")
    
    print("\nExample .env file entry:")
    print("TELEGRAM_ADMIN_IDS=123456789")
    
    print("\nFor multiple admin IDs, separate them with commas:")
    print("TELEGRAM_ADMIN_IDS=123456789,987654321")

def update_env_file():
    """Help the user update their .env file with their Telegram user ID."""
    import os
    from pathlib import Path
    
    print("\n" + "-" * 70)
    print("📝 Update your .env file")
    print("-" * 70)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("\n❌ No .env file found in the current directory.")
        create_new = input("Would you like to create a new .env file? (y/n): ").strip().lower()
        if create_new != 'y':
            print("Operation cancelled. Please create an .env file manually.")
            return
        
        # Create new .env file
        with open('.env', 'w') as f:
            f.write("# AI Football Betting Advisor Environment Variables\n\n")
            f.write("# Telegram Bot Token (required for Telegram integration)\n")
            f.write("TELEGRAM_BOT_TOKEN=\n\n")
            f.write("# Telegram Admin User IDs (comma-separated, required for receiving messages)\n")
            f.write("TELEGRAM_ADMIN_IDS=\n")
        
        print("\n✅ Created new .env file.")
    
    # Ask for Telegram user ID
    print("\nPlease enter your Telegram user ID:")
    user_id = input("> ").strip()
    
    if not user_id:
        print("❌ No user ID provided. Operation cancelled.")
        return
    
    if not user_id.isdigit():
        print("⚠️ Warning: Telegram user IDs are usually numeric. Please verify your ID.")
        confirm = input("Do you still want to proceed? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled.")
            return
    
    # Read current .env file
    with open('.env', 'r') as f:
        lines = f.readlines()
    
    # Update or add TELEGRAM_ADMIN_IDS line
    admin_id_line_found = False
    for i, line in enumerate(lines):
        if line.strip().startswith('TELEGRAM_ADMIN_IDS='):
            admin_id_line_found = True
            current_value = line.strip().split('=', 1)[1].strip()
            
            if current_value:
                # Add to existing IDs if not already present
                current_ids = [id.strip() for id in current_value.strip('[]').split(',')]
                if user_id not in current_ids:
                    current_ids.append(user_id)
                    lines[i] = f"TELEGRAM_ADMIN_IDS={','.join(current_ids)}\n"
                    print(f"\n✅ Added {user_id} to existing admin IDs.")
                else:
                    print(f"\n✅ User ID {user_id} is already in your admin IDs.")
            else:
                # Set as the only ID
                lines[i] = f"TELEGRAM_ADMIN_IDS={user_id}\n"
                print(f"\n✅ Set {user_id} as the admin ID.")
            break
    
    # If TELEGRAM_ADMIN_IDS line not found, add it
    if not admin_id_line_found:
        lines.append(f"\n# Telegram Admin User IDs (comma-separated, required for receiving messages)\n")
        lines.append(f"TELEGRAM_ADMIN_IDS={user_id}\n")
        print(f"\n✅ Added {user_id} as the admin ID.")
    
    # Write updated content back to .env file
    with open('.env', 'w') as f:
        f.writelines(lines)
    
    print("\n✅ .env file has been updated successfully.")
    print("\n⚠️ Remember to restart any running bots or shadow mode instances")
    print("   for the changes to take effect.")

def main():
    """Main function."""
    print_header()
    print_instructions()
    
    # Ask if user wants to update .env file
    print("\n" + "-" * 70)
    update = input("Would you like to update your .env file with your Telegram user ID? (y/n): ").strip().lower()
    
    if update == 'y':
        update_env_file()
    
    print("\n" + "=" * 70)
    print("🏁 Telegram User ID Finder completed")
    print("=" * 70)

if __name__ == "__main__":
    main() 