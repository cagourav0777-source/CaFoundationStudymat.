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
    save_file, search_files, count_files
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

# ----------------- /start Command -----------------
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Student"
    await add_user(user_id, first_name)
    
    # Check Force Subscribe
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await message.reply_text(
            "⚠️ **Access Denied!**\n\nPlease join our official channels below to unlock full search access:",
            reply_markup=get_fsub_keyboard(unsubbed)
        )
    
    # Agar user direct file deep-link se aaya hai
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
            print(f"Deep link send error: {e}")
    
    welcome_text = (
        f"👋 **Hello {first_name}, Welcome to CA Study Material Bot!** 📚\n\n"
        "Your fast & smart companion to find Notes, Question Banks, MTPs, RTPs, Chart Books & Revision Material instantly.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📖 **HOW TO USE THIS BOT:**\n\n"
        "1️⃣ **Type Your Query:**\n"
        "   Simply send the subject, faculty name, or book title in this chat.\n"
        "   • *Examples:* `Hardik Sir`, `MV Sir`, `Business Economics`, `Law Question Bank`\n\n"
        "2️⃣ **Browse Interactive Results:**\n"
        "   The bot scans 900+ indexed files and presents matching options with buttons.\n\n"
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
    await message.reply_text(
        "📊 **Bot Statistics:**\n\n"
        f"👥 **Total Users:** `{u_count}`\n"
        f"📁 **Total Indexed Files:** `{f_count}`"
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

# ----------------- 1. DM Search Handler (Direct Delivery Buttons) -----------------
@app.on_message(filters.text & filters.private & ~filters.command(["start", "index", "stats", "broadcast", "id"]))
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
        name = item["file_name"][:38] + ("..." if len(item["file_name"]) > 38 else "")
        # callback_data jo direct file bhejega
        buttons.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"get_{item['message_id']}")])
    
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
        name = item["file_name"][:35] + ("..." if len(item["file_name"]) > 35 else "")
        buttons.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"get_{item['message_id']}")])
    
    if total > 5:
        buttons.append([InlineKeyboardButton("Next Page ⏩", callback_data=f"page_1_{query_text}")])
    
    await message.reply_text(
        f"📚 **Results for {message.from_user.mention}:** `{query_text}` (Total: {total})\nTap below to receive the file in your DM:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ----------------- 🚀 Direct File Send Callback (100% Reliable Unpacking) -----------------
@app.on_callback_query(filters.regex(r"^get_"))
async def send_file_callback(client: Client, query: CallbackQuery):
    try:
        prefix, msg_id_str = query.data.split("_", 1)
        msg_id = int(msg_id_str)
        
        # User ke DM mein direct channel se file copy karega
        await client.copy_message(
            chat_id=query.from_user.id,
            from_chat_id=CHANNEL_ID,
            message_id=msg_id
        )
        await query.answer("✅ File aapke private chat (DM) mein bhej di gayi hai!", show_alert=False)
    except Exception as e:
        print(f"Send File Error: {e}")
        # Agar user ne pehle bot ko start nahi kiya hai DM mein
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
            name = item["file_name"][:38] + ("..." if len(item["file_name"]) > 38 else "")
            buttons.append([InlineKeyboardButton(f"📄 {name}", callback_data=f"get_{item['message_id']}")])
        
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
        if item.get("file_id"):
            inline_results.append(
                InlineQueryResultCachedDocument(
                    title=item["file_name"],
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
