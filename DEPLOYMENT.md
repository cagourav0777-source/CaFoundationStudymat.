# 🚀 Deployment Checklist

## Pre-Deployment

### Environment Setup
- [ ] Python 3.8+ installed and verified
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created from `.env.example`
- [ ] All environment variables filled correctly
- [ ] MongoDB cluster created and accessible
- [ ] Telegram bot created via @BotFather
- [ ] API credentials obtained from my.telegram.org

### Bot Configuration
- [ ] Bot added to notes channel as admin
- [ ] Channel ID obtained and added to `.env`
- [ ] Admin user IDs obtained and added to `.env`
- [ ] FSUB channels/groups configured (if using)
- [ ] Test channel messages have proper captions/filenames

### Testing Locally
- [ ] Bot starts without errors
- [ ] Database connection successful
- [ ] `/start` command works
- [ ] `/help` command displays properly
- [ ] `/id` returns correct IDs
- [ ] `/stats` works for admin
- [ ] `/index` indexes channel files
- [ ] Search returns results
- [ ] File delivery works in DM
- [ ] Bot works in groups with `/search`
- [ ] Pagination works (Next/Prev)
- [ ] Broadcast works
- [ ] FSUB toggle works (if using)
- [ ] Error handling works (try invalid commands)

## Deployment Options

### Option 1: VPS/Server (Recommended)
**Providers:** DigitalOcean, AWS, Linode, Vultr

**Steps:**
```bash
# 1. Connect to server
ssh user@your-server-ip

# 2. Install Python and Git
sudo apt update
sudo apt install python3 python3-pip git -y

# 3. Clone/upload bot files
git clone your-repo-url
# OR upload via SCP/FTP

# 4. Install dependencies
cd studymatbot-main
pip3 install -r requirements.txt

# 5. Create and configure .env
nano .env
# (paste your configuration)

# 6. Test run
python3 bot.py

# 7. Setup as service (keeps running)
sudo nano /etc/systemd/system/canotesbot.service
```

**Service File Content:**
```ini
[Unit]
Description=CA Notes Master Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/studymatbot-main
ExecStart=/usr/bin/python3 /path/to/studymatbot-main/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and Start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable canotesbot
sudo systemctl start canotesbot
sudo systemctl status canotesbot
```

### Option 2: Heroku
```bash
# 1. Install Heroku CLI
# 2. Login
heroku login

# 3. Create app
heroku create your-bot-name

# 4. Add Procfile
echo "worker: python bot.py" > Procfile

# 5. Set environment variables
heroku config:set API_ID=your_api_id
heroku config:set API_HASH=your_api_hash
# (set all variables from .env)

# 6. Deploy
git add .
git commit -m "Deploy bot"
git push heroku main

# 7. Scale worker
heroku ps:scale worker=1
```

### Option 3: Railway.app
1. Connect GitHub repository
2. Add environment variables in dashboard
3. Deploy automatically

### Option 4: Local Machine (Not Recommended for Production)
```bash
# Run in background
nohup python bot.py > output.log 2>&1 &

# Or use screen/tmux
screen -S cabot
python bot.py
# Press Ctrl+A then D to detach
```

## Post-Deployment

### Immediate Checks
- [ ] Bot responds to `/start`
- [ ] Search works
- [ ] Files are delivered
- [ ] Admin commands work
- [ ] No errors in logs

### First Hour Monitoring
- [ ] Check logs regularly: `tail -f bot.log`
- [ ] Monitor server resources (CPU, RAM)
- [ ] Test from different users
- [ ] Test in groups
- [ ] Verify database writes

### Initial Configuration
- [ ] Run `/index` to populate database
- [ ] Set FSUB status (`/startfsub` or `/stopfsub`)
- [ ] Send test broadcast to verify
- [ ] Share bot link with test users
- [ ] Monitor `/stats` for growth

## Maintenance

### Daily
- [ ] Check `/stats` for user growth
- [ ] Review `/logs` for errors
- [ ] Monitor server resources

### Weekly
- [ ] Check MongoDB storage usage
- [ ] Review search patterns
- [ ] Update content in channel
- [ ] Re-index if needed (`/index`)

### Monthly
- [ ] Update dependencies if needed
- [ ] Backup database
- [ ] Review and clean logs
- [ ] Analyze user feedback

## Monitoring Commands

```bash
# Check if bot is running
ps aux | grep bot.py

# View live logs
tail -f bot.log

# Check last 50 lines
tail -n 50 bot.log

# Search for errors
grep -i error bot.log

# Check bot status (if using systemd)
sudo systemctl status canotesbot

# Restart bot
sudo systemctl restart canotesbot

# View system logs
journalctl -u canotesbot -f
```

## Troubleshooting

### Bot Not Starting
```bash
# Check Python version
python --version  # Should be 3.8+

# Check dependencies
pip list

# Run with verbose logging
python bot.py

# Check .env file
cat .env
```

### Bot Crashes
```bash
# Check logs
tail -n 100 bot.log

# Check system resources
free -h
df -h

# Restart bot
sudo systemctl restart canotesbot
```

### Database Issues
```bash
# Test MongoDB connection
mongo "your-connection-string"

# Check database size
# (in MongoDB Compass or Atlas dashboard)

# Clear old sessions
rm *.session*
```

## Backup Strategy

### Database Backup
```bash
# MongoDB Atlas: Use automated backups (free tier)
# Manual backup:
mongodump --uri="your-mongodb-uri" --out=backup-$(date +%Y%m%d)
```

### Code Backup
```bash
# Push to Git regularly
git add .
git commit -m "Update"
git push origin main
```

### Environment Backup
```bash
# Backup .env (store securely, not in Git!)
cp .env .env.backup
```

## Security Best Practices

- [ ] Never commit .env to Git
- [ ] Keep dependencies updated
- [ ] Use strong MongoDB password
- [ ] Limit admin user IDs
- [ ] Monitor logs for suspicious activity
- [ ] Use HTTPS for webhook (if using webhooks)
- [ ] Regularly rotate bot token if compromised
- [ ] Backup database regularly
- [ ] Use firewall on server
- [ ] Keep server OS updated

## Performance Optimization

### If Bot Becomes Slow
1. Check database indexes: `db.files.getIndexes()`
2. Monitor MongoDB Atlas metrics
3. Upgrade server resources if needed
4. Implement caching (future improvement)
5. Optimize search queries
6. Clean old logs: `> bot.log`

### If Database Grows Large
1. Archive old files
2. Implement data retention policy
3. Upgrade MongoDB cluster
4. Optimize document structure

## Support & Updates

### Get Help
- Review README.md
- Check CHANGELOG.md
- Read bot.log
- Test in development environment first

### Stay Updated
- Star the repository for updates
- Join developer community
- Follow best practices
- Implement security patches

---

## Quick Commands Reference

```bash
# Start bot
python bot.py

# Stop bot (if running in foreground)
Ctrl+C

# Stop bot (if running as service)
sudo systemctl stop canotesbot

# Restart bot
sudo systemctl restart canotesbot

# View logs
tail -f bot.log

# Clear logs
> bot.log

# Check status
sudo systemctl status canotesbot

# Update dependencies
pip install -r requirements.txt --upgrade
```

---

## Emergency Contacts

**Bot Issues:**
- Check logs first
- Review error messages
- Test commands manually

**Database Issues:**
- Check MongoDB Atlas status
- Verify connection string
- Check cluster health

**Server Issues:**
- Check server status
- Monitor resources
- Restart if needed

---

**Deployment Status:** ⬜ Not Started / 🟡 In Progress / ✅ Complete

**Last Updated:** [Date]
**Deployed By:** [Name]
**Server:** [Provider/Location]

---

🎉 **Good luck with your deployment!** 🎉
