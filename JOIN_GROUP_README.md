# Telegram Group Joiner and Crawler

This script allows you to join multiple Telegram groups from a text list file, get detailed group information, and crawl member data.

## Features

- **Join Groups from List**: Read group identifiers from a text file
- **Group Information**: Get detailed info about each group
- **Member Crawling**: Extract administrator information and member counts
- **File Discovery**: Find recent files shared in groups
- **JSON Export**: Save all data to JSON format
- **Error Handling**: Robust error handling with detailed logging

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Update the bot token in `join_group.py`:
```python
BOT_TOKEN = 'your_actual_bot_token_here'
```

3. Create a groups list file (see `groups.txt` for format)

## Usage

### Basic Usage
```bash
python join_group.py
```

### With Custom Groups File
```bash
python join_group.py --groups my_groups.txt
```

### With Custom Output
```bash
python join_group.py --output my_data.json
```

### With Custom Token
```bash
python join_group.py --token YOUR_BOT_TOKEN
```

## Groups List Format

Create a text file with group identifiers, one per line:

```
# Comments start with #
@group_username
https://t.me/group_username
-1001234567890
@another_group
```

### Supported Formats:
- `@username` - Group username
- `https://t.me/username` - Full invite link
- `-1001234567890` - Group ID (for private groups)

## Output Format

The JSON output contains:

```json
{
  "group_id": {
    "group_info": {
      "id": "group_id",
      "title": "Group Name",
      "type": "GROUP|SUPERGROUP|CHANNEL",
      "username": "@group_username",
      "description": "Group description",
      "member_count": 1234,
      "invite_link": "https://t.me/+invite_link",
      "joined_at": "2024-01-01T12:00:00"
    },
    "members": {
      "administrators": [
        {
          "user_id": 123456789,
          "username": "admin_username",
          "first_name": "Admin",
          "last_name": "Name",
          "is_bot": false,
          "status": "ADMINISTRATOR",
          "can_manage_chat": true,
          "can_delete_messages": true,
          "can_restrict_members": true,
          "can_promote_members": true,
          "can_change_info": true,
          "can_invite_users": true,
          "can_pin_messages": true
        }
      ],
      "admin_count": 5,
      "total_member_count": 1234
    },
    "recent_files": [
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
          "type": "document",
          "file_id": "file_id_here",
          "file_name": "filename.ext",
          "file_size": 1024,
          "mime_type": "application/pdf"
        }
      }
    ],
    "crawled_at": "2024-01-01T12:00:00"
  }
}
```

## Bot API Limitations

### What the Bot Can Do:
- ✅ Access public groups and channels
- ✅ Get group information (title, description, member count)
- ✅ Get administrator list and their permissions
- ✅ Get recent files from updates
- ✅ Get member count

### What the Bot Cannot Do:
- ❌ Get complete member list (only administrators)
- ❌ Access private groups without invite links
- ❌ Get full chat history
- ❌ Get member details beyond administrators

## Important Notes

1. **Bot Permissions**: Your bot needs to be added to the groups or have access to public groups
2. **Rate Limiting**: The script includes delays to avoid Telegram rate limits
3. **Private Groups**: For private groups, you need invite links or the bot must be added
4. **Member Access**: Bot API can only access administrators, not regular members
5. **File Access**: Only recent files from updates are accessible

## Troubleshooting

### "Chat not found" Error
- Check if the group username is correct
- Ensure the group is public or the bot has access
- For private groups, use invite links

### "Bot is not a member" Error
- Add your bot to the group first
- Use invite links for private groups

### "Forbidden" Error
- The bot doesn't have permission to access the group
- Check if the group allows bots

### No Members Found
- Bot API cannot get regular members, only administrators
- This is a Telegram API limitation

## Example Workflow

1. **Create groups list**:
```bash
echo "@example_group1" > groups.txt
echo "@example_group2" >> groups.txt
```

2. **Run the crawler**:
```bash
python join_group.py --groups groups.txt
```

3. **Check results**:
```bash
# View the JSON output
cat group_crawl_data.json
```

## Logging

The script creates detailed logs in `join_group_logs.log` and displays progress in the console.

## Security Notes

- Keep your bot token secure
- Be respectful of group rules and privacy
- Don't abuse the API with too many requests
- Consider the privacy implications of crawling group data
