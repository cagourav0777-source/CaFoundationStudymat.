import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, InlineQuery, InlineQueryResultCachedDocument
)
from pyrogram.errors import UserNotParticipant, FloodWait
from config import API_ID, API_HASH, BOT_TOKEN, ADMINS, CHANNEL_ID, GROUP_ID, FSUB_CHATS
from database import (
    init_db, add_user, get_all_users, count_users, 
    save_file, search_files, count_files, set_fsub_status, get_fsub_status
)

app = Client("notes_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ----------------- Helper: Smart Button Title -----------------
def get_display_title(item):
    caption = item.get("caption", "").strip()
    file_name = item.get("file_name", "").strip()
    
    if caption:
        first_line = caption.split("\n")[0].strip()
        if len(first_line) > 2:
            title = first_line
        else:
            title = file_name or "Study Material"
    else:
        title = file_name or "Study Material"
    
    if len(title) > 38:
        return title[:38] + "..."
    return title

# ----------------- Force Subscribe Helpers (Dynamic ON/OFF) -----------------
async def check_fsub(client: Client, user_id: int):
    # Check if FSUB is currently enabled in settings
    is_fsub_active = await get_fsub_status()
    if not is_fsub_active:
        return []  # FSUB OFF hai, sabko allow karega
    
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

# ----------------- /start Command -----------------
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Student"
    await add_user(user_id, first_name)
    
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await message.reply_text(
            "⚠️ **Access Denied!**\n\nPlease join our official channels below to unlock full search access:",
            reply_markup=get_fsub_keyboard(unsubbed)
        )
    
    welcome_text = (
        f"👋 **Hello {first_name}, Welcome to CA Study Material Bot!** 📚\n\n"
        "Your fast & smart companion to find Notes, Question Banks, MTPs, RTPs, Chart Books & Revision Material instantly.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📖 **HOW TO USE THIS BOT:**\n\n"
        "1️⃣ **Type Your Query:**\n"
        "   Simply send the subject, faculty name, or book title in this chat.\n"
        "   • *Examples:* `Hardik Sir`, `MV Sir`, `Business Economics`, `MTP Sept 26`\n\n"
        "2️⃣ **Browse Interactive Results:**\n"
        "   The bot scans 900+ indexed files with crystal-clear subject titles on buttons.\n\n"
        "3️⃣ **Instant File Delivery:**\n"
        "   Tap any button and the bot will send the exact PDF file directly to your chat!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "❓ **CAN'T FIND WHAT YOU ARE LOOKING FOR?**\n"
        "If any specific note or question bank is missing, click below to request it directly in our discussion group!"
    )
    
    start_buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💬 Ask in Discussion Group", url="https://t.me/Caaspirants_26")
        ],
        [
            InlineKeyboardButton("📢 Main Channel", url="https://t.me/Future_ca_minds")
        ]
    ])
    
    await message.reply_text(welcome_text, reply_markup=start_buttons)

# /id Command
@app.on_message(filters.command("id"))
async def get_my_id(client: Client, message: Message):
    if message.chat.type == enums.ChatType.PRIVATE:
        await message.reply_text(f"👤 **Your Telegram User ID:** `{message.from_user.id}`")
    else:
        await message.reply_text(f"👥 **Group Chat ID:** `{message.chat.id}`")

# ----------------- Admin Commands: /startfsub & /stopfsub -----------------
@app.on_message(filters.command(["startfsub", "stopfsub", "fsub"]) & filters.private)
async def fsub_toggle_handler(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text("❌ Sirf Admin is setting ko change kar sakte hain.")
    
    cmd = message.command[0].lower()
    arg = message.command.lower() if len(message.command) > 1 else ""
    
    if cmd == "startfsub" or arg == "on":
        await set_fsub_status(True)
        await message.reply_text("✅ **Force Subscribe (FSUB) is now turned ON!**\n\nAb users ko bot use karne se pehle channels join karne padenge.")
    elif cmd == "stopfsub" or arg == "off":
        await set_fsub_status(False)
        await message.reply_text("🟢 **Force Subscribe (FSUB) is now turned OFF!**\n\nAb koi bhi user bina channel join kiye directly bot use kar sakta hai (Growth Mode Active 🚀).")
    else:
        status = await get_fsub_status()
        status_text = "🟢 **ON (Active)**" if status else "🔴 **OFF (Disabled - Free Access)**"
        await message.reply_text(
            f"⚙️ **Current FSUB Status:** {status_text}\n\n"
            "• Turn ON: `/startfsub` ya `/fsub on`\n"
            "• Turn OFF: `/stopfsub` ya `/fsub off`"
        )

# ----------------- Force Sub Verification Callback -----------------
@app.on_callback_query(filters.regex("^check_fsub_again$"))
async def fsub_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await query.answer("❌ You haven't joined all required channels yet!", show_alert=True)
    
    await query.message.delete()
    await query.message.reply_text("✅ **Access Granted!** You can now search for any notes or study material.")

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

# ----------------- Admin Command: /index -----------------
@app.on_message(filters.command("index") & filters.private)
async def index_channel_handler(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text(f"❌ You are not an Admin! Your ID: `{message.from_user.id}`")
    
    status_msg = await message.reply_text("⏳ **Indexing channel messages...**")
    
    try:
        temp = await client.send_message(CHANNEL_ID, "Indexing...")
        last_id = temp.id
        await temp.delete()
    except Exception as e:
        return await status_msg.edit_text(f"❌ **Channel Access Error:** `{str(e)}`")
    
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
            
            if count > 0 and count % 50 == 0:
                try:
                    await status_msg.edit_text(f"⏳ **Indexing in progress:** `{count}` files scanned...")
                except Exception:
                    pass
            await asyncio.sleep(0.3)
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Batch error: {e}")
            continue
            
    await status_msg.edit_text(f"✅ **Indexing Complete!**\nTotal **{count}** files are saved in the database.")

# ----------------- Admin Command: /stats -----------------
@app.on_message(filters.command("stats") & filters.private)
async def stats_handler(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text("❌ You are not an Admin.")
    
    u_count = await count_users()
    f_count = await count_files()
    fsub_status = await get_fsub_status()
    fsub_text = "🟢 Active" if fsub_status else "🔴 Inactive (Growth Mode)"
    
    await message.reply_text(
        "📊 **Bot Statistics:**\n\n"
        f"👥 **Total Users:** `{u_count}`\n"
        f"📁 **Total Indexed Files:** `{f_count}`\n"
        f"🔒 **Force Subscribe:** `{fsub_text}`"
    )

# ----------------- Admin Command: /broadcast -----------------
@app.on_message(filters.command("broadcast") & filters.private & filters.reply)
async def broadcast_handler(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text("❌ Only Admins can broadcast.")
    
    users = await get_all_users()
    success, failed = 0, 0
    status_msg = await message.reply_text(f"📢 Broadcasting to `{len(users)}` users...")
    
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

# ----------------- 1. DM Search Handler -----------------
@app.on_message(filters.text & filters.private & ~filters.command(["start", "index", "stats", "broadcast", "id", "startfsub", "stopfsub", "fsub"]))
async def dm_search_handler(client: Client, message: Message):
    user_id = message.from_user.id
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await message.reply_text(
            "⚠️ Please join our official channels to use the bot.",
            reply_markup=get_fsub_keyboard(unsubbed)
        )
    
    query_text = message.text.strip()
    if len(query_text) < 2:
        return await message.reply_text("❗ Please type at least 2 characters to search.")
    
    results, total = await search_files(query_text, limit=6, skip=0)
    if not results:
        not_found_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Ask in Discussion Group", url="https://t.me/Caaspirants_26")]
        ])
        return await message.reply_text(
            f"❌ **No material found for:** `{query_text}`\n\n"
            "• Please check the spelling or try broader keywords.\n"
            "• If it's missing, you can request it in our group:",
            reply_markup=not_found_buttons
        )
    
    buttons = []
    for item in results:
        display_name = get_display_title(item)
        buttons.append([InlineKeyboardButton(f"📄 {display_name}", callback_data=f"get_{item['message_id']}")])
    
    if total > 6:
        buttons.append([InlineKeyboardButton("Next Page ⏩", callback_data=f"page_1_{query_text}")])
    
    await message.reply_text(
        f"🔍 **Search Results for:** `{query_text}`\n📊 **Total Files Found:** `{total}`\n\nTap below to receive the file directly:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ----------------- 2. Group Search Handler -----------------
@app.on_message(filters.chat(GROUP_ID) & filters.text)
async def group_search_handler(client: Client, message: Message):
    text = message.text.strip()
    
    is_command = False
    if text.startswith("/search") or text.startswith("/notes") or text.startswith("/get"):
        is_command = True
        if " " not in text:
            return await message.reply_text("❗ Usage: `/search topic_name` (e.g. `/search hardik sir`)")
        cmd, query_text = text.split(" ", 1)
        query_text = query_text.strip()
        if len(query_text) < 2:
            return await message.reply_text("❗ Please type at least 2 characters.")
    else:
        if len(text) < 3 or text.lower() in ["hi", "hello", "gm", "gn", "ok", "thanks", "bye", "hlo"]:
            return
        query_text = text
    
    results, total = await search_files(query_text, limit=5, skip=0)
    
    if not results:
        if is_command:
            await message.reply_text(f"❌ No notes found for `{query_text}`.")
        return
    
    buttons = []
    for item in results:
        display_name = get_display_title(item)
        buttons.append([InlineKeyboardButton(f"📄 {display_name}", callback_data=f"get_{item['message_id']}")])
    
    if total > 5:
        buttons.append([InlineKeyboardButton("Next Page ⏩", callback_data=f"page_1_{query_text}")])
    
    await message.reply_text(
        f"📚 **Results for {message.from_user.mention}:** `{query_text}` (Total: {total})\nTap below to receive the file in your DM:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ----------------- Direct File Delivery Callback -----------------
@app.on_callback_query(filters.regex(r"^get_"))
async def send_file_callback(client: Client, query: CallbackQuery):
    try:
        prefix, msg_id_str = query.data.split("_", 1)
        msg_id = int(msg_id_str)
        
        await client.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=CHANNEL_ID,
            message_id=msg_id
        )
        await query.answer("✅ File sent to your chat!", show_alert=False)
    except Exception as e:
        print(f"Send File Error: {e}")
        await query.answer("❌ File send nahi ho saki! Pehle bot ke DM mein jakar /start karein.", show_alert=True)

# ----------------- Pagination Callback -----------------
@app.on_callback_query(filters.regex(r"^page_"))
async def pagination_callback(client: Client, query: CallbackQuery):
    try:
        prefix, page_str, query_text = query.data.split("_", 2)
        page = int(page_str)
        limit = 6
        skip = page * limit
        
        results, total = await search_files(query_text, limit=limit, skip=skip)
        if not results:
            return await query.answer("No more results available.", show_alert=True)
        
        buttons = []
        for item in results:
            display_name = get_display_title(item)
            buttons.append([InlineKeyboardButton(f"📄 {display_name}", callback_data=f"get_{item['message_id']}")])
        
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⏪ Prev", callback_data=f"page_{page - 1}_{query_text}"))
        if total > skip + limit:
            nav.append(InlineKeyboardButton("Next ⏩", callback_data=f"page_{page + 1}_{query_text}"))
        if nav:
            buttons.append(nav)
            
        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer()
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

# ----------------- Inline Search Mode -----------------
@app.on_inline_query()
async def inline_query_handler(client: Client, query: InlineQuery):
    text = query.query.strip()
    if not text:
        return
    
    results, _ = await search_files(text, limit=10)
    inline_results = []
    
    for item in results:
        display_name = get_display_title(item)
        if item.get("file_id"):
            inline_results.append(
                InlineQueryResultCachedDocument(
                    title=display_name,
                    file_id=item["file_id"],
                    caption=item.get("caption", "")
                )
            )
            
    await query.answer(inline_results, cache_time=5)

# ----------------- Main Execution -----------------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    print("🚀 Notes Search Bot Started Successfully!")
    app.run()
