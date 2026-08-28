import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, InlineQuery, InlineQueryResultCachedDocument, 
    InlineQueryResultArticle, InputTextMessageContent
)
from pyrogram.errors import UserNotParticipant, FloodWait
from config import API_ID, API_HASH, BOT_TOKEN, ADMINS, CHANNEL_ID, FSUB_CHATS
from database import (
    init_db, add_user, get_all_users, count_users, 
    save_file, search_files, get_file_by_id, count_files
)

app = Client("notes_search_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Helper: Check Force Subscribe
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
            # Agar bot admin nahi hai ya private chat access issue ho
            continue
    return unsubbed

def get_fsub_keyboard(unsubbed_list):
    buttons = []
    for item in unsubbed_list:
        link = f"https://t.me/{item['chat'].replace('@', '')}"
        buttons.append([InlineKeyboardButton(f"Join {item['name']}", url=link)])
    buttons.append([InlineKeyboardButton("🔄 Try Again / Refresh", callback_data="check_fsub_again")])
    return InlineKeyboardMarkup(buttons)

# Start Command
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    await add_user(user_id, message.from_user.first_name)
    
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await message.reply_text(
            "⚠️ **Access Denied!**\n\nBot ko use karne ke liye pehle hamare official channels aur group ko join karein:",
            reply_markup=get_fsub_keyboard(unsubbed)
        )
    
    await message.reply_text(
        f"👋 Namaste **{message.from_user.first_name}**!\n\n"
        "📚 Main Notes & Study Material Search Bot hoon.\n"
        "Aapko jo bhi notes ya question bank chahiye, bas uska **naam type karke send karein**!"
    )

# Force Sub Callback Refresh
@app.on_callback_query(filters.regex("^check_fsub_again$"))
async def fsub_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await query.answer("❌ Aapne abhi tak sabhi channels join nahi kiye hain!", show_alert=True)
    
    await query.message.delete()
    await query.message.reply_text(
        "✅ **Membership Verified!**\n\nAb aap kisi bhi material ka naam likhkar search kar sakte hain."
    )

# Real-Time Channel Post Listener (Auto-Save New Files)
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

# Search Handler (DM Queries)
@app.on_message(filters.text & filters.private & ~filters.command(["start", "index", "stats", "broadcast"]))
async def search_handler(client: Client, message: Message):
    user_id = message.from_user.id
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await message.reply_text(
            "⚠️ Bot ko access karne ke liye channels join karna zaroori hai.",
            reply_markup=get_fsub_keyboard(unsubbed)
        )
    
    query_text = message.text.strip()
    if len(query_text) < 2:
        return await message.reply_text("❗ Kripya kam se kam 2 akshar likhkar search karein.")
    
    results, total = await search_files(query_text, limit=6, skip=0)
    if not results:
        return await message.reply_text(
            f"❌ **'{query_text}'** ke related koi material nahi mila.\n"
            "Spelling check karein ya dusre keywords try karein."
        )
    
    buttons = []
    for item in results:
        name = item["file_name"][:40] + ("..." if len(item["file_name"]) > 40 else "")
        buttons.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"get_{str(item['_id'])}")])
    
    if total > 6:
        buttons.append([InlineKeyboardButton("Next Page ⏩", callback_data=f"page_1_{query_text}")])
    
    await message.reply_text(
        f"🔍 **Search Results for:** `{query_text}`\n📊 Total Files Found: **{total}**\n\nNiche click karke file prapt karein:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# File Delivery Callback Handler
@app.on_callback_query(filters.regex(r"^get_"))
async def send_file_callback(client: Client, query: CallbackQuery):
    doc_id = query.data.split("_")[1]
    file_info = await get_file_by_id(doc_id)
    
    if not file_info:
        return await query.answer("❌ File nahi mili ya delete ho chuki hai.", show_alert=True)
    
    try:
        await client.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=file_info["chat_id"],
            message_id=file_info["message_id"]
        )
        await query.answer("✅ File bhej di gayi hai!")
    except Exception as e:
        await query.answer("❌ File send karne mein dikkat aayi.", show_alert=True)
        print(f"Send error: {e}")

# Pagination Callback Handler
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
        name = item["file_name"][:40] + ("..." if len(item["file_name"]) > 40 else "")
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

# Admin Command: /index (Scan All Past Files from Channel)
@app.on_message(filters.command("index") & filters.user(ADMINS))
async def index_channel_handler(client: Client, message: Message):
    status_msg = await message.reply_text("⏳ **Channel indexing shuru ho rahi hai...**")
    count = 0
    
    try:
        async for msg in client.get_chat_history(CHANNEL_ID):
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
                if count % 20 == 0:
                    await status_msg.edit_text(f"⏳ **Indexing in progress:** `{count}` files indexed...")
                    await asyncio.sleep(1)
        
        await status_msg.edit_text(f"✅ **Indexing Complete!**\nTotal **{count}** files database mein save ho gayi hain.")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error while indexing: `{str(e)}`")

# Admin Command: /stats
@app.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats_handler(client: Client, message: Message):
    u_count = await count_users()
    f_count = await count_files()
    await message.reply_text(
        "📊 **Bot Statistics:**\n\n"
        f"👥 **Total Users:** `{u_count}`\n"
        f"📁 **Total Indexed Files:** `{f_count}`"
    )

# Admin Command: /broadcast
@app.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_handler(client: Client, message: Message):
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
        f"🟢 Successful: `{success}`\n"
        f"🔴 Failed: `{failed}`"
    )

# Inline Search Handler (@botname query)
@app.on_inline_query()
async def inline_query_handler(client: Client, query: InlineQuery):
    text = query.query.strip()
    if not text:
        return
    
    results, _ = await search_files(text, limit=15)
    inline_results = []
    
    for item in results:
        if item.get("file_id"):
            inline_results.append(
                InlineQueryResultCachedDocument(
                    title=item["file_name"],
                    file_id=item["file_id"],
                    caption=item.get("caption", "")
                )
            )
            
    await query.answer(inline_results, cache_time=5)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    print("🚀 Bot is starting...")
    app.run()
