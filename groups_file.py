import argparse
import os
import asyncio
import json
import logging
import glob
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
from telegram.constants import ChatType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_logs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = '7844532207:AAFBsx9V8B7zUKI-Q3slf9kXkZDOCirP7cA'  # Replace with your actual bot token

class TelegramGroupFileCollector:
    def __init__(self, bot_token):
        self.bot = Bot(token=bot_token)
        self.groups_data = {}
        
    async def get_all_groups(self):
        """Get all groups/chats the bot has access to"""
        try:
            # Get updates to find chats
            updates = await self.bot.get_updates()
            groups = {}
            
            for update in updates:
                if update.message and update.message.chat:
                    chat = update.message.chat
                    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
                        groups[chat.id] = {
                            'id': chat.id,
                            'title': chat.title,
                            'type': chat.type.name,
                            'username': chat.username,
                            'description': getattr(chat, 'description', ''),
                            'member_count': getattr(chat, 'member_count', 0)
                        }
            
            logger.info("Found %d groups/channels", len(groups))
            return groups
            
        except TelegramError as e:
            logger.error("Error getting groups: %s", e)
            return {}
    
    async def get_chat_files_from_updates(self, chat_id):
        """Get files from a specific chat using updates (Bot API limitation)"""
        try:
            files_data = []
            
            # Get updates to find messages with files from this chat
            updates = await self.bot.get_updates()
            
            for update in updates:
                if update.message and update.message.chat.id == chat_id:
                    message = update.message
                    
                    if message.document or message.photo or message.video or message.audio or message.voice or message.video_note:
                        file_info = {
                            'message_id': message.message_id,
                            'date': message.date.isoformat() if message.date else None,
                            'from_user': {
                                'id': message.from_user.id if message.from_user else None,
                                'username': message.from_user.username if message.from_user else None,
                                'first_name': message.from_user.first_name if message.from_user else None
                            } if message.from_user else None,
                            'caption': message.caption,
                            'file': {}
                        }
                        
                        # Document
                        if message.document:
                            file_info['file'] = {
                                'type': 'document',
                                'file_id': message.document.file_id,
                                'file_name': message.document.file_name,
                                'file_size': message.document.file_size,
                                'mime_type': message.document.mime_type
                            }
                        
                        # Photo
                        elif message.photo:
                            file_info['file'] = {
                                'type': 'photo',
                                'file_id': message.photo[-1].file_id,  # Get highest resolution
                                'file_size': message.photo[-1].file_size,
                                'width': message.photo[-1].width,
                                'height': message.photo[-1].height
                            }
                        
                        # Video
                        elif message.video:
                            file_info['file'] = {
                                'type': 'video',
                                'file_id': message.video.file_id,
                                'file_name': message.video.file_name,
                                'file_size': message.video.file_size,
                                'duration': message.video.duration,
                                'width': message.video.width,
                                'height': message.video.height
                            }
                        
                        # Audio
                        elif message.audio:
                            file_info['file'] = {
                                'type': 'audio',
                                'file_id': message.audio.file_id,
                                'file_name': message.audio.file_name,
                                'file_size': message.audio.file_size,
                                'duration': message.audio.duration,
                                'performer': message.audio.performer,
                                'title': message.audio.title
                            }
                        
                        # Voice
                        elif message.voice:
                            file_info['file'] = {
                                'type': 'voice',
                                'file_id': message.voice.file_id,
                                'file_size': message.voice.file_size,
                                'duration': message.voice.duration
                            }
                        
                        # Video Note
                        elif message.video_note:
                            file_info['file'] = {
                                'type': 'video_note',
                                'file_id': message.video_note.file_id,
                                'file_size': message.video_note.file_size,
                                'duration': message.video_note.duration,
                                'length': message.video_note.length
                            }
                        
                        files_data.append(file_info)
                
            logger.info("Found %d files in chat %s from updates", len(files_data), chat_id)
            return files_data
            
        except TelegramError as e:
            logger.error("Error getting files from chat %s: %s", chat_id, e)
            return []
    
    async def collect_all_data(self):
        """Collect all groups and their files"""
        logger.info("Starting data collection...")
        
        # Get all groups
        groups = await self.get_all_groups()
        
        for chat_id, group_info in groups.items():
            logger.info("Processing group: %s (ID: %s)", group_info['title'], chat_id)
            
            files = await self.get_chat_files_from_updates(chat_id)
            print(files)
            # Store data
            self.groups_data[chat_id] = {
                'group_info': group_info,
                'files': files,
                'file_count': len(files),
                'collected_at': datetime.now().isoformat()
            }
        
        logger.info("Data collection completed. Processed %d groups.", len(groups))
        return self.groups_data
    
    async def save_to_json(self, filename='telegram_groups_data.json'):
        """Save collected data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.groups_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Data saved to %s", filename)
            return True

        except (IOError, OSError, TypeError) as e:
            logger.error("Error saving to JSON: %s", e)
            return False

    async def load_from_json(self, filename='telegram_groups_data.json'):
        """Load data from JSON file"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    self.groups_data = json.load(f)
                logger.info("Data loaded from %s", filename)
                return True
            else:
                logger.warning("File %s not found", filename)
                return False
                
        except (IOError, OSError, ValueError) as e:
            logger.error("Error loading from JSON: %s", e)
            return False

async def main():
    """Main function to run the bot"""
    parser = argparse.ArgumentParser(description='Telegram Group File Collector')
    parser.add_argument('--token', help='Bot token (or set BOT_TOKEN in code)')
    parser.add_argument('--output', default='telegram_groups_data.json', help='Output JSON file')
    parser.add_argument('--load', help='Load existing data from JSON file')
    parser.add_argument('--list-chats', action='store_true', help='List all available chats')
    parser.add_argument('--send-files', action='store_true', help='Send files to chat')
    
    args = parser.parse_args()
    
    # Use provided token or the one in code
    token = args.token or BOT_TOKEN
    
    if not token or token == 'YOUR_BOT_TOKEN':
        logger.error("Please set your bot token in the code or use --token argument")
        return
    
    # List available chats
    if args.list_chats:
        await get_available_chats()
        return
    
    # Send files to chat
    if args.send_files:
        await send_file_to_chat()
        return
    
    collector = TelegramGroupFileCollector(token)
    
    # Load existing data if specified
    if args.load:
        await collector.load_from_json(args.load)
    else:
        # Collect new data
        await collector.collect_all_data()
    
    # Save to JSON
    await collector.save_to_json(args.output)
    
    # Print summary
    total_groups = len(collector.groups_data)
    total_files = sum(group['file_count'] for group in collector.groups_data.values())
    
    print("\n=== SUMMARY ===")
    print(f"Total groups processed: {total_groups}")
    print(f"Total files found: {total_files}")
    print(f"Data saved to: {args.output}")
    
    for chat_id, data in collector.groups_data.items():
        print(f"\nGroup: {data['group_info']['title']}")
        print(f"  - Chat ID: {chat_id}")
        print(f"  - Type: {data['group_info']['type']}")
        print(f"  - Files: {data['file_count']}")

async def send_file(bot: Bot, file_path: str, chat_id: int):
    try:
        # Check file size (Telegram limit is 50MB)
        file_size = os.path.getsize(file_path)
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        
        if file_size > max_size:
            print(f'File too large: {file_path} ({file_size / (1024*1024):.1f}MB > 50MB)')
            return False
        
        print(f'Sending file: {file_path} ({file_size / (1024*1024):.1f}MB)')
        
        # Open the file and send it directly with timeout handling
        with open(file_path, 'rb') as file:
            await asyncio.wait_for(
                bot.send_document(chat_id=chat_id, document=file),
                timeout=300  # 5 minutes timeout
            )
        print(f'Successfully sent: {file_path}')
        return True
        
    except asyncio.TimeoutError:
        print(f'Upload timed out for: {file_path} (file might be too large or connection slow)')
        return False
    except TelegramError as e:
        if "Chat not found" in str(e):
            print(f'Chat not found. Please check if the bot is added to the chat with ID: {chat_id}')
        elif "Request Entity Too Large" in str(e):
            print(f'File too large for Telegram: {file_path}')
        elif "Timed out" in str(e):
            print(f'Upload timed out for: {file_path} (file might be too large or connection slow)')
        else:
            print(f'Telegram error sending {file_path}: {e}')
        return False
    except FileNotFoundError:
        print(f'File not found: {file_path}')
        return False
    except Exception as e:
        print(f'Unexpected error sending {file_path}: {e}')
        return False

async def verify_chat_access(bot: Bot, chat_id: int) -> bool:
    """Verify if the bot has access to the chat"""
    try:
        chat = await bot.get_chat(chat_id)
        print(f"Chat verified: {chat.title} (ID: {chat_id})")
        return True
    except TelegramError as e:
        print(f"Cannot access chat {chat_id}: {e}")
        return False

async def get_available_chats():
    """Get all chats the bot has access to"""
    try:
        bot = Bot(token=BOT_TOKEN)
        updates = await bot.get_updates()
        chats = {}
        
        for update in updates:
            if update.message and update.message.chat:
                chat = update.message.chat
                chats[chat.id] = {
                    'id': chat.id,
                    'title': chat.title,
                    'type': chat.type.name,
                    'username': chat.username
                }
        
        print("Available chats:")
        for chat_id, info in chats.items():
            print(f"  ID: {chat_id}, Title: {info['title']}, Type: {info['type']}")
        
        return chats
    except Exception as e:
        print(f"Error getting chats: {e}")
        return {}

async def send_file_to_chat() -> None:
    path = "D:\\*.zip"  # Pattern to match .zip files
    files = glob.glob(path)
    print(f"Found files: {files}")
    
    token = BOT_TOKEN
    bot = Bot(token=token)
    chat_id = -1002903482939
    
    # Verify chat access first
    if not await verify_chat_access(bot, chat_id):
        print("Cannot proceed without chat access. Please:")
        print("1. Make sure the bot is added to the chat")
        print("2. Check if the chat ID is correct")
        print("3. Ensure the bot has permission to send messages")
        return
    
    if not files:
        print("No .zip files found in D:\\")
        return
    
    successful = 0
    failed = 0
    
    for file_path in files:
        if os.path.isfile(file_path):
            success = await send_file(bot, file_path, chat_id)
            if success:
                successful += 1
            else:
                failed += 1
        else:
            print(f"Not a file: {file_path}")
            failed += 1
    
    print(f"\n=== SUMMARY ===")
    print(f"Successfully sent: {successful} files")
    print(f"Failed to send: {failed} files")

if __name__ == "__main__":
    
    asyncio.run(send_file_to_chat())