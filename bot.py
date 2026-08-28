import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, InlineQuery, InlineQueryResultCachedDocument
)
from pyrogram.errors import UserNotParticipant, FloodWait
from config import API_ID, API_HASH, BOT_TOKEN, ADMINS, CHANNEL_ID, FSUB_CHATS
from database import (
    init_db, add_user, get_all_users, count_users, 
    save_file, search_files, get_file_by_id, count_files
)

app = Client("notes_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ----------------- Force Subscribe Helpers -----------------
async def check_fsub(client: Client, user_id: int):
    unsubbed = []
    for item in FSUB_CHATS:
        chat = item["chat"]
        try:
            member = await client.get_chat_member(chat, user_id)
            if member.status in [enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT]:
                unsubbed.append(item)
        except UserNotParticipant:
            unsubbed.append(item)
        except Exception:
            continue
    return unsubbed

def get_fsub_keyboard(unsubbed_list):
    buttons = []
    for item in unsubbed_list:
        link = f"https://t.me/{item['chat'].replace('@', '')}"
        buttons.append([InlineKeyboardButton(f"Join {item['name']}", url=link)])
    buttons.append([InlineKeyboardButton("🔄 Verify / Try Again", callback_data="check_fsub_again")])
    return InlineKeyboardMarkup(buttons)

# ----------------- Basic Commands -----------------
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    await add_user(user_id, message.from_user.first_name)
    
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await message.reply_text(
            "⚠️ **Access Denied!**\n\nBot ko use karne ke liye pehle hamare official channels ko join karein:",
            reply_markup=get_fsub_keyboard(unsubbed)
        )
    
    await message.reply_text(
        f"👋 Namaste **{message.from_user.first_name}**!\n\n"
        "📚 Main is Channel ka Official Notes Search Bot hoon.\n\n"
        "🔍 **Notes Kaise Payein:**\n"
        "Bas kisi bhi subject, teacher ya chapter ka naam likhkar send karein (e.g. `Hardik sir`, `Business Economics`)."
    )

@app.on_message(filters.command("id") & filters.private)
async def get_my_id(client: Client, message: Message):
    await message.reply_text(f"👤 **Aapki Telegram User ID:** `{message.from_user.id}`")

# ----------------- Force Sub Verification Callback -----------------
@app.on_callback_query(filters.regex("^check_fsub_again$"))
async def fsub_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await query.answer("❌ Aapne abhi tak dono channels join nahi kiye hain!", show_alert=True)
    
    await query.message.delete()
    await query.message.reply_text("✅ **Access Granted!** Ab aap koi bhi material search kar sakte hain.")

# ----------------- Real-Time Channel Auto-Indexer -----------------
@app.on_message(filters.chat(CHANNEL_ID) & (filters.document | filters.audio | filters.video | filters.photo))
async def channel_post_listener(client: Client, message: Message):
    file = message.document or message.audio or message.video or (message.photo and message.photo.file_id)
    if not file:
        return
    
    file_name = getattr(file, "file_name", None) or message.caption or f"File_{message.id}"
    file_id = getattr(file, "file_id", "")
    file_size = getattr(file, "file_size", 0)
    caption = message.caption or ""
    
    await save_file(
        file_id=file_id,
        file_name=file_name,
        file_size=file_size,
        caption=caption,
        chat_id=message.chat.id,
        message_id=message.id
    )

# ----------------- Admin Command: /index (Batch Method) -----------------
@app.on_message(filters.command("index") & filters.private)
async def index_channel_handler(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text(
            f"❌ **Aap Admin nahi hain!**\n\n"
            f"Aapki User ID: `{message.from_user.id}`\n"
            f"Isko `config.py` mein `ADMINS` list mein add karein."
        )
    
    status_msg = await message.reply_text("⏳ **Aapke channel ki indexing shuru ho rahi hai...**")
    
    try:
        temp = await client.send_message(CHANNEL_ID, "Indexing...")
        last_id = temp.id
        await temp.delete()
    except Exception as e:
        return await status_msg.edit_text(
            f"❌ **Channel Access Error:** `{str(e)}`\n\n"
            "Check karein ki bot channel mein Administrator hai aur messages post karne ki permission on hai."
        )
    
    count = 0
    batch_size = 200
    
    for i in range(last_id, 0, -batch_size):
        batch_ids = list(range(i, max(0, i - batch_size), -1))
        try:
            messages = await client.get_messages(CHANNEL_ID, batch_ids)
            for msg in messages:
                if not msg or msg.empty:
                    continue
                
                file = msg.document or msg.audio or msg.video or (msg.photo and msg.photo.file_id)
                if file:
                    file_name = getattr(file, "file_name", None) or msg.caption or f"File_{msg.id}"
                    file_id = getattr(file, "file_id", "")
                    file_size = getattr(file, "file_size", 0)
                    caption = msg.caption or ""
                    
                    await save_file(
                        file_id=file_id,
                        file_name=file_name,
                        file_size=file_size,
                        caption=caption,
                        chat_id=msg.chat.id,
                        message_id=msg.id
                    )
                    count += 1
            
            if count > 0 and count % 20 == 0:
                await status_msg.edit_text(f"⏳ **Indexing in progress:** `{count}` files index ho chuki hain...")
            await asyncio.sleep(0.3)
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Batch fetch error: {e}")
            continue
            
    await status_msg.edit_text(f"✅ **Indexing Complete!**\nTotal **{count}** files database mein successfully index ho gayi hain.")

# ----------------- Admin Command: /stats -----------------
@app.on_message(filters.command("stats") & filters.private)
async def stats_handler(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text(
            f"❌ **Aap Admin nahi hain!**\n"
            f"Aapki User ID: `{message.from_user.id}`\n"
            f"Isko `config.py` mein `ADMINS` list mein add karein."
        )
    
    u_count = await count_users()
    f_count = await count_files()
    await message.reply_text(
        "📊 **Bot Statistics:**\n\n"
        f"👥 **Total Users:** `{u_count}`\n"
        f"📁 **Total Indexed Files:** `{f_count}`"
    )

# ----------------- Admin Command: /broadcast -----------------
@app.on_message(filters.command("broadcast") & filters.private & filters.reply)
async def broadcast_handler(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text("❌ Sirf Admins broadcast kar sakte hain.")
    
    users = await get_all_users()
    success, failed = 0, 0
    status_msg = await message.reply_text(f"📢 Broadcast shuru: `{len(users)}` users...")
    
    for u_id in users:
        try:
            await message.reply_to_message.copy(chat_id=u_id)
            success += 1
            await asyncio.sleep(0.05)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            failed += 1
            
    await status_msg.edit_text(
        f"✅ **Broadcast Completed!**\n\n"
        f"🟢 Sent: `{success}`\n"
        f"🔴 Failed: `{failed}`"
    )

# ----------------- DM Search System -----------------
@app.on_message(filters.text & filters.private & ~filters.command(["start", "index", "stats", "broadcast", "id"]))
async def search_handler(client: Client, message: Message):
    user_id = message.from_user.id
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await message.reply_text(
            "⚠️ Bot ko access karne ke liye pehle channel join karein.",
            reply_markup=get_fsub_keyboard(unsubbed)
        )
    
    query_text = message.text.strip()
    if len(query_text) < 2:
        return await message.reply_text("❗ Kripya kam se kam 2 akshar likhein.")
    
    results, total = await search_files(query_text, limit=6, skip=0)
    if not results:
        return await message.reply_text(
            f"❌ **'{query_text}'** ke related koi material nahi mila.\n"
            "Spelling check karein ya dusre keywords try karein."
        )
    
    buttons = []
    for item in results:
        name = item["file_name"][:38] + ("..." if len(item["file_name"]) > 38 else "")
        buttons.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"get_{str(item['_id'])}")])
    
    if total > 6:
        buttons.append([InlineKeyboardButton("Next Page ⏩", callback_data=f"page_1_{query_text}")])
    
    await message.reply_text(
        f"🔍 **Search Results for:** `{query_text}`\n📊 Total Files: **{total}**\n\nNiche click karke file prapt karein:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ----------------- Callback Handlers (File Delivery & Pagination) -----------------
@app.on_callback_query(filters.regex(r"^get_"))
async def send_file_callback(client: Client, query: CallbackQuery):
    doc_id = query.data.split("_", 1)
    file_info = await get_file_by_id(doc_id)
    
    if not file_info:
        return await query.answer("❌ File nahi mili ya delete ho chuki hai.", show_alert=True)
    
    try:
        await client.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=file_info["chat_id"],
            message_id=file_info["message_id"]
        )
        await query.answer("✅ File send ho gayi!")
    except Exception as e:
        await query.answer("❌ File send karne mein dikkat aayi.", show_alert=True)
        print(f"Send Error: {e}")

@app.on_callback_query(filters.regex(r"^page_"))
async def pagination_callback(client: Client, query: CallbackQuery):
    _, page_str, query_text = query.data.split("_", 2)
    page = int(page_str)
    limit = 6
    skip = page * limit
    
    results, total = await search_files(query_text, limit=limit, skip=skip)
    if not results:
        return await query.answer("Aur results nahi hain.", show_alert=True)
    
    buttons = []
    for item in results:
        name = item["file_name"][:38] + ("..." if len(item["file_name"]) > 38 else "")
        buttons.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"get_{str(item['_id'])}")])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⏪ Prev", callback_data=f"page_{page - 1}_{query_text}"))
    if total > skip + limit:
        nav.append(InlineKeyboardButton("Next ⏩", callback_data=f"page_{page + 1}_{query_text}"))
    if nav:
        buttons.append(nav)
        
    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
    await query.answer()

# ----------------- Main Execution -----------------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    print("🚀 Notes Search Bot Started Successfully!")
    app.run()
