import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Required environment variables - no defaults for security
required_vars = {
    "API_ID": "API_ID",
    "API_HASH": "API_HASH", 
    "BOT_TOKEN": "BOT_TOKEN",
    "MONGO_URI": "MONGO_URI"
}

missing_vars = []
for var_name, env_name in required_vars.items():
    value = os.environ.get(env_name)
    if not value:
        missing_vars.append(env_name)
    else:
        globals()[var_name] = value

if missing_vars:
    print(f"❌ ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please set these environment variables before running the bot.")
    print("Copy .env.example to .env and fill in your credentials.")
    sys.exit(1)

# Convert API_ID to integer
try:
    API_ID = int(API_ID)
except ValueError:
    print("❌ ERROR: API_ID must be a valid integer")
    sys.exit(1)

# Optional environment variables with sensible defaults
ADMINS = [int(x) for x in os.environ.get("ADMINS", "").split(",") if x.strip()] if os.environ.get("ADMINS") else []
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0")) if os.environ.get("CHANNEL_ID") else 0
GROUP_ID = int(os.environ.get("GROUP_ID", "0")) if os.environ.get("GROUP_ID") else 0
DB_NAME = os.environ.get("DB_NAME", "NotesSearchBot")

# Force subscribe configuration
FSUB_CHATS = []
if os.environ.get("FSUB_CHANNEL"):
    FSUB_CHATS.append({"name": "📢 Notes Channel", "chat": os.environ.get("FSUB_CHANNEL")})
if os.environ.get("FSUB_GROUP"):
    FSUB_CHATS.append({"name": "💬 Discussion Group", "chat": os.environ.get("FSUB_GROUP")})
