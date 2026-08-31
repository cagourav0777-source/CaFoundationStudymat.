# 📚 CA Notes Master Bot

A powerful Telegram bot for CA students to search and access study materials instantly. Built with Python and Pyrogram.

## ✨ Features

### For Students
- 🔍 **Smart Search Engine** - Find notes, PDFs, videos, and Google Drive links instantly
- 📱 **DM & Group Support** - Works in private chat and study groups
- 🎯 **Intelligent Matching** - Advanced search algorithm finds relevant materials
- 📄 **Multi-Format Support** - Documents, photos, videos, audio, and text notes
- ⚡ **Instant Delivery** - Click and receive files directly in your DM
- 🔗 **Deep Linking** - Share direct file links from groups
- 🎨 **Pagination** - Browse through large search results easily
- 🔒 **Force Subscribe** - Optional channel/group joining requirement

### For Admins
- 📊 **Statistics Dashboard** - Track users, groups, and indexed files
- 📢 **Broadcast System** - Send announcements to all users and groups
- 🗂️ **Auto-Indexing** - Automatically indexes files from your channel
- 📁 **Manual Indexing** - Index historical files with `/index` command
- ⚙️ **FSUB Control** - Enable/disable force subscribe anytime
- 👥 **User Management** - Track and manage bot users

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- MongoDB database (free tier from MongoDB Atlas)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Telegram API credentials (from [my.telegram.org](https://my.telegram.org))

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/studymatbot.git
cd studymatbot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Run the bot**
```bash
python bot.py
```

## ⚙️ Configuration

Edit `.env` file with your credentials:

```env
API_ID=12345678                    # From my.telegram.org
API_HASH=your_api_hash             # From my.telegram.org
BOT_TOKEN=123456:ABC-DEF...        # From @BotFather
ADMINS=123456789,987654321         # Admin user IDs (comma-separated)
CHANNEL_ID=-1001234567890          # Your files channel ID
GROUP_ID=-1001234567890            # Your discussion group ID
FSUB_CHANNEL=@YourChannel          # Force subscribe channel username
FSUB_GROUP=@YourGroup              # Force subscribe group username
MONGO_URI=mongodb+srv://...        # MongoDB connection string
DB_NAME=NotesSearchBot             # Database name
```

### Getting IDs
- **User ID**: Send `/id` to the bot in private chat
- **Channel/Group ID**: Forward a message from the channel/group to [@userinfobot](https://t.me/userinfobot)

## 📖 User Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot and see welcome message |
| `/id` | Get your user ID or group chat ID |
| `<any text>` | Search for study materials (in DM) |
| `/search <query>` | Search in groups |
| `/notes <query>` | Alternative search command (groups) |
| `/get <query>` | Alternative search command (groups) |

## 🔑 Admin Commands

| Command | Description |
|---------|-------------|
| `/stats` | View bot statistics (users, groups, files) |
| `/index` | Manually index all channel files |
| `/broadcast` | Send message to all users and groups |
| `/startfsub` | Enable force subscribe |
| `/stopfsub` | Disable force subscribe |
| `/fsub on/off` | Toggle force subscribe |

### Broadcast Usage
```bash
# Method 1: Reply to a message
/broadcast (reply to any message/photo/video)

# Method 2: Direct text
/broadcast Your announcement message here
```

## 🎯 How It Works

1. **Indexing**: Bot automatically saves files from your configured channel to MongoDB
2. **Search**: Users search with keywords, bot performs intelligent matching
3. **Delivery**: Files are delivered directly via inline buttons or deep links
4. **Groups**: In groups, buttons redirect users to DM for file delivery

## 🏗️ Project Structure

```
studymatbot-main/
├── bot.py              # Main bot application
├── config.py           # Configuration management
├── database.py         # MongoDB operations
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (create from .env.example)
├── .env.example       # Environment template
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

## 📊 Search Algorithm

The bot uses a two-tier search system:

1. **Strict Search**: Matches all keywords (AND logic)
2. **Smart Fallback**: Filters common words and uses OR logic for better results

This ensures minimal false negatives while maintaining relevance.

## 🔒 Security Features

- Admin-only commands with ID verification
- Environment-based configuration (no hardcoded secrets)
- MongoDB injection protection with regex escaping
- FloodWait handling for Telegram rate limits

## 🐛 Troubleshooting

### Bot not starting
- Check if all environment variables are set correctly
- Verify MongoDB connection string is valid
- Ensure bot token is correct

### Files not indexing
- Verify bot is admin in the channel
- Check CHANNEL_ID is correct (should be negative number)
- Run `/index` command manually

### Search returns no results
- Run `/index` first to populate database
- Check if files have captions or filenames
- Try broader keywords

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 📧 Support

For support, join our discussion group or contact the admin.

---

**Made with ❤️ for CA Aspirants**
