import os

# Telegram API Credentials (my.telegram.org se milega)
API_ID = int(os.environ.get("API_ID", "12345678"))
API_HASH = os.environ.get("API_HASH", "your_api_hash_here")

# Bot Token (@BotFather se milega)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token_here")

# Admin IDs (Apna Telegram User ID daalein)
ADMINS = [int(x) for x in os.environ.get("ADMINS", "8709673662").split()]

# Notes Channel ID jisme se files search karni hai (e.g. -1001234567890)
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1003990661985"))

# Force Subscribe Channels/Groups (Username ya Chat ID)
# Dono mein bot ka Admin hona zaroori hai
FSUB_CHATS = [
    {"name": "📢 Main Notes Channel", "chat": os.environ.get("FSUB_CHANNEL", "@Ca_minds")},
    {"name": "💬 Discussion Group", "chat": os.environ.get("FSUB_GROUP", "@Caaspirants_26")}
]

# MongoDB Connection URL (MongoDB Atlas se free cluster banayein)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = os.environ.get("DB_NAME", "NotesSearchBot")
