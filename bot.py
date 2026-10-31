import asyncio
import re
import logging
import sys
import os
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, InlineQuery, InlineQueryResultCachedDocument, ChatMemberUpdated
)
from pyrogram.errors import UserNotParticipant, FloodWait
from dotenv import load_dotenv
from flask import Flask
import threading

# Load environment variables from .env file
load_dotenv()

from config import (
    API_ID, API_HASH, BOT_TOKEN, ADMINS, CHANNEL_ID, FSUB_CHATS,
    SEARCH_RESULTS_LIMIT, PAGINATION_LIMIT, BROADCAST_SLEEP,
    INDEXING_BATCH_SIZE, INDEXING_SLEEP
)
from database import (
    init_db, add_user, get_all_users, count_users,
    add_group, get_all_groups, count_groups, save_file,
    search_files, count_files, set_fsub_status, get_fsub_status,
    get_groups_details, remove_group # <--- remove_group added
)
)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Client("notes_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Cached Bot Username to avoid repeated API calls
BOT_USERNAME = None

async def get_bot_username(client: Client) -> str:
    global BOT_USERNAME
    if not BOT_USERNAME:
        me = client.me or await client.get_me()
        BOT_USERNAME = me.username
    return BOT_USERNAME

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
        
    if media_type == "photo" or file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
        icon = "🖼"
    elif media_type == "video":
        icon = "🎥"
    elif media_type == "audio":
        icon = "🎵"
    elif media_type == "document" or file_name.lower().endswith(('.pdf', '.doc', '.docx', '.zip', '.rar')):
        icon = "📄"
    elif "http://" in caption or "https://" in caption or "drive.google.com" in caption:
        icon = "🔗"
    else:
        icon = "📄"
        
    if len(title) > 36:
        return f"{icon} {title[:36]}..."
    return f"{icon} {title}"

# ----------------- Force Subscribe Helpers -----------------
def format_fsub_url(val) -> str:
    val = str(val).strip()
    if val.startswith("http://") or val.startswith("https://"):
        return val
    if val.startswith("@"):
        return f"https://t.me/{val[1:]}"
    return f"https://t.me/{val}"

async def check_fsub(client: Client, user_id: int):
    is_fsub_active = await get_fsub_status()
    if not is_fsub_active:
        return []
    
    unsubbed = []
    for item in FSUB_CHATS:
        chat_target = item.get("chat_id") or item.get("chat")
        if not chat_target:
            continue
            
        try:
            member = await client.get_chat_member(chat_target, user_id)
            if member.status in [enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT]:
                unsubbed.append(item)
        except UserNotParticipant:
            unsubbed.append(item)
        except Exception as e:
            logger.warning(f"FSUB check failed for {item.get('name')} ({chat_target}): {e}")
            fallback = item.get("link") or item.get("chat")
            if fallback and str(fallback) != str(chat_target) and not str(fallback).startswith("-100"):
                try:
                    member = await client.get_chat_member(fallback, user_id)
                    if member.status in [enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT]:
                        unsubbed.append(item)
                    continue
                except UserNotParticipant:
                    unsubbed.append(item)
                    continue
                except Exception as ex2:
                    logger.warning(f"FSUB fallback check also failed for {fallback}: {ex2}")
            
            if "CHAT_ADMIN_REQUIRED" in str(e).upper():
                logger.error(f"❌ Bot must be an ADMIN with invite permissions in {item.get('name')} ({chat_target}) to verify members!")
            continue
            
    return unsubbed

def get_fsub_keyboard(unsubbed_list):
    buttons = []
    for item in unsubbed_list:
        raw_link = item.get("link") or item.get("chat") or item.get("chat_id")
        link = format_fsub_url(raw_link)
        buttons.append([InlineKeyboardButton(f"Join {item['name']}", url=link)])
    buttons.append([InlineKeyboardButton("🔄 Verify / Try Again", callback_data="check_fsub_again")])
    return InlineKeyboardMarkup(buttons)

# ----------------- Auto Group Add Detector & Notifier -----------------
@app.on_chat_member_updated()
async def on_bot_added(client: Client, chat_member: ChatMemberUpdated):
    if chat_member.new_chat_member and chat_member.new_chat_member.user.is_self:
        chat = chat_member.chat
        if chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await add_group(chat.id, chat.title or "Group")
            logger.info(f"👥 Bot added to Group: {chat.title} ({chat.id})")
            
            # --- Admin Notification System ---
            adder = chat_member.from_user
            adder_mention = adder.mention if adder else "Unknown User"
            
            try:
                member_count = await client.get_chat_members_count(chat.id)
            except:
                member_count = "Unknown"
                
            notification_text = (
                f"🔔 **Bot Added to New Group!**\n\n"
                f"📌 **Group Name:** {chat.title}\n"
                f"🆔 **Group ID:** `{chat.id}`\n"
                f"👤 **Added By:** {adder_mention}\n"
                f"👥 **Total Members:** `{member_count}`"
            )
            
            # Send alert to all Admins
            for admin_id in ADMINS:
                try:
                    await client.send_message(chat_id=admin_id, text=notification_text)
                except Exception as e:
                    logger.error(f"Could not send new group alert to admin {admin_id}: {e}")

# ----------------- 🌟 /start Command & Deep-Link Delivery -----------------
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Aspirant"
    await add_user(user_id, first_name)
    
    # Check FSUB with Premium Animated Warning Emoji
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await message.reply_text(
            '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> <b>Access Denied!</b>\n\nPlease join our official channels below to unlock search access:',
            reply_markup=get_fsub_keyboard(unsubbed),
            parse_mode=enums.ParseMode.HTML
        )
    
    # Deep Link Handler: Group click se DM mein file delivery
    raw_text = message.text.strip()
    if " " in raw_text:
        cmd, param = raw_text.split(" ", 1)
        param = param.strip()
        if param.startswith("get_"):
            try:
                msg_id_str = param.replace("get_", "").strip()
                msg_id = int(msg_id_str)
                await client.copy_message(
                    chat_id=user_id,
                    from_chat_id=CHANNEL_ID,
                    message_id=msg_id
                )
                return
            except Exception as e:
                logger.error(f"Deep link send error: {e}")
                return await message.reply_text(f"❌ Error delivering file: {str(e)}")

    bot_username = await get_bot_username(client)
    
    # Fully Animated Premium Emojis Integrated Welcome Text
    welcome_text = (
        f'<tg-emoji emoji-id="5325547803936572038">✨</tg-emoji> <b>Welcome to CA Notes Master Bot!</b> <tg-emoji emoji-id="5325547803936572038">✨</tg-emoji>\n\n'
        f'<tg-emoji emoji-id="6199464934460365423">🩷</tg-emoji> Hi <b>{first_name}</b>!\n\n'
        f'<tg-emoji emoji-id="6221958163520819301">🔥</tg-emoji> <b>What I Do:</b>\n'
        f'Find CA Foundation & Inter study materials instantly - Notes, Question Banks, MTPs, RTPs & Drive Links!\n\n'
        f'<tg-emoji emoji-id="5388790720628811468">🔍</tg-emoji> <b>How to Search:</b>\n'
        f'Just type any keyword here:\n'
        f'• <code>Hardik Sir Accounts</code>\n'
        f'• <code>Business Economics MTP</code>\n'
        f'• <code>Question Bank Sept 26</code>\n\n'
        f'<tg-emoji emoji-id="6017003526746542911">📚</tg-emoji> Get instant results with one tap!\n\n'
        f'<tg-emoji emoji-id="5422439311196834318">💡</tg-emoji> <b>Pro Tip:</b> Add me to your study group and use <code>/notes &lt;topic&gt;</code> or <code>/search &lt;topic&gt;</code> command!'
    )

    buttons = [
        [InlineKeyboardButton("➕ Add Me to Group", url=f"https://t.me/{bot_username}?startgroup=true")],
        [InlineKeyboardButton("❓ Help & Commands", callback_data="help_menu")]
    ]

    await message.reply_text(
        welcome_text, 
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode=enums.ParseMode.HTML
    )

# /id Command
@app.on_message(filters.command("id"))
async def get_my_id(client: Client, message: Message):
    if message.chat.type == enums.ChatType.PRIVATE:
        await message.reply_text(f"👤 **Your Telegram User ID:** `{message.from_user.id}`")
    else:
        await message.reply_text(f"👥 **Group Chat ID:** `{message.chat.id}`")

# /help Command
@app.on_message(filters.command("help"))
async def help_handler(client: Client, message: Message):
    help_text = (
        "📖 **CA Notes Master - Help Guide**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**🔍 How to Search:**\n"
        "• In DM: Just type any keyword directly\n"
        "• In Groups: Use `/search <keyword>` or `/notes <keyword>`\n\n"
        "**✨ Search Examples:**\n"
        "• `Hardik Sir Law`\n"
        "• `Business Economics MTP`\n"
        "• `Question Bank Sept 26`\n"
        "• `Accounts Drive Link`\n\n"
        "**📋 Available Commands:**\n"
        "• `/start` - Start the bot\n"
        "• `/help` - Show this help message\n"
        "• `/id` - Get your user ID or group ID\n"
        "• `/search <query>` or `/notes <query>` - Search in groups\n"
        "• `/ping` - Check bot response speed\n"
        "• `/about` - About this bot\n\n"
        "**💡 Pro Tips:**\n"
        "• Use specific keywords for better results\n"
        "• Try faculty names, subject names, or material types\n"
        "• Add bot to your study group for easy access\n"
        "• Use Next/Prev buttons to browse more results"
    )

    await message.reply_text(help_text)

# Help callback handler
@app.on_callback_query(filters.regex("^help_menu$"))
async def help_callback(client: Client, query: CallbackQuery):
    help_text = (
        "📖 **CA Notes Master - Quick Guide**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**🔍 How to Search:**\n"
        "• In DM: Just type any keyword directly\n"
        "• In Groups: Use `/search <keyword>` or `/notes <keyword>`\n\n"
        "**✨ Search Examples:**\n"
        "• `Hardik Sir Law`\n"
        "• `Business Economics MTP`\n"
        "• `Question Bank Sept 26`\n\n"
        "**📋 Commands:**\n"
        "• `/help` - Show complete help\n"
        "• `/id` - Get your ID\n"
        "• `/ping` - Bot speed check\n\n"
        "Type `/help` for detailed guide!"
    )
    await query.answer()
    await query.message.reply_text(help_text)

# /ping Command - Health Check
@app.on_message(filters.command("ping"))
async def ping_handler(client: Client, message: Message):
    import time
    start = time.time()
    msg = await message.reply_text("🏓 Pinging...")
    end = time.time()
    await msg.edit(f"🏓 **Pong!**\n⚡ **Response Time:** `{(end-start)*1000:.2f}ms`")

# /about Command
@app.on_message(filters.command("about"))
async def about_handler(client: Client, message: Message):
    about_text = (
        "ℹ️ **About CA Notes Master Bot**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 **Bot Name:** CA Notes Master\n"
        "📌 **Version:** 2.0 Professional\n"
        "🔧 **Framework:** Pyrogram (Python)\n"
        "💾 **Database:** MongoDB\n"
        "🚀 **Features:**\n"
        "  • Smart AI-powered search\n"
        "  • Multi-format support (PDFs, Photos, Links)\n"
        "  • Group & DM integration\n"
        "  • Real-time indexing\n"
        "  • Broadcast messaging\n\n"
        "👨‍💻 **Developer:** Gourav\n"
        "📅 **Last Updated:** August 2026\n\n"
        "💡 **Purpose:** Making CA Foundation & Inter study materials accessible to all aspirants instantly!"
    )

    buttons = [
        [InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/Cagourav_18")]
    ]

    await message.reply_text(about_text, reply_markup=InlineKeyboardMarkup(buttons))

def admin_only():
    async def func(flt, client, message):
        return message.from_user.id in ADMINS
    return filters.create(func)

# /logs Command (Admin Only)
@app.on_message(filters.command("logs") & admin_only())
async def logs_handler(client: Client, message: Message):
    try:
        if not os.path.exists('bot.log'):
            return await message.reply_text("❌ Log file (bot.log) not found.")

        with open('bot.log', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            last_50 = ''.join(lines[-50:])

        if not last_50.strip():
            return await message.reply_text("✅ No logs found. Bot is running clean!")

        if len(last_50) <= 3900:
            await message.reply_text(f"📄 **Recent Logs (Last 50 lines):**\n```\n{last_50}\n```")
        else:
            temp_log_path = "recent_logs.txt"
            with open(temp_log_path, "w", encoding="utf-8") as temp_f:
                temp_f.write(last_50)
            await message.reply_document(
                document=temp_log_path,
                caption="📄 **Recent Logs (Last 50 lines)**"
            )
            if os.path.exists(temp_log_path):
                os.remove(temp_log_path)
    except Exception as e:
        await message.reply_text(f"❌ Error reading logs: {e}")

# /groups Command (Admin Only) - To list all connected groups
@app.on_message(filters.command("groups") & admin_only())
async def list_groups_handler(client: Client, message: Message):
    status_msg = await message.reply_text("⏳ Fetching groups list from database...")
    
    groups = await get_groups_details()
    if not groups:
        return await status_msg.edit_text("❌ No connected groups found.")
        
    text = f"📋 **Connected Groups List (Total: {len(groups)}):**\n\n"
    for i, g in enumerate(groups, 1):
        text += f"{i}. **{g['title']}** (`{g['chat_id']}`)\n"
        
    if len(text) > 4000:
        file_path = "groups_list.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text.replace("**", "").replace("`", ""))
            
        await message.reply_document(
            document=file_path,
            caption=f"📋 **Complete Groups List (Total: {len(groups)})**"
        )
        await status_msg.delete()
        if os.path.exists(file_path):
            os.remove(file_path)
    else:
        await status_msg.edit_text(text)

@app.on_message(filters.command(["startfsub", "stopfsub", "fsub"]) & filters.private)
async def fsub_toggle_handler(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text("❌ Only Admins can change this setting.")

    cmd = message.command[0].lower()
    arg = message.command[1].lower() if len(message.command) > 1 else ""

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

@app.on_callback_query(filters.regex("^check_fsub_again$"))
async def fsub_callback(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    unsubbed = await check_fsub(client, user_id)
    if unsubbed:
        return await query.answer("❌ You haven't joined all required channels yet!", show_alert=True)
    
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.message.reply_text("✅ **Access Granted!** You can now search for any notes or study material.")

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

@app.on_edited_message(filters.chat(CHANNEL_ID))
async def channel_post_edited_listener(client: Client, message: Message):
    await channel_post_listener(client, message)

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
    last_reported = 0
    batch_size = INDEXING_BATCH_SIZE

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

            if count - last_reported >= 50:
                try:
                    await status_msg.edit_text(f"⏳ **Indexing in progress:** `{count}` items saved...")
                    last_reported = count
                except Exception:
                    pass
            await asyncio.sleep(INDEXING_SLEEP)
        except FloodWait as e:
            logger.warning(f"FloodWait: sleeping for {e.value} seconds")
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.error(f"Batch error during indexing: {e}")
            continue

    await status_msg.edit_text(f"✅ **Indexing Complete!**\nTotal **{count}** materials (PDFs, Photos & Links) are saved in the database.")

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

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply_text("❌ Only Admins can broadcast.")

    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text(
            "❗ **How to Broadcast:**\n\n"
            "1️⃣ **Reply** to any message/photo/video and type `/broadcast`\n"
            "2️⃣ OR directly type: `/broadcast Your message here`"
        )

    users = await get_all_users()
    groups = await get_all_groups()

    if not users and not groups:
        return await message.reply_text("❌ No users or groups found in database.")

    status_msg = await message.reply_text(
        f"📢 **Broadcast Starting...**\n\n"
        f"👥 Target Users: `{len(users)}`\n"
        f"💬 Target Groups: `{len(groups)}`"
    )

    u_success, u_failed = 0, 0
    g_success, g_failed = 0, 0

    for u_id in users:
        try:
            if message.reply_to_message:
                await message.reply_to_message.copy(chat_id=u_id)
            else:
                broadcast_text = message.text.split(" ", 1)[1]
                await client.send_message(chat_id=u_id, text=broadcast_text)
            u_success += 1
            await asyncio.sleep(BROADCAST_SLEEP)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            u_failed += 1
            logger.error(f"Broadcast failed for user {u_id}: {e}")

    for g_id in groups:
        try:
            if message.reply_to_message:
                await message.reply_to_message.copy(chat_id=g_id)
            else:
                broadcast_text = message.text.split(" ", 1)[1]
                await client.send_message(chat_id=g_id, text=broadcast_text)
            g_success += 1
            await asyncio.sleep(BROADCAST_SLEEP)
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            g_failed += 1
            logger.error(f"Broadcast failed for group {g_id}: {e}")

    await status_msg.edit_text(
        f"✅ **Broadcast Completed Successfully!**\n\n"
        f"👤 **Users (DM):**\n"
        f"  • Sent: `{u_success}` | Failed: `{u_failed}`\n\n"
        f"💬 **Groups:**\n"
        f"  • Sent: `{g_success}` | Failed: `{g_failed}`\n\n"
        f"📊 **Total Delivered:** `{u_success + g_success}`"
    )

EXCLUDED_COMMANDS = ["start", "index", "stats", "broadcast", "id", "startfsub", "stopfsub", "fsub", "help", "ping", "about", "logs", "groups"]

@app.on_message(filters.text & filters.private & ~filters.command(EXCLUDED_COMMANDS))
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

    if len(query_text) > 100:
        return await message.reply_text("❗ Search query too long. Please use shorter keywords.")

    results, total = await search_files(query_text, limit=SEARCH_RESULTS_LIMIT, skip=0)
    if not results:
        return await message.reply_text(
            f"❌ **No material found for:** `{query_text}`\n\n"
            "• Please check the spelling or try broader keywords."
        )

    buttons = []
    for item in results:
        display_name = get_display_title(item)
        buttons.append([InlineKeyboardButton(display_name, callback_data=f"get_{item['message_id']}")])

    safe_query = query_text[:35]
    if total > SEARCH_RESULTS_LIMIT:
        buttons.append([InlineKeyboardButton("Next Page ⏩", callback_data=f"page_1_{safe_query}")])

    await message.reply_text(
        f"🔍 **Search Results for:** `{query_text}`\n📊 **Total Found:** `{total}`\n\nTap below to receive the material directly:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_message(filters.group & filters.text)
async def group_search_handler(client: Client, message: Message):
    text = message.text.strip()
    parts = text.split(" ", 1)
    raw_cmd = parts[0].lower()

    valid_cmds = ["/notes", "/search", "/get"]
    if not any(raw_cmd == cmd or raw_cmd.startswith(f"{cmd}@") for cmd in valid_cmds):
        return

    await add_group(message.chat.id, message.chat.title or "Group")

    if len(parts) < 2 or not parts[1].strip():
        cmd_display = raw_cmd.split("@")[0]
        return await message.reply_text(
            f"❗ **Usage:** `{cmd_display} topic_name`"
        )

    query_text = parts[1].strip()

    if len(query_text) < 2:
        return await message.reply_text("❗ Please type at least 2 characters.")

    results, total = await search_files(query_text, limit=SEARCH_RESULTS_LIMIT, skip=0)

    if not results:
        return await message.reply_text(f"❌ No notes found for `{query_text}`.")

    bot_username = await get_bot_username(client)
    buttons = []
    for item in results:
        display_name = get_display_title(item)
        deep_link = f"https://t.me/{bot_username}?start=get_{item['message_id']}"
        buttons.append([InlineKeyboardButton(display_name, url=deep_link)])

    safe_query = query_text[:35]
    if total > SEARCH_RESULTS_LIMIT:
        buttons.append([InlineKeyboardButton("Next Page ⏩", callback_data=f"page_1_{safe_query}")])

    await message.reply_text(
        f"📚 **Search Results for {message.from_user.mention}:** `{query_text}` (Total: {total})\nTap any button below to get the file in your DM:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

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
        logger.error(f"File delivery error: {err_str}")
        await query.answer(f"❌ Error: {err_str[:60]}", show_alert=True)

@app.on_callback_query(filters.regex(r"^page_"))
async def pagination_callback(client: Client, query: CallbackQuery):
    try:
        prefix, page_str, query_text = query.data.split("_", 2)
        page = int(page_str)
        limit = PAGINATION_LIMIT
        skip = page * limit

        results, total = await search_files(query_text, limit=limit, skip=skip)
        if not results:
            return await query.answer("No more results available.", show_alert=True)

        is_group = query.message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]
        bot_username = await get_bot_username(client)

        buttons = []
        for item in results:
            display_name = get_display_title(item)
            if is_group:
                deep_link = f"https://t.me/{bot_username}?start=get_{item['message_id']}"
                buttons.append([InlineKeyboardButton(display_name, url=deep_link)])
            else:
                buttons.append([InlineKeyboardButton(display_name, callback_data=f"get_{item['message_id']}")])

        safe_query = query_text[:35]
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⏪ Prev", callback_data=f"page_{page - 1}_{safe_query}"))
        if total > skip + limit:
            nav.append(InlineKeyboardButton("Next ⏩", callback_data=f"page_{page + 1}_{safe_query}"))
        if nav:
            buttons.append(nav)

        await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer()
    except Exception as e:
        logger.error(f"Pagination Error: {e}")
        await query.answer(f"Error: {str(e)[:60]}", show_alert=True)

@app.on_inline_query()
async def inline_query_handler(client: Client, query: InlineQuery):
    text = query.query.strip()
    if not text:
        return
    
    results, _ = await search_files(text, limit=10)
    inline_results = []
    
    for idx, item in enumerate(results):
        display_name = get_display_title(item)
        if item.get("file_id"):
            inline_results.append(
                InlineQueryResultCachedDocument(
                    id=str(item.get("message_id") or idx),
                    title=display_name,
                    file_id=item["file_id"],
                    caption=item.get("caption", "")
                )
            )
            
    await query.answer(inline_results, cache_time=5)

# Flask Server for Render Port requirement
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is active and running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)

# ----------------- Main Execution -----------------
if __name__ == "__main__":
    web_thread = threading.Thread(target=run_web)
    web_thread.daemon = True
    web_thread.start()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(init_db())
        logger.info("🚀 CA Notes Master Bot Starting...")
        logger.info(f"👥 Admins: {len(ADMINS)}")
        logger.info(f"📢 Channel ID: {CHANNEL_ID}")
        app.run()
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
