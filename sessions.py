import os
import asyncio
import json
from telethon import TelegramClient
from telethon.errors import UpdateAppToLoginError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SESSIONS_DIR = "sessions"  # Directory to store session files
SESSIONS_INFO_FILE = "sessions/sessions_info.json"  # File to store sessions metadata

async def create_session(session_name, api_id, api_hash):
    """
    Create and authenticate a new Telegram session
    
    Args:
        session_name: Name for the session file
        api_id: Telegram API ID
        api_hash: Telegram API Hash
        
    Returns:
        bool: Whether session was successfully created and authenticated
    """
    session_path = os.path.join(SESSIONS_DIR, session_name)
    
    try:
        # Create client
        client = TelegramClient(session_path, api_id, api_hash, system_version="4.16.30-vxCUSTOM")
        
        try:
            await client.start()
        except UpdateAppToLoginError:
            print(f"\nError: Telethon version is outdated for {session_name}")
            await client.disconnect()
            return False
            
        # Check if already authorized
        if await client.is_user_authorized():
            print(f"Session {session_name} is already authorized.")
            await client.disconnect()
            return True
            
        # If not authorized, request phone and code
        try:
            phone = input(f"\nEnter phone number for session {session_name}: ")
            await client.send_code_request(phone)
            code = input("Enter the verification code: ")
            await client.sign_in(phone, code)
            
            print(f"Session {session_name} created and authorized successfully!")
            
            # Get some basic info about the account
            me = await client.get_me()
            username = me.username if me.username else "No username"
            first_name = me.first_name if me.first_name else "No first name"
            
            # Return account info
            await client.disconnect()
            return {
                "session_name": session_name,
                "phone": phone,
                "username": username,
                "first_name": first_name,
                "status": "available"
            }
            
        except Exception as e:
            print(f"Error authenticating session {session_name}: {str(e)}")
            await client.disconnect()
            return False
            
    except Exception as e:
        print(f"Error creating session {session_name}: {str(e)}")
        return False

async def create_multiple_sessions(num_sessions):
    """
    Create multiple Telegram sessions
    
    Args:
        num_sessions: Number of sessions to create
    """
    # Ensure sessions directory exists
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    
    # Load existing sessions info if available
    sessions_info = []
    if os.path.exists(SESSIONS_INFO_FILE):
        try:
            with open(SESSIONS_INFO_FILE, 'r') as f:
                sessions_info = json.load(f)
            print(f"Loaded {len(sessions_info)} existing sessions.")
        except Exception as e:
            print(f"Error loading existing sessions: {str(e)}")
            sessions_info = []
    
    # Load API credentials from environment variables
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not api_id or not api_hash:
        print("Error: API credentials not found in .env file")
        print("Please create a .env file with TELEGRAM_API_ID and TELEGRAM_API_HASH")
        return
    
    # Convert string to int (API_ID should be an integer)
    api_id = int(api_id)
    
    # Calculate how many new sessions to create
    existing_count = len(sessions_info)
    sessions_to_create = max(0, num_sessions - existing_count)
    
    print(f"\nCreating {sessions_to_create} new sessions (already have {existing_count})...")
    
    # Create new sessions
    for i in range(sessions_to_create):
        session_name = f"session_{existing_count + i + 1}"
        print(f"\nCreating session {i+1}/{sessions_to_create}: {session_name}")
        
        session_info = await create_session(session_name, api_id, api_hash)
        
        if session_info:
            sessions_info.append(session_info)
    
    # Save updated sessions info
    with open(SESSIONS_INFO_FILE, 'w') as f:
        json.dump(sessions_info, f, indent=4)
    
    print(f"\nTotal sessions available: {len(sessions_info)}")
    print(f"Sessions info saved to {SESSIONS_INFO_FILE}")

async def test_sessions():
    """Test all available sessions to ensure they are still valid"""
    if not os.path.exists(SESSIONS_INFO_FILE):
        print("No sessions found. Please create sessions first.")
        return
    
    # Load API credentials from environment variables
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not api_id or not api_hash:
        print("Error: API credentials not found in .env file")
        return
    
    # Convert string to int (API_ID should be an integer)
    api_id = int(api_id)
    
    # Load sessions info
    with open(SESSIONS_INFO_FILE, 'r') as f:
        sessions_info = json.load(f)
    
    print(f"Testing {len(sessions_info)} sessions...")
    
    for i, session_info in enumerate(sessions_info):
        session_name = session_info['session_name']
        session_path = os.path.join(SESSIONS_DIR, session_name)
        
        print(f"\nTesting session {i+1}/{len(sessions_info)}: {session_name}")
        
        try:
            client = TelegramClient(session_path, api_id, api_hash, system_version="4.16.30-vxCUSTOM")
            await client.start()
            
            if await client.is_user_authorized():
                print(f"Session {session_name} is active and authorized.")
                me = await client.get_me()
                print(f"Account: {me.first_name} (@{me.username if me.username else 'No username'})")
                session_info['status'] = "available"
            else:
                print(f"Session {session_name} is not authorized.")
                session_info['status'] = "unauthorized"
            
            await client.disconnect()
            
        except Exception as e:
            print(f"Error testing session {session_name}: {str(e)}")
            session_info['status'] = "error"
    
    # Save updated sessions info
    with open(SESSIONS_INFO_FILE, 'w') as f:
        json.dump(sessions_info, f, indent=4)
    
    print(f"\nSession testing completed. Updated status saved to {SESSIONS_INFO_FILE}")

async def main():
    """Main function with command line interface"""
    print("Telegram Sessions Manager")
    print("========================")
    print("1. Create multiple sessions")
    print("2. Test existing sessions")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ")
    
    if choice == "1":
        try:
            num_sessions = int(input("How many total sessions do you want to have? "))
            if num_sessions <= 0:
                print("Number of sessions must be greater than 0")
                return
            await create_multiple_sessions(num_sessions)
        except ValueError:
            print("Please enter a valid number")
            
    elif choice == "2":
        await test_sessions()
        
    elif choice == "3":
        print("Exiting...")
        
    else:
        print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())