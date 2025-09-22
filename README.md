# Telegram Group File Collector

This bot collects all groups/channels that it has access to, retrieves all files from each group, and saves the data to JSON for reuse.

## Features

- **Get All Groups**: Automatically discovers all groups, supergroups, and channels the bot has access to
- **File Collection**: For each group, collects all files including:
  - Documents
  - Photos
  - Videos
  - Audio files
  - Voice messages
  - Video notes
- **JSON Export**: Saves all data to JSON format for easy reuse
- **Comprehensive Data**: Includes file metadata, chat information, and user details
- **Error Handling**: Robust error handling with detailed logging
- **Load/Save**: Can load existing data and append new data

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Get your bot token from [@BotFather](https://t.me/botfather)

3. Update the bot token in `groups_file.py`:
```python
BOT_TOKEN = 'your_actual_bot_token_here'
```

## Usage

### Basic Usage
```bash
python groups_file.py
```

### With Custom Output File
```bash
python groups_file.py --output my_data.json
```

### With Custom Token
```bash
python groups_file.py --token YOUR_BOT_TOKEN
```

### Load Existing Data
```bash
python groups_file.py --load existing_data.json
```

## Output Format

The JSON output contains:
```json
{
  "chat_id": {
    "group_info": {
      "id": "chat_id",
      "title": "Group Name",
      "type": "GROUP|SUPERGROUP|CHANNEL",
      "username": "@group_username",
      "description": "Group description",
      "member_count": 123
    },
    "files": [
      {
        "message_id": 123,
        "date": "2024-01-01T12:00:00",
        "from_user": {
          "id": 123456789,
          "username": "username",
          "first_name": "First Name"
        },
        "caption": "File caption",
        "file": {
          "type": "document|photo|video|audio|voice|video_note",
          "file_id": "file_id_here",
          "file_name": "filename.ext",
          "file_size": 1024,
          "mime_type": "application/pdf"
        }
      }
    ],
    "file_count": 5,
    "collected_at": "2024-01-01T12:00:00"
  }
}
```

## Logging

The bot creates detailed logs in `bot_logs.log` and displays progress in the console.

## Important Notes

- Make sure your bot is added to the groups/channels you want to collect data from
- The bot needs appropriate permissions to read messages and files
- **Bot API Limitation**: The bot can only access recent messages from `get_updates()`. It cannot access full chat history like a user client would.
- The bot will only collect files from messages that appear in recent updates
- Large groups with many files may take time to process
- The bot respects Telegram's rate limits automatically

## Bot API Limitations

The Telegram Bot API has limitations compared to user clients:

- **No Chat History Access**: Bots cannot retrieve full chat history
- **Updates Only**: Bots can only access recent messages through `get_updates()`
- **Recent Messages**: Only messages that trigger updates to your bot will be accessible

### Alternative Solutions

For full chat history access, you would need to use:
- **Telethon** (Python library for user accounts)
- **Pyrogram** (Python library for user accounts)
- **User Account**: Requires your personal Telegram account credentials

These alternatives can access full chat history but require user account setup and have different security considerations.

## Troubleshooting

1. **"Please set your bot token"**: Update the `BOT_TOKEN` variable in the code
2. **"Error getting groups"**: Ensure your bot is added to at least one group
3. **"Error getting files"**: Check if the bot has permission to read messages in the group
4. **Empty results**: Make sure there are recent messages in the groups (the bot uses `get_updates()` to discover groups)
