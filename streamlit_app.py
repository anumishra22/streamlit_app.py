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
import sqlite3
from datetime import datetime
from playwright.async_api import async_playwright
from telegram.ext import Application, CommandHandler
import streamlit.components.v1 as components

# ============== CONFIGURATION ==============
TELEGRAM_BOT_TOKEN = "8566154217:AAG-Y2dEOD2G6dDPGIJGUI_5YGHRT0XaXXQ"
TELEGRAM_ADMIN_ID = "8567425809"  # Aapka ID jahan updates jayenge

MAX_MEMORY_PERCENT = 75
CRITICAL_MEMORY = 85
MAX_LOGS = 50
AUTO_PING_INTERVAL = 180  # 3 minutes
# ===========================================

# ============== DATABASE SETUP ==============
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    password TEXT,
                    name TEXT,
                    created_at TEXT,
                    last_login TEXT,
                    total_messages INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1
                )''')
    
    # Sessions table
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    server_id TEXT,
                    login_time TEXT,
                    ip_address TEXT,
                    device TEXT,
                    is_running INTEGER DEFAULT 0,
                    messages_sent INTEGER DEFAULT 0,
                    group_name TEXT,
                    last_active TEXT
                )''')
    
    # Global stats
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_users INTEGER DEFAULT 0,
                    total_messages INTEGER DEFAULT 0,
                    total_sessions INTEGER DEFAULT 0,
                    last_updated TEXT
                )''')
    
    # Insert default stats
    c.execute("INSERT OR IGNORE INTO stats (id, total_users, total_messages, total_sessions, last_updated) VALUES (1, 0, 0, 0, ?)", 
              (datetime.now().isoformat(),))
    
    conn.commit()
    conn.close()

init_db()

# ============== PAGE CONFIG ==============
st.set_page_config(
    page_title="Anurag Mishra Bot Controller",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============== PROFESSIONAL CSS ==============
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .main {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        min-height: 100vh;
        color: white;
    }
    
    /* Auth Container */
    .auth-container {
        max-width: 450px;
        margin: 100px auto;
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(20px);
        border-radius: 30px;
        padding: 40px;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 25px 50px rgba(0,0,0,0.5);
    }
    
    .auth-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 900;
        margin-bottom: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .auth-subtitle {
        text-align: center;
        color: rgba(255,255,255,0.6);
        margin-bottom: 30px;
        font-size: 1rem;
    }
    
    /* Input Fields */
    .stTextInput > div > div > input {
        background: rgba(0,0,0,0.3) !important;
        border: 2px solid rgba(255,255,255,0.1) !important;
        border-radius: 15px !important;
        color: white !important;
        padding: 15px 20px !important;
        font-size: 1rem !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 4px rgba(102,126,234,0.2) !important;
    }
    
    /* Buttons */
    .stButton > button {
        width: 100% !important;
        border-radius: 15px !important;
        height: 55px !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        border: none !important;
        transition: all 0.3s !important;
    }
    
    .btn-primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }
    
    .btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 15px 30px rgba(102,126,234,0.4) !important;
    }
    
    .btn-success {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%) !important;
        color: #000 !important;
    }
    
    .btn-danger {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%) !important;
    }
    
    /* Dashboard */
    .dashboard-header {
        background: linear-gradient(135deg, rgba(102,126,234,0.2) 0%, rgba(118,75,162,0.2) 100%);
        backdrop-filter: blur(20px);
        border-radius: 25px;
        padding: 30px;
        margin-bottom: 25px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .dashboard-title {
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
        background: linear-gradient(135deg, #fff 0%, #a8edea 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .user-badge {
        display: inline-flex;
        align-items: center;
        gap: 10px;
        background: rgba(255,255,255,0.1);
        padding: 10px 20px;
        border-radius: 50px;
        margin-top: 15px;
        font-weight: 600;
    }
    
    .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 1.2rem;
        color: #333;
    }
    
    /* Cards */
    .glass-card {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(20px);
        border-radius: 25px;
        padding: 25px;
        border: 1px solid rgba(255,255,255,0.1);
        margin-bottom: 20px;
    }
    
    .card-title {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Stats Grid */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        margin-bottom: 25px;
    }
    
    .stat-box {
        background: rgba(0,0,0,0.2);
        border-radius: 20px;
        padding: 25px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.05);
        transition: all 0.3s;
    }
    
    .stat-box:hover {
        transform: translateY(-5px);
        background: rgba(255,255,255,0.08);
    }
    
    .stat-value {
        font-size: 2.5rem;
        font-weight: 900;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .stat-label {
        color: rgba(255,255,255,0.6);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 5px;
    }
    
    /* Status Badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 12px 24px;
        border-radius: 50px;
        font-weight: 700;
        font-size: 0.95rem;
    }
    
    .status-online {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: #000;
        box-shadow: 0 10px 30px rgba(56,239,125,0.3);
    }
    
    .status-offline {
        background: linear-gradient(135deg, #636e72 0%, #b2bec3 100%);
        color: #fff;
    }
    
    .pulse-dot {
        width: 8px;
        height: 8px;
        background: currentColor;
        border-radius: 50%;
        animation: blink 1.5s infinite;
    }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    
    /* Controls */
    .control-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 15px;
        margin: 20px 0;
    }
    
    /* Logs */
    .logs-container {
        background: rgba(0,0,0,0.3);
        border-radius: 20px;
        padding: 20px;
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid rgba(255,255,255,0.05);
    }
    
    .log-entry {
        padding: 12px 15px;
        margin: 8px 0;
        border-radius: 12px;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        border-left: 3px solid;
        animation: slideIn 0.3s ease;
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    .log-success { background: rgba(17,153,142,0.15); border-color: #11998e; color: #38ef7d; }
    .log-error { background: rgba(255,65,108,0.15); border-color: #ff416c; color: #ff4b2b; }
    .log-warning { background: rgba(254,202,87,0.15); border-color: #feca57; color: #feca57; }
    .log-info { background: rgba(102,126,234,0.15); border-color: #667eea; color: #a8edea; }
    
    /* Telegram Badge */
    .tg-float {
        position: fixed;
        bottom: 25px;
        right: 25px;
        background: linear-gradient(135deg, #0088cc 0%, #00a8e8 100%);
        color: white;
        padding: 15px 25px;
        border-radius: 50px;
        font-weight: 700;
        box-shadow: 0 15px 35px rgba(0,136,204,0.4);
        display: flex;
        align-items: center;
        gap: 10px;
        z-index: 9999;
    }
    
    .tg-indicator {
        width: 10px;
        height: 10px;
        background: #00ff88;
        border-radius: 50%;
        animation: pulse 1s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.2); }
    }
    
    /* Form Elements */
    .stNumberInput > div > div > input {
        background: rgba(0,0,0,0.3) !important;
        border: 2px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        color: white !important;
    }
    
    .stTextArea > div > div > textarea {
        background: rgba(0,0,0,0.3) !important;
        border: 2px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        color: white !important;
        font-family: 'Courier New', monospace !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); border-radius: 10px; }
    ::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 10px; }
    
    /* Responsive */
    @media (max-width: 768px) {
        .stats-grid { grid-template-columns: repeat(2, 1fr); }
        .control-grid { grid-template-columns: repeat(2, 1fr); }
    }
    </style>
""", unsafe_allow_html=True)

# ============== TELEGRAM MANAGER ==============
class TelegramManager:
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
            self.app.add_handler(CommandHandler("users", self.cmd_users))
            self.app.add_handler(CommandHandler("stats", self.cmd_stats))
            self.app.add_handler(CommandHandler("broadcast", self.cmd_broadcast))
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
            await update.message.reply_text("⛔ Unauthorized!")
            return
        await update.message.reply_text("✅ *Anurag Mishra Bot Controller*\n\nUse /help", parse_mode='Markdown')
    
    async def cmd_users(self, update, context):
        if not self.is_admin(update):
            return
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT username, name, last_login, total_messages FROM users WHERE is_active=1 ORDER BY last_login DESC")
        users = c.fetchall()
        conn.close()
        
        text = "👥 *ACTIVE USERS*\n\n"
        for u in users[:10]:
            uname, name, last, msgs = u
            text += f"👤 *{name}* (`{uname}`)\n🕐 {last[:16] if last else 'Never'}\n💬 {msgs} msgs\n\n"
        
        await update.message.reply_text(text or "No users", parse_mode='Markdown')
    
    async def cmd_stats(self, update, context):
        if not self.is_admin(update):
            return
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT total_users, total_messages, total_sessions FROM stats WHERE id=1")
        stats = c.fetchone()
        c.execute("SELECT COUNT(*) FROM users WHERE is_active=1")
        active_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM sessions WHERE is_running=1")
        active_sessions = c.fetchone()[0]
        conn.close()
        
        mem = psutil.virtual_memory()
        
        await update.message.reply_text(f"""
📊 *GLOBAL STATISTICS - Anurag Mishra*

👥 Total Users: `{stats[0] if stats else 0}`
🟢 Active Users: `{active_users}`
💬 Total Messages: `{stats[1] if stats else 0}`
🖥️ Active Sessions: `{active_sessions}`
🧠 RAM Usage: `{mem.percent}%`

⏰ `{datetime.now().strftime('%H:%M:%S')}`
        """, parse_mode='Markdown')
    
    async def cmd_broadcast(self, update, context):
        if not self.is_admin(update):
            return
        msg = ' '.join(context.args) if context.args else "Broadcast from Anurag"
        await self.send_to_admin(f"📢 *BROADCAST*\n\n{msg}", "broadcast")
        await update.message.reply_text("Sent!", parse_mode='Markdown')
    
    async def cmd_help(self, update, context):
        if not self.is_admin(update):
            return
        await update.message.reply_text("""
🤖 *Anurag Mishra Commands*

/users - List users
/stats - Global statistics
/broadcast [msg] - Send message
/help - This help

⚡ Auto-monitoring active
        """, parse_mode='Markdown')
    
    async def send_to_admin(self, text, msg_type="info"):
        if not self.enabled or not self.app:
            return
        
        now = time.time()
        if msg_type not in ["system", "login", "critical", "broadcast"] and now - self.last_alert < self.alert_cooldown:
            return
        self.last_alert = now
        
        full_text = f"🤖 *Anurag Mishra Controller*\n\n{text}\n\n⏰ `{datetime.now().strftime('%H:%M:%S')}`"
        
        try:
            await self.app.bot.send_message(
                chat_id=self.admin_id,
                text=full_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Send error: {e}")
    
    async def send_login_alert(self, username, name, user_id, ip, device, total_users, total_msgs):
        await self.send_to_admin(f"""
🔔 *NEW USER LOGIN*

👤 *{name}* (`{username}`)
🆔 ID: `{user_id}`
📍 IP: `{ip}`
💻 Device: `{device}`

📊 *Current Stats:*
👥 Total Users: `{total_users}`
💬 Total Messages: `{total_msgs}`
        """, "login")

# ============== DATABASE FUNCTIONS ==============
def get_db():
    return sqlite3.connect('users.db')

def create_user(username, password, name):
    conn = get_db()
    c = conn.cursor()
    user_id = "AM-" + hashlib.md5((username + str(time.time())).encode()).hexdigest()[:8].upper()
    try:
        c.execute("INSERT INTO users (id, username, password, name, created_at, last_login) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, password, name, datetime.now().isoformat(), datetime.now().isoformat()))
        c.execute("UPDATE stats SET total_users = total_users + 1, last_updated = ? WHERE id = 1",
                (datetime.now().isoformat(),))
        conn.commit()
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def verify_user(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, total_messages FROM users WHERE username=? AND password=? AND is_active=1",
              (username, password))
    result = c.fetchone()
    if result:
        c.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.now().isoformat(), result[0]))
        conn.commit()
    conn.close()
    return result

def get_global_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT total_users, total_messages FROM stats WHERE id=1")
    stats = c.fetchone()
    conn.close()
    return stats or (0, 0)

def update_message_count(user_id, count):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET total_messages = total_messages + ? WHERE id = ?", (count, user_id))
    c.execute("UPDATE stats SET total_messages = total_messages + ? WHERE id = 1", (count,))
    conn.commit()
    conn.close()

def create_session(user_id, server_id, ip, device):
    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO sessions (user_id, server_id, login_time, ip_address, device, last_active)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (user_id, server_id, datetime.now().isoformat(), ip, device, datetime.now().isoformat()))
    c.execute("UPDATE stats SET total_sessions = total_sessions + 1 WHERE id = 1")
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id

def update_session(session_id, messages=0, is_running=False, group_name=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("""UPDATE sessions SET messages_sent = ?, is_running = ?, group_name = ?, last_active = ?
                 WHERE id = ?""",
              (messages, 1 if is_running else 0, group_name, datetime.now().isoformat(), session_id))
    conn.commit()
    conn.close()

# ============== MEMORY MANAGER ==============
class MemoryManager:
    def __init__(self):
        self.process = psutil.Process()
        self.last_restart = 0
        
    def get_ram(self):
        return psutil.virtual_memory().percent
    
    def cleanup(self):
        if 'logs' in st.session_state and len(st.session_state.logs) > MAX_LOGS:
            st.session_state.logs = st.session_state.logs[:MAX_LOGS]
        
        keep = ['authenticated', 'user_id', 'username', 'name', 'session_id', 'server_id',
                'bot_running', 'logs', 'memory_mgr', 'telegram_mgr', 'restart_count',
                'cleanup_count', 'message_count', 'group_name', 'last_health_check']
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

# ============== INIT ==============
if 'memory_mgr' not in st.session_state:
    st.session_state.memory_mgr = MemoryManager()
    st.session_state.telegram_mgr = TelegramManager(TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID)
    st.session_state.logs = []
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.name = None
    st.session_state.session_id = None
    st.session_state.server_id = "SRV-" + hashlib.md5(str(time.time()).encode()).hexdigest()[:6].upper()
    st.session_state.bot_running = False
    st.session_state.restart_count = 0
    st.session_state.cleanup_count = 0
    st.session_state.message_count = 0
    st.session_state.group_name = ""
    st.session_state.last_health_check = time.time()

mm = st.session_state.memory_mgr
tg = st.session_state.telegram_mgr

def log(msg, level="INFO"):
    t = datetime.now().strftime("%H:%M:%S")
    colors = {"SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️", "LOGIN": "🔔"}
    emoji = colors.get(level, "•")
    entry = f"{emoji} [{t}] {level}: {msg}"
    st.session_state.logs.insert(0, entry)
    if len(st.session_state.logs) > MAX_LOGS:
        st.session_state.logs.pop()

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

def get_system_info():
    try:
        import socket
        import requests
        ip = requests.get('https://api.ipify.org?format=json', timeout=5).json().get('ip', 'Unknown')
    except:
        ip = 'Unknown'
    import platform
    return {'ip': ip, 'device': platform.system() + " " + platform.release()}

# ============== KEEP ALIVE ==============
def keep_alive():
    while True:
        try:
            if mm.need_restart():
                st.session_state.trigger_restart = True
            
            # Update session
            if st.session_state.get('session_id'):
                update_session(st.session_state.session_id, 
                           st.session_state.get('message_count', 0),
                           st.session_state.get('bot_running', False),
                           st.session_state.get('group_name', ''))
            
            time.sleep(AUTO_PING_INTERVAL)
        except:
            time.sleep(60)

if 'ka_started' not in st.session_state:
    threading.Thread(target=keep_alive, daemon=True).start()
    st.session_state.ka_started = True

# ============== START TELEGRAM ==============
if 'tg_started' not in st.session_state:
    def start_tg():
        asyncio.run(tg.init())
    threading.Thread(target=start_tg, daemon=True).start()
    st.session_state.tg_started = True

# ============== BOT LOGIC ==============
async def user_bot(url, msg, delay, group_name):
    st.session_state.bot_running = True
    st.session_state.group_name = group_name
    attempt = 0
    
    await tg.send_to_admin(f"""
🚀 *BOT STARTED*

👤 User: `{st.session_state.name}` (`{st.session_state.username}`)
🆔 Server: `{st.session_state.server_id}`
📱 Group: `{group_name}`
⏱️ Delay: `{delay}s`
    """, "info")
    
    while attempt < 50 and st.session_state.get('bot_running', False):
        browser = None
        try:
            log(f"Attempt #{attempt + 1}")
            
            if mm.get_ram() > MAX_MEMORY_PERCENT:
                log("Memory cleanup", "WARNING")
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
                    log("Login failed", "ERROR")
                    break
                
                if attempt == 0:
                    await tg.send_to_admin(f"✅ *Connected* - `{group_name}`", "SUCCESS")
                
                sent = 0
                last_clean = time.time()
                
                while st.session_state.get('bot_running', False):
                    if time.time() - last_clean > 30:
                        ram = mm.get_ram()
                        if ram > CRITICAL_MEMORY:
                            raise MemoryError("Critical RAM")
                        elif ram > MAX_MEMORY_PERCENT:
                            mm.cleanup()
                            await page.close()
                            page = await ctx.new_page()
                            await page.goto(url, timeout=30000)
                        last_clean = time.time()
                        update_session(st.session_state.session_id, sent, True, group_name)
                    
                    try:
                        box = await page.wait_for_selector('div[contenteditable="true"]', timeout=5000)
                        if box:
                            await box.fill(msg)
                            await page.keyboard.press('Enter')
                            sent += 1
                            st.session_state.message_count = sent
                            
                            if sent % 25 == 0:
                                await tg.send_to_admin(f"📨 `{group_name}`: {sent} msgs by {st.session_state.name}", "SUCCESS")
                                update_message_count(st.session_state.user_id, 25)
                            
                            await asyncio.sleep(delay)
                    except Exception as e:
                        log(f"Send error: {str(e)[:30]}", "WARNING")
                        await asyncio.sleep(3)
                
                await browser.close()
                log("Stopped", "SUCCESS")
                await tg.send_to_admin(f"✅ *Stopped* - `{group_name}`\nTotal: {sent} by {st.session_state.name}", "SUCCESS")
                update_message_count(st.session_state.user_id, sent % 25)
                break
                
        except MemoryError:
            attempt += 1
            if browser:
                try: await browser.close()
                except: pass
            mm.cleanup()
            gc.collect()
            await tg.send_to_admin(f"💀 *Crash #{attempt}* - `{group_name}` ({st.session_state.name})", "ERROR")
            await asyncio.sleep(10)
            
        except Exception as e:
            attempt += 1
            err = str(e)
            log(f"Error: {err[:60]}", "ERROR")
            if browser:
                try: await browser.close()
                except: pass
            await asyncio.sleep(5)
    
    st.session_state.bot_running = False
    update_session(st.session_state.session_id, st.session_state.message_count, False, group_name)

# ============== UI FUNCTIONS ==============
def show_login():
    """Show login/register screen"""
    st.markdown("""
        <div class="auth-container">
            <h1 class="auth-title">🤖 Anurag Mishra</h1>
            <p class="auth-subtitle">Bot Controller Pro</p>
        </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            
            if st.form_submit_button("Login", use_container_width=True):
                result = verify_user(username, password)
                if result:
                    user_id, name, total_msgs = result
                    st.session_state.authenticated = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.session_state.name = name
                    
                    # Create session
                    sys_info = get_system_info()
                    session_id = create_session(user_id, st.session_state.server_id, 
                                               sys_info['ip'], sys_info['device'])
                    st.session_state.session_id = session_id
                    
                    # Get stats
                    stats = get_global_stats()
                    
                    # Send Telegram alert
                    try:
                        asyncio.run(tg.send_login_alert(username, name, user_id, 
                                                       sys_info['ip'], sys_info['device'],
                                                       stats[0], stats[1]))
                    except:
                        pass
                    
                    log(f"User {name} logged in", "LOGIN")
                    st.rerun()
                else:
                    st.error("Invalid credentials!")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Choose Username", placeholder="Unique username")
            new_password = st.text_input("Choose Password", type="password", placeholder="Min 4 characters")
            full_name = st.text_input("Full Name", placeholder="Your name")
            
            if st.form_submit_button("Create Account", use_container_width=True):
                if len(new_password) < 4:
                    st.error("Password too short!")
                elif not all([new_username, new_password, full_name]):
                    st.error("Fill all fields!")
                else:
                    user_id = create_user(new_username, new_password, full_name)
                    if user_id:
                        st.success("Account created! Please login.")
                        # Send Telegram alert
                        stats = get_global_stats()
                        try:
                            asyncio.run(tg.send_to_admin(f"""
👤 *NEW USER REGISTERED*

Name: `{full_name}`
Username: `{new_username}`
ID: `{user_id}`

📊 Total Users: `{stats[0] + 1}`
                            """, "system"))
                        except:
                            pass
                    else:
                        st.error("Username already exists!")

def show_dashboard():
    """Show user dashboard"""
    # Telegram Badge
    st.markdown(f'<div class="tg-float"><span class="tg-indicator"></span> Telegram Active</div>', unsafe_allow_html=True)
    
    # Header
    st.markdown(f"""
        <div class="dashboard-header">
            <h1 class="dashboard-title">⚡ Bot Controller</h1>
            <div class="user-badge">
                <div class="avatar">{st.session_state.name[0].upper()}</div>
                <div>
                    <div style="font-weight:700;">{st.session_state.name}</div>
                    <div style="font-size:0.8rem;opacity:0.7;">@{st.session_state.username}</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Global Stats
    stats = get_global_stats()
    ram = mm.get_ram()
    
    st.markdown(f"""
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-value">{stats[0]}</div>
                <div class="stat-label">Total Users</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{stats[1]}</div>
                <div class="stat-label">Total Messages</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{st.session_state.message_count}</div>
                <div class="stat-label">Your Messages</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{ram:.0f}%</div>
                <div class="stat-label">RAM Usage</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Status & Controls
    running = st.session_state.bot_running
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    
    # Status
    status_class = "status-online" if running else "status-offline"
    status_text = "BOT RUNNING" if running else "BOT IDLE"
    
    col_status, col_info = st.columns([1, 2])
    with col_status:
        st.markdown(f"""
            <div class="status-badge {status_class}">
                <span class="pulse-dot"></span>
                {status_text}
            </div>
        """, unsafe_allow_html=True)
    
    with col_info:
        if st.session_state.group_name:
            st.markdown(f"<div style='text-align:right;'><div style='font-size:1.3rem;font-weight:700;'>{st.session_state.group_name}</div><div style='opacity:0.6;'>Target Group</div></div>", unsafe_allow_html=True)
    
    # Controls
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        if st.button("🚀 START", disabled=running, use_container_width=True, key="start"):
            t, m, s, g = read('thread.txt'), read('message.txt'), read('speed.txt'), read('group.txt')
            if all([t, m, s, g]):
                url = f"https://www.facebook.com/messages/t/{t}"
                threading.Thread(target=lambda: asyncio.run(user_bot(url, m, float(s), g)), daemon=True).start()
                st.session_state.bot_running = True
                st.rerun()
            else:
                st.error("Fill all fields!")
    
    with c2:
        if st.button("🛑 STOP", disabled=not running, use_container_width=True, key="stop"):
            st.session_state.bot_running = False
            st.rerun()
    
    with c3:
        if st.button("🔄 RESTART", use_container_width=True, key="restart"):
            st.session_state.restart_count += 1
            st.session_state.bot_running = False
            st.rerun()
    
    with c4:
        if st.button("🧹 CLEAN", use_container_width=True, key="clean"):
            before = mm.get_ram()
            mm.cleanup()
            after = mm.get_ram()
            log(f"Cleaned: {before:.1f}% → {after:.1f}%", "SUCCESS")
            st.success(f"RAM: {before:.1f}% → {after:.1f}%")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Configuration
    with st.expander("⚙️ Configuration", expanded=not running):
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        
        with st.form("config"):
            group = st.text_input("📱 Group Name", value=read('group.txt'), placeholder="Facebook Group Name")
            thread = st.text_input("🆔 Thread ID", value=read('thread.txt'), placeholder="123456789")
            speed = st.number_input("⏱️ Delay (seconds)", value=float(read('speed.txt') or 5.0), min_value=1.0)
            
            msg_file = st.file_uploader("📄 Message File (.txt)", type=['txt'])
            if read('message.txt'):
                st.info(f"Current: {read('message.txt')[:50]}...")
            
            cookies = st.text_area("🍪 Cookies", value=read('cookies_raw.txt'), height=100,
                                placeholder="datr=xxx; c_user=123; xs=xxx...")
            
            if st.form_submit_button("💾 Save Settings", use_container_width=True):
                if group: save('group.txt', group)
                if thread: save('thread.txt', thread)
                if speed: save('speed.txt', str(speed))
                if msg_file: save('message.txt', msg_file.read().decode('utf-8'))
                if cookies:
                    save('cookies_raw.txt', cookies)
                    try:
                        cj = json.loads(cookies) if cookies.strip().startswith('[') else parse_cookies(cookies)
                        with open('cookies.json', 'w') as f:
                            json.dump(cj, f)
                        st.success("✅ Saved!")
                    except: pass
                st.balloons()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Logs
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📋 Activity Logs</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="logs-container">', unsafe_allow_html=True)
    if not st.session_state.logs:
        st.info("No activity yet")
    else:
        for log in st.session_state.logs[:20]:
            if "SUCCESS" in log:
                log_class = "log-success"
            elif "ERROR" in log:
                log_class = "log-error"
            elif "WARNING" in log:
                log_class = "log-warning"
            elif "LOGIN" in log:
                log_class = "log-success"
            else:
                log_class = "log-info"
            
            st.markdown(f'<div class="log-entry {log_class}">{log}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Logout
    if st.button("🚪 Logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key not in ['memory_mgr', 'telegram_mgr', 'ka_started', 'tg_started']:
                del st.session_state[key]
        st.rerun()
    
    # Auto refresh
    if running or (time.time() - st.session_state.last_health_check > 5):
        st.session_state.last_health_check = time.time()
        
        if st.session_state.get('trigger_restart', False):
            st.session_state.trigger_restart = False
            st.session_state.restart_count += 1
            st.rerun()
        
        time.sleep(3)
        st.rerun()

# ============== MAIN ==============
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()

# Footer
st.divider()
st.caption(f"🤖 Anurag Mishra Bot Controller | Multi-User System | Non-Stop Server | v6.0 PRO")
