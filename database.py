import re
import logging
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

# Configure logging
logger = logging.getLogger(__name__)

# Create MongoDB client with connection pooling
client = AsyncIOMotorClient(
    MONGO_URI,
    maxPoolSize=10,
    minPoolSize=2,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000
)

db = client[DB_NAME]

files_col = db["files"]
users_col = db["users"]
groups_col = db["groups"]
settings_col = db["settings"]

async def init_db():
    try:
        # Test connection
        await client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB")
        
        # Create indexes
        await files_col.create_index([("file_name", "text"), ("caption", "text")])
        await files_col.create_index([("chat_id", 1), ("message_id", 1)], unique=True)
        await users_col.create_index("user_id", unique=True)
        await groups_col.create_index("chat_id", unique=True)
        
        logger.info("✅ Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"❌ MongoDB connection error: {e}")
        logger.error("Please check your MONGO_URI in environment variables")
        raise

# ----------------- Settings (FSUB Toggle) -----------------
async def set_fsub_status(enabled: bool):
    await settings_col.update_one(
        {"key": "fsub_status"},
        {"$set": {"enabled": enabled}},
        upsert=True
    )

async def get_fsub_status() -> bool:
    doc = await settings_col.find_one({"key": "fsub_status"})
    if doc:
        return doc.get("enabled", False)
    return False

# ----------------- User & Group Functions -----------------
async def add_user(user_id: int, name: str):
    try:
        await users_col.update_one(
            {"user_id": user_id},
            {"$set": {"name": name}},
            upsert=True
        )
    except Exception:
        pass

async def get_all_users():
    return [doc["user_id"] async for doc in users_col.find({})]

async def count_users():
    return await users_col.count_documents({})

async def add_group(chat_id: int, title: str):
    try:
        await groups_col.update_one(
            {"chat_id": chat_id},
            {"$set": {"title": title}},
            upsert=True
        )
    except Exception:
        pass

async def get_all_groups():
    return [doc["chat_id"] async for doc in groups_col.find({})]

async def count_groups():
    return await groups_col.count_documents({})

# ----------------- Universal Save File (PDFs, Photos, Links) -----------------
async def save_file(file_id: str, file_name: str, file_size: int, caption: str, chat_id: int, message_id: int, media_type: str = "document"):
    try:
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
        logger.error(f"DB Save Error: {e}")
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
    
    # 2. Smart Fallback (Agar 'sir' ya 'notes' ki wajah se file miss ho rahi ho, to main keyword se search karega)
    ignore_words = {"sir", "mam", "notes", "pdf", "book", "for", "by", "ka", "ki", "ke", "all"}
    primary_words = [w for w in words if len(w) >= 3 and w.lower() not in ignore_words]
    
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
    try:
        return await files_col.find_one({"_id": ObjectId(doc_id)})
    except Exception:
        return None

async def count_files():
    return await files_col.count_documents({})
