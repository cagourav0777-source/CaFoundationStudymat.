import re
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]

files_col = db["files"]
users_col = db["users"]

# Unique index ensure karna taaki duplicate files save na hon
async def init_db():
    await files_col.create_index([("file_name", "text"), ("caption", "text")])
    await files_col.create_index([("chat_id", 1), ("message_id", 1)], unique=True)
    await users_col.create_index("user_id", unique=True)

# User Database Functions
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
    cursor = users_col.find({})
    return [doc["user_id"] async for doc in cursor]

async def count_users():
    return await users_col.count_documents({})

# File Database Functions
async def save_file(file_id: str, file_name: str, file_size: int, caption: str, chat_id: int, message_id: int):
    try:
        data = {
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "caption": caption,
            "chat_id": chat_id,
            "message_id": message_id
        }
        await files_col.update_one(
            {"chat_id": chat_id, "message_id": message_id},
            {"$set": data},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False

async def search_files(query: str, limit: int = 10, skip: int = 0):
    words = query.strip().split()
    # Case-insensitive matching for each word
    regex_queries = [{"file_name": {"$regex": re.escape(w), "$options": "i"}} for w in words]
    filter_query = {"$and": regex_queries} if regex_queries else {}
    
    total = await files_col.count_documents(filter_query)
    cursor = files_col.find(filter_query).skip(skip).limit(limit)
    results = [doc async for doc in cursor]
    return results, total

async def get_file_by_id(doc_id: str):
    from bson.objectid import ObjectId
    try:
        return await files_col.find_one({"_id": ObjectId(doc_id)})
    except Exception:
        return None

async def count_files():
    return await files_col.count_documents({})
