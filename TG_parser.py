from telethon import TelegramClient, functions, types
from telethon.errors import ChannelPrivateError, FloodWaitError, UsernameNotOccupiedError, UpdateAppToLoginError
import csv
import os
import re
import asyncio
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

async def get_channel_info(client, username):
    """
    Get channel information for a specific username
    
    Args:
        client: Telegram client
        username: Channel username (without '@')
        
    Returns:
        Tuple with (last_post_date, posts_last_week, description_username)
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
        
        return (formatted_date, posts_last_week, description_username or '-')
    
    except ChannelPrivateError:
        return ('Приватный канал', '-', '-')
    
    except UsernameNotOccupiedError:
        return ('Канал не существует', '-', '-')
    
    except FloodWaitError as e:
        print(f"Hit rate limit. Waiting for {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
        # Retry after waiting
        return await get_channel_info(client, username)
    
    except Exception as e:
        print(f"Error processing {username}: {str(e)}")
        return (f'Ошибка: {str(e)}', '-', '-')

async def main():
    """
    Main function to process all channels and save results to CSV
    """
    # Check if API credentials are available
    if not API_ID or not API_HASH:
        print("Error: API credentials not found in .env file")
        print("Please create a .env file with TELEGRAM_API_ID and TELEGRAM_API_HASH")
        return

    client = None
    try:
        # Create client with newer API layer version
        client = TelegramClient('scraper_session', API_ID, API_HASH, system_version="4.16.30-vxCUSTOM")
        
        try:
            await client.start()
        except UpdateAppToLoginError:
            print("\nError: Your Telethon version is outdated for this API request.")
            print("Try updating Telethon: pip install --upgrade telethon")
            print("Or use a newer system_version parameter.")
            return
            
        # Check if client is authorized
        if not await client.is_user_authorized():
            print("You need to authorize first.")
            try:
                await client.send_code_request(input("Enter your phone number: "))
                await client.sign_in(input("Enter your phone number again: "), input("Enter the code: "))
            except Exception as e:
                print(f"Authentication error: {str(e)}")
                return
        
        # Read usernames from input file
        usernames = []
        try:
            with open(INPUT_FILE, 'r', encoding='utf-8') as file:
                usernames = [line.strip() for line in file if line.strip()]
        except Exception as e:
            print(f"Error reading input file: {str(e)}")
            return
        
        # Create Results directory if it doesn't exist
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        
        # Prepare CSV file
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            writer.writerow(['Юзернейм канала', 'Дата последнего поста', 'Количество постов за неделю', 'Юзернейм из описания'])
            
            # Process each username
            total = len(usernames)
            for i, username in enumerate(usernames, 1):
                # Remove @ if it exists
                clean_username = username[1:] if username.startswith('@') else username
                
                print(f"Processing {i}/{total}: {username}")
                
                # Get channel info
                last_post_date, posts_last_week, description_username = await get_channel_info(client, clean_username)
                
                # Write to CSV
                writer.writerow([username, last_post_date, posts_last_week, description_username])
                
                # Add delay to avoid hitting rate limits
                await asyncio.sleep(1)
        
        print(f"Completed! Results saved to {OUTPUT_FILE}")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    finally:
        # Ensure client is disconnected if it exists and is connected
        if client and client.is_connected():
            await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nUnhandled error: {str(e)}")