import asyncio
import re
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, InlineQuery, InlineQueryResultCachedDocument
)
from pyrogram.errors import UserNotParticipant, FloodWait
from config import API_ID, API_HASH, BOT_TOKEN, ADMINS, CHANNEL_ID, FSUB_CHATS
from database import (
    init_db, add_user, get_all_users, count_users, 
    add_group, count_groups, save_file, search_files, 
    count_files, set_fsub_status, get_fsub_status
)

app = Client("notes_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ----------------- Helper: Message Extractor -----------------
def extract_message_data(msg: Message):
    file_id = ""
    file_name = ""
    file_size = 0
    caption = msg.caption or ""
    media_type = "document"
    
    if msg.document:
        file_id = msg.document.file_id
        file_name = msg.document.file_name or caption or f"Document_{msg.id}.pdf"
        file_size = msg.document.file_size
        media_type = "document"
    elif msg.photo:
        file_id = msg.photo.file_id
        file_size = msg.photo.file_size
        media_type = "photo"
        if caption:
            file_name = caption.split("\n")[0].strip()[:60]
        else:
            file_name = f"Photo_Note_{msg.id}.jpg"
    elif msg.video:
        file_id = msg.video.file_id
        file_name = msg.video.file_name or caption or f"Video_{msg.id}"
        file_size = msg.video.file_size
        media_type = "video"
    elif msg.audio:
        file_id = msg.audio.file_id
        file_name = msg.audio.file_name or caption or f"Audio_{msg.id}"
        file_size = msg.audio.file_size
        media_type = "audio"
    elif msg.text:
        text_content = msg.text.strip()
        if len(text_content) < 4 or text_content.startswith("/"):
            return None
        file_name = text_content.split("\n")[0].strip()[:60]
        caption = text_content
        media_type = "text"
    else:
        return None
        
    return {
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "caption": caption,
        "media_type": media_type,
        "chat_id": msg.chat.id,
        "message_id": msg.id
    }

# ----------------- Helper: Smart Button Title -----------------
def get_display_title(item):
    caption = item.get("caption", "").strip()
    file_name = item.get("file_name", "").strip()
    media_type = item.get("media_type", "")
    
    if caption:
        first_line = caption.split("\n")[0].strip()
        title = first_line if len(first_line) > 2 else (file_name or "Study Material")
    else:
        title = file_name or "Study Material"
        
    if "http://" in caption or "https://" in caption or "drive.google.com" in caption:
        icon = "🔗"
    elif media_type == "photo" or file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
        icon = "🖼"
    elif media_type == "video":
        icon = "🎥"
    elif media_type == "audio":
        icon = "🎵"
    else:
        icon = "📄"
        
    if len(title) > 36:
        return f"{icon} {title[:36]}..."
    return f"{icon} {title}"

# ----------------- Force Subscribe Helpers -----------------
async def check_fsub(client: Client, user_id: int):
    is_fsub_active = await get_fsub_status()
    if not is_fsub_active:
        return []
    
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

# ----------------- 🌟 /start Command & Deep-Link Delivery -----------------
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Aspirant"
    await add_user(user_id, first_name)
    
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await message.reply_text(
            "⚠️ **Access Denied!**\n\nPlease join our official channels below to unlock search access:",
            reply_markup=get_fsub_keyboard(unsubbed)
        )
    
    # Deep Link Handler: Group click se jab user yahan aayega to file deliver hogi
    if len(message.command) > 1 and message.command.startswith("get_"):
        try:
            prefix, msg_id_str = message.command.split("_", 1)
            msg_id = int(msg_id_str)
            await client.copy_message(
                chat_id=user_id,
                from_chat_id=CHANNEL_ID,
                message_id=msg_id
            )
            return
        except Exception as e:
            print(f"Deep link error: {e}")
            return await message.reply_text(f"❌ Error delivering file: {str(e)}")
    
    welcome_text = (
        f"✨ **𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐓𝐎 𝐂𝐀 𝐍𝐎𝐓𝐄𝐒 𝐌𝐀𝐒𝐓𝐄𝐑** ✨\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 Hello **{first_name}**, your personal automated search engine for **CA Foundation & Inter** study resources.\n\n"
        f"⚡ Find **Notes, Question Banks, MTPs, RTPs, Chart Books & Google Drive Links** in seconds!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 **𝐇𝐎𝐖 𝐓𝐎 𝐒𝐄𝐀𝐑𝐂𝐇:**\n\n"
        f"1️⃣ **Send Any Keyword:**\n"
        f"   Just type what you need directly in this chat:\n"
        f"   • *Faculty:* `Hardik Sir`, `MV Sir`, `Shubham Singhal`\n"
        f"   • *Subjects:* `Business Economics`, `Law`, `Accounts`, `QA`\n"
        f"   • *Material:* `Question Bank`, `MTP Sept 26`, `Drive Links`\n\n"
        f"2️⃣ **Smart Results:**\n"
        f"   The bot scans all files, photos & Drive folders with clear titles.\n\n"
        f"3️⃣ **Instant File Delivery:**\n"
        f"   Tap any button and get the exact PDF, photo, or drive link instantly in this chat!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Pro Tip: Add this bot to any study group to search notes directly with your friends!*"
    )
    
    await message.reply_text(welcome_text)

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
        return await message.reply_text("❌ Only Admins can change this setting.")
    
    cmd = message.command[0].lower()
    arg = message.command.lower() if len(message.command) > 1 else ""
    
    if cmd == "startfsub" or arg == "on":
        await set_fsub_status(True)
        await message.reply_text("✅ **Force Subscribe (FSUB) is now turned ON!**\n\nUsers must join channels to use the bot.")
    elif cmd == "stopfsub" or arg == "off":
        await set_fsub_status(False)
        await message.reply_text("🟢 **Force Subscribe (FSUB) is now turned OFF!**\n\nGrowth Mode Active: All users have free instant access.")
    else:
        status = await get_fsub_status()
        status_text = "🟢 **ON (Active)**" if status else "🔴 **OFF (Disabled - Free Access)**"
        await message.reply_text(
            f"⚙️ **Current FSUB Status:** {status_text}\n\n"
            "• Turn ON: `/startfsub` or `/fsub on`\n"
            "• Turn OFF: `/stopfsub` or `/fsub off`"
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
@app.on_message(filters.chat(CHANNEL_ID))
async def channel_post_listener(client: Client, message: Message):
    data = extract_message_data(message)
    if not data:
        return
    
    await save_file(
        file_id=data["file_id"],
        file_name=data["file_name"],
        file_size=data["file_size"],
        caption=data["caption"],
        chat_id=data["chat_id"],
        message_id=data["message_id"],
        media_type=data["media_type"]
    )

# ----------------- Admin Command: /index -----------------
@app.on_message(filters.command("index") & filters.private)
async def index_channel_handler(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text(f"❌ You are not an Admin! Your ID: `{message.from_user.id}`")
    
    status_msg = await message.reply_text("⏳ **Indexing channel (PDFs, Photos & Drive Links)...**")
    
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
                
                data = extract_message_data(msg)
                if not data:
                    continue
                
                await save_file(
                    file_id=data["file_id"],
                    file_name=data["file_name"],
                    file_size=data["file_size"],
                    caption=data["caption"],
                    chat_id=data["chat_id"],
                    message_id=data["message_id"],
                    media_type=data["media_type"]
                )
                count += 1
            
            if count > 0 and count % 50 == 0:
                try:
                    await status_msg.edit_text(f"⏳ **Indexing in progress:** `{count}` items saved...")
                except Exception:
                    pass
            await asyncio.sleep(0.3)
            
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            print(f"Batch error: {e}")
            continue
            
    await status_msg.edit_text(f"✅ **Indexing Complete!**\nTotal **{count}** materials are saved in the database.")

# ----------------- Admin Command: /stats (Tracks Groups Too) -----------------
@app.on_message(filters.command("stats") & filters.private)
async def stats_handler(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text("❌ You are not an Admin.")
    
    u_count = await count_users()
    g_count = await count_groups()
    f_count = await count_files()
    fsub_status = await get_fsub_status()
    fsub_text = "🟢 Active" if fsub_status else "🔴 Inactive (Growth Mode)"
    
    await message.reply_text(
        "📊 **Bot Global Statistics:**\n\n"
        f"👥 **Total Users (DM):** `{u_count}`\n"
        f"💬 **Connected Groups:** `{g_count}`\n"
        f"📁 **Total Indexed Materials:** `{f_count}`\n"
        f"🔒 **Force Subscribe:** `{fsub_text}`"
    )

# ----------------- Admin Command: /broadcast -----------------
@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text("❌ Only Admins can broadcast.")
    
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text(
            "❗ **Broadcast Kaise Karein:**\n\n"
            "1️⃣ Kisi bhi message ko **Reply** karke `/broadcast` likhein.\n"
            "2️⃣ YA direct likhein: `/broadcast Aapka message`"
        )
    
    users = await get_all_users()
    if not users:
        return await message.reply_text("❌ Database mein koi users nahi hain.")
    
    status_msg = await message.reply_text(f"📢 **Broadcast shuru:** `{len(users)}` users...")
    success, failed = 0, 0
    
    for u_id in users:
        try:
            if message.reply_to_message:
                await message.reply_to_message.copy(chat_id=u_id)
            else:
                broadcast_text = message.text.split(" ", 1)
                await client.send_message(chat_id=u_id, text=broadcast_text)
            success += 1
            await asyncio.sleep(0.04)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception:
            failed += 1
            
    await status_msg.edit_text(
        f"✅ **Broadcast Completed!**\n\n"
        f"🟢 **Delivered:** `{success}`\n"
        f"🔴 **Failed / Blocked:** `{failed}`\n"
        f"👥 **Total Targeted:** `{len(users)}`"
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
        return await message.reply_text(
            f"❌ **No material found for:** `{query_text}`\n\n"
            "• Please check the spelling or try broader keywords (e.g. `Hardik sir`, `Economics`)."
        )
    
    buttons = []
    for item in results:
        display_name = get_display_title(item)
        buttons.append([InlineKeyboardButton(display_name, callback_data=f"get_{item['message_id']}")])
    
    if total > 6:
        buttons.append([InlineKeyboardButton("Next Page ⏩", callback_data=f"page_1_{query_text}")])
    
    await message.reply_text(
        f"🔍 **Search Results for:** `{query_text}`\n📊 **Total Found:** `{total}`\n\nTap below to receive the material directly:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ----------------- 2. 🌍 Universal Group Search Handler (Har Group Mein Kaam Karega) -----------------
@app.on_message(filters.group & filters.text)
async def group_search_handler(client: Client, message: Message):
    # Track the group in database
    await add_group(message.chat.id, message.chat.title or "Group")
    
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
        # Ignore common chat words
        if len(text) < 3 or text.lower() in ["hi", "hello", "gm", "gn", "ok", "thanks", "bye", "hlo", "yes", "no"]:
            return
        query_text = text
    
    results, total = await search_files(query_text, limit=5, skip=0)
    
    if not results:
        if is_command:
            await message.reply_text(f"❌ No notes found for `{query_text}`.")
        return
    
    bot_username = (await client.get_me()).username
    buttons = []
    for item in results:
        display_name = get_display_title(item)
        # Deep Link: User click karega to bot ke DM me file deliver hogi
        deep_link = f"https://t.me/{bot_username}?start=get_{item['message_id']}"
        buttons.append([InlineKeyboardButton(display_name, url=deep_link)])
    
    await message.reply_text(
        f"📚 **Results for {message.from_user.mention}:** `{query_text}` (Total: {total})\nTap any button below to get the file in your DM:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ----------------- Direct File Delivery Callback (DM Only) -----------------
@app.on_callback_query(filters.regex(r"^get_"))
async def send_file_callback(client: Client, query: CallbackQuery):
    try:
        prefix, msg_id_str = query.data.split("_", 1)
        msg_id = int(msg_id_str)
        
        await client.copy_message(
            chat_id=query.message.chat.id,
            from_chat_id=CHANNEL_ID,
            message_id=msg_id
        )
        await query.answer("✅ Sent!", show_alert=False)
    except Exception as e:
        err_str = str(e)
        print(f"Send Error: {err_str}")
        await query.answer(f"❌ Error: {err_str[:60]}", show_alert=True)

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
            buttons.append([InlineKeyboardButton(display_name, callback_data=f"get_{item['message_id']}")])
        
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
