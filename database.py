import re
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

files_col = db["files"]
users_col = db["users"]
groups_col = db["groups"]
settings_col = db["settings"]

async def init_db():
    await files_col.create_index([("file_name", "text"), ("caption", "text")])
    await files_col.create_index([("chat_id", 1), ("message_id", 1)], unique=True)
    await users_col.create_index("user_id", unique=True)
    await groups_col.create_index("chat_id", unique=True)

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

# ----------------- User Functions -----------------
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

# ----------------- Group Functions -----------------
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
        print(f"DB Save Error: {e}")
        return False

async def search_files(query: str, limit: int = 6, skip: int = 0):
    clean_query = re.sub(r'[^\w\s]', ' ', query)
    words = [w.strip() for w in clean_query.split() if len(w.strip()) > 1]
    
    if not words:
        words = [query.strip()]
        
    regex_queries = [
        {
            "$or": [
                {"file_name": {"$regex": re.escape(w), "$options": "i"}},
                {"caption": {"$regex": re.escape(w), "$options": "i"}}
            ]
        }
        for w in words
    ]
    
    filter_query = {"$and": regex_queries} if regex_queries else {}
    
    total = await files_col.count_documents(filter_query)
    cursor = files_col.find(filter_query).skip(skip).limit(limit)
    results = [doc async for doc in cursor]
    return results, total

async def get_file_by_id(doc_id: str):
    try:
        return await files_col.find_one({"_id": ObjectId(doc_id)})
    except Exception:
        return None

async def count_files():
    return await files_col.count_documents({})
