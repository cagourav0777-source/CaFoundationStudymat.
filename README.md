# StudyMatBot - CA Notes Search Bot

A Telegram bot for searching and delivering CA Foundation & Inter study materials including notes, question banks, MTPs, RTPs, and more.

## 🚀 Features

- **Smart Search**: Two-tier search algorithm with strict matching and smart fallback
- **Multi-Media Support**: Handles PDFs, photos, videos, audio, and text messages
- **Force Subscribe**: Optional forced subscription to channels/groups
- **Auto-Indexing**: Real-time channel monitoring for automatic file indexing
- **Deep Links**: Direct file delivery from groups to DM
- **Pagination**: Navigate through search results with prev/next buttons
- **Admin Controls**: Indexing, stats, broadcasting, and FSUB management
- **Inline Search**: Search directly from Telegram's chat input
- **Rate Limiting**: Prevents abuse with search rate limits
- **Logging**: Comprehensive logging for debugging and monitoring

## 🛠️ Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
API_ID=your_api_id_here
API_HASH=your_api_hash_here
BOT_TOKEN=your_bot_token_here
ADMINS=123456789,987654321
CHANNEL_ID=-1001234567890
GROUP_ID=-1009876543210
FSUB_CHANNEL=@your_channel_username
FSUB_GROUP=@your_group_username
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
DB_NAME=NotesSearchBot
```

### 3. Get Telegram Credentials

1. Get `API_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org)
2. Create a bot via [@BotFather](https://t.me/BotFather) to get `BOT_TOKEN`
3. Add your bot to your channel as admin
4. Get Channel ID and Group ID (use `/id` command in Telegram)

### 4. Setup MongoDB

Create a free MongoDB Atlas cluster and get your connection string.

### 5. Run the Bot

```bash
python bot.py
```

## 📋 Commands

### User Commands
- `/start` - Start the bot and welcome message
- `/id` - Get your Telegram ID or Group Chat ID

### Admin Commands
- `/index` - Index all files from the channel
- `/stats` - View bot statistics (users, groups, files)
- `/broadcast` - Broadcast message to all users and groups
- `/startfsub` - Enable force subscribe
- `/stopfsub` - Disable force subscribe
- `/fsub` - Check force subscribe status

### Group Commands
- `/search <topic>` - Search for study materials in groups

## 🔧 Configuration Constants

Edit these in `bot.py` to customize behavior:

```python
MIN_TEXT_LENGTH = 4           # Minimum text length for text messages
MIN_QUERY_LENGTH = 2          # Minimum characters for search
SEARCH_RESULTS_LIMIT = 6      # Results per page
TITLE_MAX_LENGTH = 36         # Max length for button titles
INDEXING_BATCH_SIZE = 200     # Messages per indexing batch
BROADCAST_DELAY = 0.04        # Delay between broadcast messages
FSUB_CHECK_DELAY = 0.3         # Delay for force subscribe checks
RATE_LIMIT_SEARCH = 3          # Max searches per minute
RATE_LIMIT_PERIOD = 60         # Rate limit time window (seconds)
```

## 🐛 Bug Fixes Applied

1. **Fixed broadcast command bug** - Now properly extracts text from message
2. **Removed hardcoded credentials** - Environment variables are now required
3. **Fixed deprecated asyncio usage** - Updated to use `asyncio.run()`
4. **Added MongoDB connection handling** - Proper error handling and connection pooling
5. **Added input sanitization** - Prevents injection attacks in callback data
6. **Added constants for magic numbers** - Improved code maintainability
7. **Improved indexing efficiency** - Added safety limits and progress tracking
8. **Added proper logging** - Replaced print statements with logging module
9. **Added rate limiting** - Prevents search abuse (3 searches per minute)

## 📁 File Structure

```
studymatbot-main/
├── bot.py              # Main bot logic and handlers
├── config.py           # Configuration and environment variables
├── database.py         # MongoDB operations and search algorithm
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
├── .env                # Your actual environment variables (not in git)
├── bot.log            # Bot logs (created automatically)
└── README.md          # This file
```

## 🔒 Security Notes

- Never commit `.env` file to version control
- Use strong MongoDB passwords
- Limit admin IDs to trusted users only
- Keep your API credentials secure
- Use environment variables for all sensitive data

## 📊 Database Schema

### Files Collection
```json
{
  "file_id": "string",
  "file_name": "string", 
  "file_size": integer,
  "caption": "string",
  "chat_id": integer,
  "message_id": integer,
  "media_type": "string"
}
```

### Users Collection
```json
{
  "user_id": integer,
  "name": "string"
}
```

### Groups Collection
```json
{
  "chat_id": integer,
  "title": "string"
}
```

### Settings Collection
```json
{
  "key": "fsub_status",
  "enabled": boolean
}
```

## 🚦 Troubleshooting

### Bot won't start
- Check all environment variables are set in `.env`
- Verify MongoDB connection string is correct
- Ensure bot token is valid
- Check `bot.log` for error messages

### Search not working
- Run `/index` command to index channel files
- Check MongoDB connection
- Verify channel ID is correct
- Check bot has admin rights in channel

### Force subscribe issues
- Verify FSUB_CHANNEL and FSUB_GROUP usernames
- Check bot is admin in those channels/groups
- Use `/fsub` command to check status

## 📝 License

This project is provided as-is for educational purposes.

## 🤝 Contributing

Feel free to submit issues and enhancement requests!