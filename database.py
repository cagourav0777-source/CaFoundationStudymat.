import re
import logging
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import MONGO_URI, DB_NAME

logger = logging.getLogger(__name__)

# Initialize MongoDB client with timeout
try:
    client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]

    files_col = db["files"]
    users_col = db["users"]
    groups_col = db["groups"]
    settings_col = db["settings"]
except Exception as e:
    logger.error(f"Failed to initialize MongoDB client: {e}")
    raise

async def init_db():
    """Initialize database with indexes"""
    try:
        # Test connection first
        await client.admin.command('ping')
        logger.info("✅ MongoDB connection established successfully")

        # Create indexes
        await files_col.create_index([("file_name", "text"), ("caption", "text")])
        await files_col.create_index([("chat_id", 1), ("message_id", 1)], unique=True)
        await users_col.create_index("user_id", unique=True)
        await groups_col.create_index("chat_id", unique=True)

        logger.info("✅ Database indexes created successfully")
        return True
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise Exception("Failed to connect to MongoDB. Check your MONGO_URI.")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        raise

# ----------------- Settings (FSUB Toggle) -----------------
async def set_fsub_status(enabled: bool):
    """Set force subscribe status"""
    try:
        await settings_col.update_one(
            {"key": "fsub_status"},
            {"$set": {"enabled": enabled}},
            upsert=True
        )
        logger.info(f"FSUB status updated to: {enabled}")
        return True
    except Exception as e:
        logger.error(f"Error setting FSUB status: {e}")
        return False

async def get_fsub_status() -> bool:
    """Get current force subscribe status"""
    try:
        doc = await settings_col.find_one({"key": "fsub_status"})
        if doc:
            return doc.get("enabled", False)
        return False
    except Exception as e:
        logger.error(f"Error getting FSUB status: {e}")
        return False

# ----------------- User & Group Functions -----------------
async def add_user(user_id: int, name: str):
    """Add or update user in database"""
    try:
        if not isinstance(user_id, int) or user_id <= 0:
            logger.warning(f"Invalid user_id: {user_id}")
            return False

        await users_col.update_one(
            {"user_id": user_id},
            {"$set": {"name": name}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error adding user {user_id}: {e}")
        return False

async def get_all_users():
    """Get all user IDs"""
    try:
        return [doc["user_id"] async for doc in users_col.find({})]
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []

async def count_users():
    """Count total users"""
    try:
        return await users_col.count_documents({})
    except Exception as e:
        logger.error(f"Error counting users: {e}")
        return 0

async def add_group(chat_id: int, title: str):
    """Add or update group in database"""
    try:
        if not isinstance(chat_id, int):
            logger.warning(f"Invalid chat_id: {chat_id}")
            return False

        await groups_col.update_one(
            {"chat_id": chat_id},
            {"$set": {"title": title}},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error adding group {chat_id}: {e}")
        return False

async def get_all_groups():
    """Get all group chat IDs"""
    try:
        return [doc["chat_id"] async for doc in groups_col.find({})]
    except Exception as e:
        logger.error(f"Error getting all groups: {e}")
        return []

async def count_groups():
    """Count total groups"""
    try:
        return await groups_col.count_documents({})
    except Exception as e:
        logger.error(f"Error counting groups: {e}")
        return 0

# ----------------- Universal Save File (PDFs, Photos, Links) -----------------
async def save_file(file_id: str, file_name: str, file_size: int, caption: str, chat_id: int, message_id: int, media_type: str = "document"):
    """Save file metadata to database"""
    try:
        # Validate inputs
        if not isinstance(message_id, int) or message_id <= 0:
            logger.warning(f"Invalid message_id: {message_id}")
            return False

        if not isinstance(chat_id, int):
            logger.warning(f"Invalid chat_id: {chat_id}")
            return False

        # Sanitize inputs
        file_name = str(file_name)[:255] if file_name else "Unknown"
        caption = str(caption)[:4096] if caption else ""

        data = {
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "caption": caption,
            "chat_id": chat_id,
            "message_id": message_id,
            "media_type": media_type
        }
        await files_col.update_one(
            {"chat_id": chat_id, "message_id": message_id},
            {"$set": data},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"DB Save Error for message {message_id}: {e}")
        return False

# ----------------- 🔍 Smart Search Algorithm (Zero Missed Files) -----------------
async def search_files(query: str, limit: int = 6, skip: int = 0):
    clean_query = re.sub(r'[^\w\s]', ' ', query).strip()
    words = [w.strip() for w in clean_query.split() if len(w.strip()) > 1]
    
    if not words:
        words = [query.strip()]
        
    # 1. Strict Search (Saare words match karne ki koshish karega)
    regex_and = [
        {
            "$or": [
                {"file_name": {"$regex": re.escape(w), "$options": "i"}},
                {"caption": {"$regex": re.escape(w), "$options": "i"}}
            ]
        }
        for w in words
    ]
    filter_and = {"$and": regex_and} if regex_and else {}
    total_and = await files_col.count_documents(filter_and)
    
    if total_and > 0:
        cursor = files_col.find(filter_and).sort("message_id", -1).skip(skip).limit(limit)
        results = [doc async for doc in cursor]
        return results, total_and
    
    # 2. Smart Fallback 1: Filter filler words like 'sir', 'notes' and try strict AND on remaining words
    ignore_words = {"sir", "mam", "notes", "pdf", "book", "for", "by", "ka", "ki", "ke", "all"}
    primary_words = [w for w in words if len(w) >= 3 and w.lower() not in ignore_words]
    
    if primary_words and len(primary_words) < len(words):
        regex_and_primary = [
            {
                "$or": [
                    {"file_name": {"$regex": re.escape(w), "$options": "i"}},
                    {"caption": {"$regex": re.escape(w), "$options": "i"}}
                ]
            }
            for w in primary_words
        ]
        filter_and_primary = {"$and": regex_and_primary}
        total_primary = await files_col.count_documents(filter_and_primary)
        if total_primary > 0:
            cursor = files_col.find(filter_and_primary).sort("message_id", -1).skip(skip).limit(limit)
            results = [doc async for doc in cursor]
            return results, total_primary

    # 3. Smart Fallback 2: Agar abhi bhi koi result na ho, tab OR matching karein
    if not primary_words:
        primary_words = words
        
    regex_or = [
        {
            "$or": [
                {"file_name": {"$regex": re.escape(w), "$options": "i"}},
                {"caption": {"$regex": re.escape(w), "$options": "i"}}
            ]
        }
        for w in primary_words
    ]
    filter_or = {"$or": regex_or} if regex_or else {}
    total_or = await files_col.count_documents(filter_or)
    
    cursor = files_col.find(filter_or).sort("message_id", -1).skip(skip).limit(limit)
    results = [doc async for doc in cursor]
    return results, total_or

async def get_file_by_id(doc_id: str):
    """Get file by MongoDB document ID"""
    try:
        return await files_col.find_one({"_id": ObjectId(doc_id)})
    except Exception as e:
        logger.error(f"Error getting file by ID {doc_id}: {e}")
        return None

async def count_files():
    """Count total files in database"""
    try:
        return await files_col.count_documents({})
    except Exception as e:
        logger.error(f"Error counting files: {e}")
        return 0
