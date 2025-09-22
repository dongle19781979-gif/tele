# File Organizer with Gemini README Generator

This utility scans a folder, creates a new subfolder for each file, copies or moves the file into it, and generates a README.md per item using Google Gemini (optional).

## 1) Setup

1. Install Python 3.9+
2. Create a virtual environment (recommended):
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your Google API key (optional, for AI generation):
   - Copy `.env.example` to `.env`
   - Paste your key: `GOOGLE_API_KEY=...`

If you skip the API key, pass `--skip-ai` and the script will generate a simple README template instead.

## 2) Usage

Basic:
```bash
python3 organize_with_gemini.py --source-dir /absolute/path/to/folder
```

Options:
- `--output-dir`: Destination base (default: `<source>_organized`)
- `--move`: Move instead of copy (default is copy)
- `--include-ext`: Comma-separated filter (e.g., `.py,.md`)
- `--exclude-ext`: Comma-separated exclusion list (e.g., `.png,.jpg`)
- `--readme-filename`: Name for generated readme (default `README.md`)
- `--model`: Gemini model (default `gemini-1.5-flash`)
- `--skip-ai`: Disable AI and use a fallback template
- `--overwrite`: Overwrite existing folders/READMEs
- `--dry-run`: Print actions without making changes
- `--verbose`: More logs

Examples:
```bash
# Copy files and generate AI README
python3 organize_with_gemini.py --source-dir /data/my_files

# Move files, restrict to .py and .md, skip AI
python3 organize_with_gemini.py --source-dir /data/my_files --move --include-ext .py,.md --skip-ai

# Custom output directory and model
python3 organize_with_gemini.py --source-dir /data/my_files --output-dir /data/organized --model gemini-1.5-pro
```

## Notes
- The script reads a small snippet of each file (if textual) to help Gemini infer a purpose.
- If a target subfolder already exists and `--overwrite` is not set, it will be skipped.
- Hidden files are included if present in the source directory.

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
