import asyncio
import json
import logging
import os
import argparse
from datetime import datetime
from telegram import Bot, ChatMember
from telegram.error import TelegramError
from telegram.constants import ChatType, ChatMemberStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('join_group_logs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = '7844532207:AAFBsx9V8B7zUKI-Q3slf9kXkZDOCirP7cA'  # Replace with your actual bot token

class TelegramGroupJoiner:
    def __init__(self, bot_token):
        self.bot = Bot(token=bot_token)
        self.joined_groups = {}
        
    async def read_group_list(self, filename):
        """Read group list from text file"""
        try:
            groups = []
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):  # Skip empty lines and comments
                        groups.append(line)
            
            logger.info("Read %d groups from %s", len(groups), filename)
            return groups
            
        except FileNotFoundError:
            logger.error("File not found: %s", filename)
            return []
        except Exception as e:
            logger.error("Error reading group list: %s", e)
            return []
    
    async def join_group(self, group_identifier):
        """Join a group using username or invite link"""
        try:
            # Try to get chat info first
            chat = await self.bot.get_chat(group_identifier)
            
            # Check if it's a group or channel
            if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]:
                logger.warning("Not a group/channel: %s", group_identifier)
                return None
            
            # Get basic group info
            group_info = {
                'id': chat.id,
                'title': chat.title,
                'type': chat.type.name,
                'username': chat.username,
                'description': getattr(chat, 'description', ''),
                'member_count': getattr(chat, 'member_count', 0),
                'invite_link': getattr(chat, 'invite_link', ''),
                'joined_at': datetime.now().isoformat()
            }
            
            logger.info("Successfully accessed group: %s (ID: %s)", chat.title, chat.id)
            return group_info
            
        except TelegramError as e:
            logger.error("Failed to access group %s: %s", group_identifier, e)
            return None
    
    async def get_group_members(self, chat_id, limit=200):
        """Get all members from a group"""
        try:
            members = []
            offset = 0
            
            # Get chat administrators first
            admins = await self.bot.get_chat_administrators(chat_id)
            admin_ids = {admin.user.id for admin in admins}
            
            # Get chat members (this might be limited by Telegram API)
            try:
                # Note: get_chat_member_count is available, but getting all members is limited
                member_count = await self.bot.get_chat_member_count(chat_id)
                logger.info("Group has %d members", member_count)
                
                # For public groups, we can try to get some members through updates
                # This is a limitation of the Bot API
                logger.warning("Bot API cannot get all members. Only administrators are accessible.")
                
            except TelegramError as e:
                logger.error("Cannot get member count: %s", e)
                member_count = 0
            
            # Store admin information
            for admin in admins:
                member_info = {
                    'user_id': admin.user.id,
                    'username': admin.user.username,
                    'first_name': admin.user.first_name,
                    'last_name': admin.user.last_name,
                    'is_bot': admin.user.is_bot,
                    'status': admin.status.name,
                    'can_be_edited': getattr(admin, 'can_be_edited', False),
                    'can_manage_chat': getattr(admin, 'can_manage_chat', False),
                    'can_delete_messages': getattr(admin, 'can_delete_messages', False),
                    'can_manage_video_chats': getattr(admin, 'can_manage_video_chats', False),
                    'can_restrict_members': getattr(admin, 'can_restrict_members', False),
                    'can_promote_members': getattr(admin, 'can_promote_members', False),
                    'can_change_info': getattr(admin, 'can_change_info', False),
                    'can_invite_users': getattr(admin, 'can_invite_users', False),
                    'can_pin_messages': getattr(admin, 'can_pin_messages', False)
                }
                members.append(member_info)
            
            logger.info("Found %d administrators in group %s", len(members), chat_id)
            return members, member_count
            
        except TelegramError as e:
            logger.error("Error getting members from group %s: %s", chat_id, e)
            return [], 0
    
    async def crawl_group_data(self, group_identifier):
        """Crawl all data from a group"""
        logger.info("Starting crawl for group: %s", group_identifier)
        
        # Join/get group info
        group_info = await self.join_group(group_identifier)
        if not group_info:
            return None
        
        # Get members
        members, member_count = await self.get_group_members(group_info['id'])
        
        # Get recent messages/files (limited by Bot API)
        recent_files = await self.get_recent_files(group_info['id'])
        
        group_data = {
            'group_info': group_info,
            'members': {
                'administrators': members,
                'admin_count': len(members),
                'total_member_count': member_count
            },
            'recent_files': recent_files,
            'crawled_at': datetime.now().isoformat()
        }
        
        return group_data
    
    async def get_recent_files(self, chat_id):
        """Get recent files from group (limited by Bot API)"""
        try:
            files = []
            updates = await self.bot.get_updates()
            
            for update in updates:
                if update.message and update.message.chat and update.message.chat.id == chat_id:
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
                                'file_id': message.photo[-1].file_id,
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
                                'duration': message.video.duration
                            }
                        
                        # Audio
                        elif message.audio:
                            file_info['file'] = {
                                'type': 'audio',
                                'file_id': message.audio.file_id,
                                'file_name': message.audio.file_name,
                                'file_size': message.audio.file_size,
                                'duration': message.audio.duration
                            }
                        
                        files.append(file_info)
            
            logger.info("Found %d recent files in group %s", len(files), chat_id)
            return files
            
        except TelegramError as e:
            logger.error("Error getting files from group %s: %s", chat_id, e)
            return []
    
    async def process_group_list(self, group_list_file):
        """Process all groups from the list file"""
        groups = await self.read_group_list(group_list_file)
        
        if not groups:
            logger.error("No groups found in file: %s", group_list_file)
            return
        
        logger.info("Processing %d groups...", len(groups))
        
        for i, group_identifier in enumerate(groups, 1):
            logger.info("Processing group %d/%d: %s", i, len(groups), group_identifier)
            
            try:
                group_data = await self.crawl_group_data(group_identifier)
                if group_data:
                    self.joined_groups[group_data['group_info']['id']] = group_data
                    logger.info("Successfully crawled group: %s", group_data['group_info']['title'])
                else:
                    logger.warning("Failed to crawl group: %s", group_identifier)
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error("Unexpected error processing group %s: %s", group_identifier, e)
        
        logger.info("Completed processing %d groups", len(groups))
    
    async def save_to_json(self, filename='group_crawl_data.json'):
        """Save crawled data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.joined_groups, f, indent=2, ensure_ascii=False)
            
            logger.info("Data saved to %s", filename)
            return True
            
        except Exception as e:
            logger.error("Error saving to JSON: %s", e)
            return False

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Telegram Group Joiner and Crawler')
    parser.add_argument('--token', help='Bot token (or set BOT_TOKEN in code)')
    parser.add_argument('--groups', default='groups.txt', help='Text file with group list')
    parser.add_argument('--output', default='group_crawl_data.json', help='Output JSON file')
    
    args = parser.parse_args()
    
    # Use provided token or the one in code
    token = args.token or BOT_TOKEN
    
    if not token or token == 'YOUR_BOT_TOKEN':
        logger.error("Please set your bot token in the code or use --token argument")
        return
    
    joiner = TelegramGroupJoiner(token)
    
    # Process groups
    await joiner.process_group_list(args.groups)
    
    # Save data
    await joiner.save_to_json(args.output)
    
    # Print summary
    total_groups = len(joiner.joined_groups)
    total_admins = sum(group['members']['admin_count'] for group in joiner.joined_groups.values())
    total_members = sum(group['members']['total_member_count'] for group in joiner.joined_groups.values())
    
    print("\n=== CRAWL SUMMARY ===")
    print(f"Total groups processed: {total_groups}")
    print(f"Total administrators found: {total_admins}")
    print(f"Total members (estimated): {total_members}")
    print(f"Data saved to: {args.output}")
    
    for group_id, data in joiner.joined_groups.items():
        group_info = data['group_info']
        members = data['members']
        print(f"\nGroup: {group_info['title']}")
        print(f"  - ID: {group_id}")
        print(f"  - Type: {group_info['type']}")
        print(f"  - Members: {members['total_member_count']}")
        print(f"  - Admins: {members['admin_count']}")
        print(f"  - Recent files: {len(data['recent_files'])}")

if __name__ == "__main__":
    asyncio.run(main())
