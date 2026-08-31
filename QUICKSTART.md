# 🚀 Quick Start Guide - CA Notes Master Bot

## Step-by-Step Setup (5 Minutes)

### 1️⃣ Prerequisites Check
- [ ] Python 3.8+ installed (`python --version`)
- [ ] MongoDB account (free at mongodb.com/atlas)
- [ ] Telegram Bot Token from @BotFather
- [ ] API credentials from my.telegram.org

### 2️⃣ Installation

```bash
# Clone or download the repository
cd studymatbot-main

# Install dependencies
pip install -r requirements.txt
```

### 3️⃣ Configuration

**Step 1: Create .env file**
```bash
# Copy the example template
copy .env.example .env
```

**Step 2: Get Required Credentials**

#### A. Telegram API Credentials
1. Go to https://my.telegram.org
2. Login with your phone number
3. Click "API Development Tools"
4. Copy `API_ID` and `API_HASH`

#### B. Bot Token
1. Open Telegram and search for @BotFather
2. Send `/newbot` and follow instructions
3. Copy the bot token

#### C. Channel & Group IDs
1. Forward a message from your channel/group to @userinfobot
2. Copy the chat ID (it should be negative, like `-1001234567890`)

#### D. MongoDB URI
1. Sign up at https://mongodb.com/atlas
2. Create a free cluster
3. Click "Connect" → "Connect your application"
4. Copy the connection string
5. Replace `<password>` with your database password

**Step 3: Fill .env file**
```env
API_ID=12345678
API_HASH=abc123def456
BOT_TOKEN=123456:ABC-DEF1234ghIkl
ADMINS=123456789,987654321
CHANNEL_ID=-1001234567890
GROUP_ID=-1001234567890
FSUB_CHANNEL=@YourChannel
FSUB_GROUP=@YourGroup
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DB_NAME=NotesSearchBot
```

### 4️⃣ Setup Your Channel

**Step 1: Create a channel**
- Make it private
- Add your bot as admin with "Post Messages" permission

**Step 2: Upload some files**
- Upload PDFs, photos, or videos
- Add descriptive captions/filenames

**Step 3: Get Channel ID**
- Forward any message from channel to @userinfobot
- Copy the ID and add to .env as `CHANNEL_ID`

### 5️⃣ Run the Bot

```bash
# Start the bot
python bot.py
```

**You should see:**
```
✅ MongoDB connection established successfully
✅ Database indexes created successfully
🚀 CA Notes Master Bot Started Successfully!
```

### 6️⃣ Initial Setup Commands

**Step 1: Start the bot**
- Open your bot in Telegram
- Send `/start`

**Step 2: Verify admin access**
- Send `/stats` - You should see statistics
- If you get "Not admin" error, check your user ID with `/id` and add it to ADMINS in .env

**Step 3: Index your channel**
```
/index
```
This will scan all messages in your channel and save them to database.

**Step 4: Test search**
- Type any keyword
- You should see search results with buttons

### 7️⃣ Force Subscribe Setup (Optional)

If you want users to join your channels before using the bot:

```
/startfsub
```

To disable it:
```
/stopfsub
```

---

## 🎯 Quick Command Reference

### User Commands
- `/start` - Welcome message
- `/help` - Complete guide
- `/id` - Get your user ID
- `/about` - Bot information
- `/ping` - Check bot response time

### Admin Commands
- `/stats` - View statistics
- `/index` - Index channel files
- `/broadcast` - Send message to all users
- `/startfsub` - Enable force subscribe
- `/stopfsub` - Disable force subscribe
- `/logs` - View error logs

---

## ✅ Testing Checklist

- [ ] Bot starts without errors
- [ ] Database connection works
- [ ] `/start` shows welcome message
- [ ] `/stats` shows statistics (for admins)
- [ ] `/index` indexes files successfully
- [ ] Search returns results
- [ ] Files are delivered when clicked
- [ ] Bot works in groups with `/search`
- [ ] Force subscribe works (if enabled)
- [ ] Broadcast works

---

## 🐛 Common Issues

### "Missing required environment variables"
**Fix:** Make sure your .env file has all required variables set

### "MongoDB connection failed"
**Fix:** Check your MONGO_URI is correct and cluster is running

### "You are not an Admin"
**Fix:** 
1. Send `/id` to the bot
2. Add your user ID to ADMINS in .env (comma-separated, no spaces)
3. Restart the bot

### "Channel Access Error"
**Fix:** Make sure bot is admin in the channel with post permissions

### Files not indexing
**Fix:** 
1. Verify CHANNEL_ID is correct (negative number)
2. Check bot has access to channel
3. Try `/index` again

### Search returns no results
**Fix:**
1. Run `/index` first to populate database
2. Check if files have captions or filenames
3. Try broader keywords

---

## 📱 Adding Bot to Groups

1. Add bot to your study group
2. Make it admin (optional but recommended)
3. Users can search with `/search <query>`
4. Files are delivered in DM

---

## 🎓 Pro Tips

1. **Better Search Results**
   - Upload files with descriptive names
   - Add detailed captions
   - Include faculty names, subjects, topics

2. **Organize Your Channel**
   - Use consistent naming conventions
   - Group related files together
   - Add dates to time-sensitive materials

3. **Maintenance**
   - Run `/stats` regularly to monitor growth
   - Check `/logs` if something goes wrong
   - Re-index after uploading many files

4. **Growth**
   - Start with FSUB disabled (`/stopfsub`)
   - Enable FSUB after reaching target users
   - Use broadcast sparingly to avoid spam

---

## 🆘 Need Help?

1. Check the README.md for detailed documentation
2. Review CHANGELOG.md for recent changes
3. Check bot.log file for error details
4. Join our support group (see .env FSUB_GROUP)

---

**Setup Time:** ~5 minutes
**Difficulty:** Beginner-friendly
**Support:** Community-driven

Happy coding! 🎉
