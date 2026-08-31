import os

API_ID = int(os.environ.get("API_ID", "12345678"))
API_HASH = os.environ.get("API_HASH", "your_api_hash_here")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token_here")

ADMINS = [int(x) for x in os.environ.get("ADMINS", "8709673662").split()]

# 🔒 Aapka Notes Channel ID
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1004409746970"))

# 🔒 Aapka Discussion Group ID (Jahan bot ko allow karna hai)
GROUP_ID = int(os.environ.get("GROUP_ID", "-1003120344502"))

FSUB_CHATS = [
    {"name": "📢 Notes Channel", "chat": os.environ.get("FSUB_CHANNEL", "@Ca_minds")},
    {"name": "💬 Discussion Group", "chat": os.environ.get("FSUB_GROUP", "@Caaspirants_26")}
]

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority")
DB_NAME = os.environ.get("DB_NAME", "NotesSearchBot")
