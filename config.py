import os
import sys
from dotenv import load_dotenv

# Load environment variables first before validation
load_dotenv()

# Required environment variables - bot won't start without them
REQUIRED_ENV_VARS = ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_URI", "ADMINS", "CHANNEL_ID"]

def validate_config():
    """Validate that all required environment variables are set"""
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            missing.append(var)

    if missing:
        print(f"❌ ERROR: Missing required environment variables: {', '.join(missing)}")
        print(f"💡 Please create a .env file or set these variables")
        print(f"📄 See .env.example for template")
        sys.exit(1)

# Validate configuration on import
validate_config()

# Telegram API Credentials
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Admin User IDs (comma-separated)
ADMINS = [int(x.strip()) for x in os.environ.get("ADMINS", "").split(",") if x.strip()]

# Notes Channel ID (where files are stored)
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))

# Discussion Group ID (optional)
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))

# Force Subscribe Channels/Groups
# chat_id: used by Pyrogram to verify membership reliably
# link: public username or invite link shown on join buttons
FSUB_CHATS = [
    {
        "name": "📢 Notes Channel",
        "chat_id": CHANNEL_ID if CHANNEL_ID else os.environ.get("FSUB_CHANNEL", "@YourChannel"),
        "link": os.environ.get("FSUB_CHANNEL", "@YourChannel")
    },
    {
        "name": "💬 Discussion Group",
        "chat_id": GROUP_ID if GROUP_ID else os.environ.get("FSUB_GROUP", "@YourGroup"),
        "link": os.environ.get("FSUB_GROUP", "@YourGroup")
    }
]

# MongoDB Configuration
MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = os.environ.get("DB_NAME", "NotesSearchBot")

# Optional: Log Channel
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "0")) if os.environ.get("LOG_CHANNEL") else None

# Bot Settings
SEARCH_RESULTS_LIMIT = 6
PAGINATION_LIMIT = 6
BROADCAST_SLEEP = 0.04
INDEXING_BATCH_SIZE = 200
INDEXING_SLEEP = 0.3
