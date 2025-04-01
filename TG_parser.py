from telethon import TelegramClient, functions, types
from telethon.errors import ChannelPrivateError, FloodWaitError, UsernameNotOccupiedError, UpdateAppToLoginError
import csv
import os
import re
import asyncio
import json
import random
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API credentials from environment variables
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')

# File paths
INPUT_FILE = 'Results/Results.txt'
OUTPUT_FILE = 'Results/Table.csv'
PROGRESS_FILE = 'Results/progress.json'
SESSIONS_DIR = 'sessions'
SESSIONS_INFO_FILE = 'sessions/sessions_info.json'

# Constants
MAX_FLOOD_WAIT_TIME = 300  # 5 minutes in seconds

def extract_username(about):
    """
    Extract username from channel description/about text
    
    Args:
        about (str): Channel description text
        
    Returns:
        str or None: Extracted username with @ or None if not found
    """
    if not about:
        return None
    
    # Looking for @username pattern in the description
    username_pattern = r'@([a-zA-Z0-9_]{5,32})'
    match = re.search(username_pattern, about)
    
    if match:
        return '@' + match.group(1)
    return None

async def get_channel_info(client, username, active_session, sessions_info):
    """
    Get channel information for a specific username
    
    Args:
        client: Telegram client
        username: Channel username (without '@')
        active_session: Current active session information
        sessions_info: List of all available sessions
        
    Returns:
        Tuple with (last_post_date, posts_last_week, description_username, session_change)
        session_change will be True if a session switch occurred
    """
    try:
        # Get channel information
        channel = await client(functions.channels.GetFullChannelRequest(
            channel=username
        ))
        
        # Get channel description
        about = channel.full_chat.about
        description_username = extract_username(about)
        
        # Get the most recent message
        messages = await client.get_messages(username, limit=1)
        last_post_date = None
        
        if messages and len(messages) > 0:
            last_post_date = messages[0].date
        
        # Get messages from the last 7 days
        week_ago = datetime.now() - timedelta(days=7)
        
        # Use offset_date to get messages from the last 7 days
        messages_last_week = await client.get_messages(
            username, 
            limit=100,  # Reasonable limit to avoid excessive API calls
            offset_date=week_ago
        )
        
        posts_last_week = len(messages_last_week)
        
        # Format the last post date for output
        formatted_date = last_post_date.strftime('%Y-%m-%d') if last_post_date else '-'
        
        return (formatted_date, posts_last_week, description_username or '-', False)
    
    except ChannelPrivateError:
        return ('Приватный канал', '-', '-', False)
    
    except UsernameNotOccupiedError:
        return ('Канал не существует', '-', '-', False)
    
    except FloodWaitError as e:
        print(f"Hit rate limit. Wait time: {e.seconds} seconds.")
        
        # Check if wait time exceeds threshold for switching
        if e.seconds > MAX_FLOOD_WAIT_TIME:
            print(f"Wait time exceeds {MAX_FLOOD_WAIT_TIME} seconds. Attempting to switch session...")
            
            # Try to switch to another session
            new_session = await switch_session(active_session, sessions_info)
            
            if new_session:
                print(f"Switched to session: {new_session['session_name']}")
                # Return a signal to indicate session switch
                return (None, None, None, True)
            else:
                print("No alternative sessions available. Waiting for the required time...")
        
        # If wait time is acceptable or no alternative sessions, wait and retry
        await asyncio.sleep(e.seconds)
        return await get_channel_info(client, username, active_session, sessions_info)
    
    except Exception as e:
        print(f"Error processing {username}: {str(e)}")
        return (f'Ошибка: {str(e)}', '-', '-', False)

async def switch_session(current_session, sessions_info):
    """
    Switch to another available session
    
    Args:
        current_session: Current session that hit rate limit
        sessions_info: List of all available sessions
        
    Returns:
        New session info or None if no available sessions
    """
    available_sessions = [
        session for session in sessions_info 
        if session['status'] == 'available' and session['session_name'] != current_session['session_name']
    ]
    
    if not available_sessions:
        return None
    
    # Update status of current session to indicate it's on cooldown
    for session in sessions_info:
        if session['session_name'] == current_session['session_name']:
            session['status'] = 'cooldown'
            session['cooldown_until'] = (datetime.now() + timedelta(minutes=30)).isoformat()
    
    # Save updated session info
    with open(SESSIONS_INFO_FILE, 'w') as f:
        json.dump(sessions_info, f, indent=4)
    
    # Return a random available session
    return random.choice(available_sessions)

async def get_available_session(sessions_info):
    """
    Get an available session from the sessions pool
    
    Args:
        sessions_info: List of all sessions
        
    Returns:
        Available session info or None if no available sessions
    """
    # Update status for sessions that were on cooldown but are now available
    current_time = datetime.now()
    
    for session in sessions_info:
        if session['status'] == 'cooldown' and 'cooldown_until' in session:
            cooldown_until = datetime.fromisoformat(session['cooldown_until'])
            if current_time > cooldown_until:
                session['status'] = 'available'
                if 'cooldown_until' in session:
                    del session['cooldown_until']
    
    # Find available sessions
    available_sessions = [session for session in sessions_info if session['status'] == 'available']
    
    if not available_sessions:
        return None
    
    # Save updated session info
    with open(SESSIONS_INFO_FILE, 'w') as f:
        json.dump(sessions_info, f, indent=4)
    
    # Return a random available session
    return random.choice(available_sessions)

def save_progress(username, is_processed):
    """
    Save progress information to allow resuming
    
    Args:
        username: Current username being processed
        is_processed: Whether processing completed successfully
    """
    progress = {
        'last_username': username,
        'is_processed': is_processed,
        'timestamp': datetime.now().isoformat()
    }
    
    # Ensure Results directory exists
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=4)

def load_progress():
    """
    Load progress information to resume from last point
    
    Returns:
        dict: Progress information or None if no progress file
    """
    if not os.path.exists(PROGRESS_FILE):
        return None
    
    try:
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading progress file: {str(e)}")
        return None

async def save_channel_result(writer, username, data):
    """
    Save channel data to CSV
    
    Args:
        writer: CSV writer object
        username: Channel username
        data: Tuple of (last_post_date, posts_last_week, description_username)
    """
    last_post_date, posts_last_week, description_username = data
    writer.writerow([username, last_post_date, posts_last_week, description_username])

async def process_channel(client, username, active_session, sessions_info, writer):
    """
    Process a single channel and save its results
    
    Args:
        client: Telegram client
        username: Channel username
        active_session: Current active session
        sessions_info: List of all sessions
        writer: CSV writer for output
        
    Returns:
        Tuple of (success, new_session, new_client) where:
            success: Whether channel was processed successfully
            new_session: New session if session switch occurred
            new_client: New client if session switch occurred
    """
    # Remove @ if it exists
    clean_username = username[1:] if username.startswith('@') else username
    
    print(f"Processing: {username}")
    
    # Get channel info
    channel_data, posts_last_week, description_username, session_changed = await get_channel_info(
        client, clean_username, active_session, sessions_info
    )
    
    # If session switch occurred
    if session_changed:
        # Get a new session
        new_session = await get_available_session(sessions_info)
        
        if not new_session:
            print("No available sessions. Cannot continue.")
            return False, None, None
        
        # Create a new client with the new session
        session_path = os.path.join(SESSIONS_DIR, new_session['session_name'])
        new_client = TelegramClient(session_path, int(API_ID), API_HASH, system_version="4.16.30-vxCUSTOM")
        
        try:
            await new_client.start()
            print(f"Started new client with session: {new_session['session_name']}")
            
            # Process the channel with the new client
            return await process_channel(new_client, username, new_session, sessions_info, writer)
        except Exception as e:
            print(f"Error starting new client: {str(e)}")
            await new_client.disconnect()
            return False, None, None
    
    # Write results to CSV
    await save_channel_result(writer, username, (channel_data, posts_last_week, description_username))
    
    # Save progress
    save_progress(username, True)
    
    # Add delay to avoid hitting rate limits too quickly
    await asyncio.sleep(1)
    
    return True, None, None

async def main():
    """
    Main function to process all channels and save results to CSV
    
    Returns:
        str: The last username being processed or None
    """
    # Check if API credentials are available
    if not API_ID or not API_HASH:
        print("Error: API credentials not found in .env file")
        print("Please create a .env file with TELEGRAM_API_ID and TELEGRAM_API_HASH")
        return None

    # Check if sessions are available
    if not os.path.exists(SESSIONS_INFO_FILE):
        print("Error: No sessions found. Please run create_sessions.py first.")
        return
    
    # Load sessions info
    try:
        with open(SESSIONS_INFO_FILE, 'r') as f:
            sessions_info = json.load(f)
    except Exception as e:
        print(f"Error loading sessions info: {str(e)}")
        return
    
    # Get an available session
    active_session = await get_available_session(sessions_info)
    
    if not active_session:
        print("No available sessions. Please create sessions using create_sessions.py")
        return
    
    print(f"Using session: {active_session['session_name']}")
    
    client = None
    try:
        # Create client with the selected session
        session_path = os.path.join(SESSIONS_DIR, active_session['session_name'])
        client = TelegramClient(session_path, int(API_ID), API_HASH, system_version="4.16.30-vxCUSTOM")
        
        try:
            await client.start()
        except UpdateAppToLoginError:
            print("\nError: Telethon version is outdated for this API request.")
            print("Try updating Telethon: pip install --upgrade telethon")
            return
        
        # Read usernames from input file
        usernames = []
        try:
            with open(INPUT_FILE, 'r', encoding='utf-8') as file:
                usernames = [line.strip() for line in file if line.strip()]
        except Exception as e:
            print(f"Error reading input file: {str(e)}")
            return
        
        # Load progress to determine where to start
        progress = load_progress()
        start_index = 0
        
        if progress and progress['last_username'] in usernames:
            last_index = usernames.index(progress['last_username'])
            
            # If last channel was processed successfully, start from next one
            if progress['is_processed']:
                start_index = last_index + 1
            else:
                # If last channel wasn't processed successfully, retry it
                start_index = last_index
                
            print(f"Resuming from index {start_index} (username: {usernames[start_index]})")
        
        # Check if we've already processed all channels
        if start_index >= len(usernames):
            print("All channels have been processed.")
            return
        
        # Create Results directory if it doesn't exist
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        # Check if output file exists and has header
        file_exists = os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0
        
        # Open CSV file in append mode if resuming
        with open(OUTPUT_FILE, 'a' if file_exists else 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header if file is new
            if not file_exists:
                writer.writerow(['Юзернейм канала', 'Дата последнего поста', 'Количество постов за неделю', 'Юзернейм из описания'])
            
            # Process each username from the starting point
            total = len(usernames)
            i = start_index
            current_username = None
            
            while i < total:
                current_username = usernames[i]
                print(f"Processing {i+1}/{total}: {current_username}")
                
                # Save that we're starting to process this username
                save_progress(current_username, False)
                
                success, new_session, new_client = await process_channel(
                    client, current_username, active_session, sessions_info, writer
                )
                
                # If session was switched, update our references
                if new_session and new_client:
                    # Close the old client
                    await client.disconnect()
                    
                    # Update to the new session and client
                    active_session = new_session
                    client = new_client
                
                # Only increment if successful
                if success:
                    i += 1
        
        print(f"Completed! Results saved to {OUTPUT_FILE}")
        return current_username
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return current_username if 'current_username' in locals() else None
    
    finally:
        # Ensure client is disconnected if it exists and is connected
        if client and client.is_connected():
            await client.disconnect()

if __name__ == "__main__":
    current_username = None
    try:
        current_username = asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        # Even when cancelled, save progress if we know the current username
        if current_username:
            save_progress(current_username, False)
            print(f"Progress saved. Resume from {current_username}")
    except Exception as e:
        print(f"\nUnhandled error: {str(e)}")