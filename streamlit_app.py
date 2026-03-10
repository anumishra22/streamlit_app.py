import streamlit as st
import json
import asyncio
import os
import time
import threading
import requests
import gc
import psutil
from datetime import datetime
from playwright.async_api import async_playwright
from telegram.ext import Application, CommandHandler, ContextTypes
import hashlib

# ============== CONFIGURATION ==============
# HARDCODED - BAS YAHAN DAALO
TELEGRAM_BOT_TOKEN = "8567425809:AAE67VWXbpfHpWurWH6tMlN_pNLoTu6R60k"
TELEGRAM_CHAT_ID = "8567425809"  # Admin ID - Sirf yeh control kar sakta hai

# SERVER IDENTIFICATION
SERVER_ID = hashlib.md5(os.urandom(32)).hexdigest()[:8].upper()
SERVER_NAME = f"FB-BOT-{SERVER_ID}"
GROUP_NAME = "Unknown"

MAX_MEMORY_PERCENT = 75
CRITICAL_MEMORY = 85
MAX_LOGS = 25
RESTART_COOLDOWN = 30
# ===========================================

# --- Page Config ---
st.set_page_config(
    page_title=f"🤖 {SERVER_NAME}", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PRO CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .main { 
        background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 50%, #16213e 100%); 
        color: #ffffff;
    }
    
    .stApp { max-width: 100%; }
    
    /* Header */
    .server-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 20px;
        margin-bottom: 20px;
        box-shadow: 0 20px 60px rgba(102, 126, 234, 0.4);
    }
    
    .server-title {
        font-size: 2.5rem;
        font-weight: 900;
        color: white;
        text-shadow: 0 0 30px rgba(255,255,255,0.5);
        margin: 0;
    }
    
    .server-meta {
        display: flex;
        gap: 20px;
        margin-top: 10px;
        flex-wrap: wrap;
    }
    
    .meta-badge {
        background: rgba(255,255,255,0.2);
        padding: 8px 16px;
        border-radius: 50px;
        font-size: 0.85rem;
        font-weight: 600;
        backdrop-filter: blur(10px);
    }
    
    /* Status Cards */
    .status-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin: 20px 0;
    }
    
    .status-card {
        background: rgba(255,255,255,0.05);
        border-radius: 20px;
        padding: 25px;
        border: 1px solid rgba(255,255,255,0.1);
        backdrop-filter: blur(20px);
        transition: all 0.3s ease;
    }
    
    .status-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    }
    
    .status-running { border-left: 5px solid #00f5d4; }
    .status-idle { border-left: 5px solid #fee440; }
    .status-warning { border-left: 5px solid #f15bb5; }
    .status-critical { border-left: 5px solid #ef233c; animation: critical-pulse 1s infinite; }
    
    @keyframes critical-pulse {
        0%, 100% { box-shadow: 0 0 20px rgba(239, 35, 60, 0.5); }
        50% { box-shadow: 0 0 40px rgba(239, 35, 60, 0.8); }
    }
    
    .metric-value {
        font-size: 3rem;
        font-weight: 900;
        color: #00f5d4;
        margin: 10px 0;
    }
    
    .metric-label {
        color: #a0a0a0;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    /* Controls */
    .control-section {
        background: rgba(255,255,255,0.03);
        border-radius: 20px;
        padding: 30px;
        margin: 20px 0;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .control-btn {
        border-radius: 15px !important;
        height: 60px !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        transition: all 0.3s !important;
    }
    
    .btn-start { background: linear-gradient(135deg, #00f5d4, #00bbf9) !important; color: #000 !important; }
    .btn-stop { background: linear-gradient(135deg, #f15bb5, #ef233c) !important; }
    .btn-restart { background: linear-gradient(135deg, #fee440, #f48c06) !important; color: #000 !important; }
    .btn-clean { background: linear-gradient(135deg, #9b5de5, #f15bb5) !important; }
    
    .control-btn:hover {
        transform: scale(1.05);
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    
    /* Logs */
    .log-container {
        background: rgba(0,0,0,0.3);
        border-radius: 20px;
        padding: 20px;
        max-height: 400px;
        overflow-y: auto;
    }
    
    .log-entry {
        padding: 12px;
        margin: 8px 0;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        border-left: 4px solid;
        animation: slideIn 0.3s ease;
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    .log-success { background: rgba(0, 245, 212, 0.1); border-color: #00f5d4; color: #00f5d4; }
    .log-error { background: rgba(239, 35, 60, 0.1); border-color: #ef233c; color: #ef233c; }
    .log-warning { background: rgba(254, 228, 64, 0.1); border-color: #fee440; color: #fee440; }
    .log-info { background: rgba(155, 93, 229, 0.1); border-color: #9b5de5; color: #c77dff; }
    .log-telegram { background: rgba(0, 187, 249, 0.1); border-color: #00bbf9; color: #00bbf9; }
    
    /* Telegram Status */
    .tg-status {
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #0088cc, #00c6ff);
        padding: 15px 25px;
        border-radius: 50px;
        font-weight: 700;
        box-shadow: 0 10px 30px rgba(0, 136, 204, 0.4);
        z-index: 999;
    }
    
    /* Config Form */
    .config-card {
        background: rgba(255,255,255,0.05);
        border-radius: 20px;
        padding: 25px;
        margin: 15px 0;
    }
    
    .stTextInput > div > div > input, .stNumberInput > div > div > input {
        background: rgba(0,0,0,0.3) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 12px !important;
        color: white !important;
        padding: 15px !important;
    }
    
    .stTextArea > div > div > textarea {
        background: rgba(0,0,0,0.3) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 12px !important;
        color: white !important;
        font-family: 'Courier New', monospace !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); border-radius: 10px; }
    ::-webkit-scrollbar-thumb { background: #667eea; border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: #764ba2; }
    
    /* Animations */
    .pulse-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #00f5d4;
        margin-right: 10px;
        animation: dot-pulse 1s infinite;
    }
    
    @keyframes dot-pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.5); opacity: 0.5; }
    }
    </style>
""", unsafe_allow_html=True)

# ============== TELEGRAM MANAGER ==============
class TelegramManager:
    def __init__(self, token, chat_id):
        self.token = token
        self.admin_id = str(chat_id)
        self.app = None
        self.enabled = True
        self.last_alert = 0
        self.alert_cooldown = 30
        
    async def init(self):
        try:
            self.app = Application.builder().token(self.token).build()
            
            # Admin commands
            self.app.add_handler(CommandHandler("start", self.cmd_admin_start))
            self.app.add_handler(CommandHandler("servers", self.cmd_servers))
            self.app.add_handler(CommandHandler("status", self.cmd_status))
            self.app.add_handler(CommandHandler("startbot", self.cmd_start_bot))
            self.app.add_handler(CommandHandler("stopbot", self.cmd_stop_bot))
            self.app.add_handler(CommandHandler("restart", self.cmd_restart))
            self.app.add_handler(CommandHandler("restartall", self.cmd_restart_all))
            self.app.add_handler(CommandHandler("memory", self.cmd_memory))
            self.app.add_handler(CommandHandler("logs", self.cmd_logs))
            self.app.add_handler(CommandHandler("broadcast", self.cmd_broadcast))
            self.app.add_handler(CommandHandler("help", self.cmd_help))
            
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)
            
            await self.send_admin(f"""
🔥 *{SERVER_NAME} ONLINE*

🆔 Server: `{SERVER_ID}`
👤 Admin ID: `{self.admin_id}`

*Commands:*
/servers - List all servers
/status - This server status
/startbot - Start this bot
/stopbot - Stop this bot
/restart - Restart this server
/restartall - Restart all servers
/memory - RAM usage
/logs - Recent logs
/broadcast - Message all servers
/help - Help
            """, "system")
            
            return True
        except Exception as e:
            print(f"Telegram init error: {e}")
            return False
    
    def is_admin(self, update):
        user_id = str(update.effective_chat.id)
        if user_id != self.admin_id:
            asyncio.create_task(update.message.reply_text("⛔ *Unauthorized Access!*", parse_mode='Markdown'))
            return False
        return True
    
    # Admin Commands
    async def cmd_admin_start(self, update, context):
        if not self.is_admin(update):
            return
        await self.send_admin("✅ *Admin Verified!*\nUse /help for commands", "success")
    
    async def cmd_servers(self, update, context):
        if not self.is_admin(update):
            return
        await update.message.reply_text(f"""
🖥️ *ACTIVE SERVERS*

🆔 `{SERVER_NAME}`
📊 Status: {'🟢 Running' if st.session_state.get('bot_running') else '🔴 Idle'}
💾 RAM: `{psutil.virtual_memory().percent}%`
📨 Messages: `{st.session_state.get('message_count', 0)}`
        """, parse_mode='Markdown')
    
    async def cmd_status(self, update, context):
        if not self.is_admin(update):
            return
        mem = psutil.virtual_memory()
        status = "🟢 RUNNING" if st.session_state.get('bot_running') else "🔴 STOPPED"
        await update.message.reply_text(f"""
📊 *{SERVER_NAME} STATUS*

{status}
🆔 ID: `{SERVER_ID}`
💾 RAM: `{mem.percent}%` ({mem.used//1024//1024}MB / {mem.total//1024//1024}MB)
🔄 Restarts: `{st.session_state.get('restart_count', 0)}`
🧹 Cleanups: `{st.session_state.get('cleanup_count', 0)}`
📨 Messages: `{st.session_state.get('message_count', 0)}`
⏱️ Uptime: Running
        """, parse_mode='Markdown')
    
    async def cmd_start_bot(self, update, context):
        if not self.is_admin(update):
            return
        st.session_state.tg_command = "START"
        await update.message.reply_text(f"🚀 *Starting {SERVER_NAME}...*", parse_mode='Markdown')
        await self.send_admin(f"🚀 *Start command received for {SERVER_NAME}*", "command")
    
    async def cmd_stop_bot(self, update, context):
        if not self.is_admin(update):
            return
        st.session_state.tg_command = "STOP"
        await update.message.reply_text(f"🛑 *Stopping {SERVER_NAME}...*", parse_mode='Markdown')
        await self.send_admin(f"🛑 *Stop command received for {SERVER_NAME}*", "command")
    
    async def cmd_restart(self, update, context):
        if not self.is_admin(update):
            return
        st.session_state.tg_command = "RESTART"
        await update.message.reply_text(f"🔄 *Restarting {SERVER_NAME}...*", parse_mode='Markdown')
        await self.send_admin(f"🔄 *Restart command received for {SERVER_NAME}*", "command")
    
    async def cmd_restart_all(self, update, context):
        if not self.is_admin(update):
            return
        st.session_state.tg_command = "RESTART"
        await update.message.reply_text("🔄 *Restart ALL servers command sent!*", parse_mode='Markdown')
        await self.send_admin("🔄 *RESTART ALL command executed*", "command")
    
    async def cmd_memory(self, update, context):
        if not self.is_admin(update):
            return
        mem = psutil.virtual_memory()
        await update.message.reply_text(f"""
🧠 *{SERVER_NAME} MEMORY*

Used: `{mem.percent}%`
Available: `{mem.available//1024//1024} MB`
Total: `{mem.total//1024//1024} MB`
Free: `{mem.free//1024//1024} MB`
        """, parse_mode='Markdown')
    
    async def cmd_logs(self, update, context):
        if not self.is_admin(update):
            return
        logs = st.session_state.get('logs', [])[:10]
        text = f"📋 *{SERVER_NAME} LOGS*\n\n" + "\n".join([f"`{l[:70]}`" for l in logs])
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_broadcast(self, update, context):
        if not self.is_admin(update):
            return
        msg = ' '.join(context.args) if context.args else "Test broadcast"
        await self.send_admin(f"📢 *BROADCAST*\n\n{msg}", "broadcast")
        await update.message.reply_text("📢 *Broadcast sent!*", parse_mode='Markdown')
    
    async def cmd_help(self, update, context):
        if not self.is_admin(update):
            return
        await update.message.reply_text("""
🤖 *ADMIN COMMANDS*

/servers - List all active servers
/status - Current server status
/startbot - Start this server
/stopbot - Stop this server  
/restart - Restart this server
/restartall - Restart ALL servers
/memory - Memory usage
/logs - View recent logs
/broadcast [msg] - Send to all
/help - This help

⚡ You have FULL control!
        """, parse_mode='Markdown')
    
    async def send_admin(self, text, msg_type="info"):
        """Send message to admin with rate limiting"""
        if not self.enabled or not self.app:
            return
        
        now = time.time()
        if msg_type not in ["system", "command", "critical", "fatal"] and now - self.last_alert < self.alert_cooldown:
            return
        self.last_alert = now
        
        # Add server prefix
        full_text = f"🖥️ *{SERVER_NAME}*\n{text}"
        
        try:
            await self.app.bot.send_message(
                chat_id=self.admin_id,
                text=full_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Telegram send error: {e}")

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
        
        keep = ['bot_running', 'logs', 'memory_mgr', 'telegram_mgr', 
                'restart_count', 'cleanup_count', 'message_count', 
                'last_health_check', 'tg_command', 'ka_started', 'tg_started']
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
    st.session_state.telegram_mgr = TelegramManager(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    st.session_state.logs = []
    st.session_state.bot_running = False
    st.session_state.restart_count = 0
    st.session_state.cleanup_count = 0
    st.session_state.message_count = 0
    st.session_state.last_health_check = time.time()
    st.session_state.tg_command = None

mm = st.session_state.memory_mgr
tg = st.session_state.telegram_mgr

def log(msg, level="INFO"):
    t = datetime.now().strftime("%H:%M:%S")
    entry = f"[{t}] {level}: {msg}"
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

# ============== SELF-HEALING BOT ==============
async def super_bot(url, msg, delay):
    st.session_state.bot_running = True
    attempt = 0
    
    # Notify admin
    await tg.send_admin(f"""
🚀 *BOT STARTED*

🎯 Target: `{url.split('/')[-1]}`
⏱️ Delay: `{delay}s`
💾 Initial RAM: `{mm.get_ram()}%`
    """, "start")
    
    while attempt < 100 and st.session_state.get('bot_running', False):
        browser = None
        try:
            log(f"Launch attempt #{attempt + 1}")
            
            if mm.get_ram() > MAX_MEMORY_PERCENT:
                log("Pre-launch cleanup", "CLEAN")
                mm.cleanup()
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    executable_path="/usr/bin/chromium",
                    args=['--no-sandbox', '--disable-gpu', '--single-process', '--no-zygote', '--disable-images', '--disable-javascript']
                )
                
                ctx = await browser.new_context(viewport={'width': 1280, 'height': 720})
                
                if os.path.exists('cookies.json'):
                    with open('cookies.json', 'r') as f:
                        c = json.load(f)
                        essential = [x for x in c if x.get('name') in ['c_user', 'xs']]
                        await ctx.add_cookies(essential[:2])
                
                page = await ctx.new_page()
                log("Loading Facebook...")
                await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                await asyncio.sleep(10)
                
                if "login" in page.url:
                    await tg.send_admin("❌ *LOGIN FAILED!* Check cookies", "error")
                    break
                
                if attempt == 0:
                    await tg.send_admin("✅ *CONNECTED!* Sending messages...", "success")
                
                sent = 0
                last_clean = time.time()
                last_status = time.time()
                
                while st.session_state.get('bot_running', False):
                    # Check Telegram commands
                    cmd = st.session_state.get('tg_command')
                    if cmd == "STOP":
                        st.session_state.tg_command = None
                        st.session_state.bot_running = False
                        await tg.send_admin("🛑 *STOPPED by Telegram command*", "stop")
                        break
                    
                    if cmd == "RESTART":
                        st.session_state.tg_command = None
                        raise Exception("Admin restart requested")
                    
                    # Memory check every 30 sec
                    if time.time() - last_clean > 30:
                        ram = mm.get_ram()
                        if ram > CRITICAL_MEMORY:
                            await tg.send_admin(f"🔥 *CRITICAL MEMORY: {ram}%!*\nAuto-restarting...", "critical")
                            raise MemoryError("Critical RAM")
                        elif ram > MAX_MEMORY_PERCENT:
                            log(f"High memory: {ram}%", "WARN")
                            mm.cleanup()
                            await page.close()
                            page = await ctx.new_page()
                            await page.goto(url, timeout=30000)
                        last_clean = time.time()
                    
                    # Hourly update
                    if time.time() - last_status > 3600:
                        await tg.send_admin(f"""
⏰ *HOURLY REPORT*

📨 Messages: `{sent}`
💾 RAM: `{mm.get_ram()}%`
🔄 Attempts: `{attempt}`
                        """, "hourly")
                        last_status = time.time()
                    
                    # Send message
                    try:
                        box = await page.wait_for_selector('div[contenteditable="true"]', timeout=5000)
                        if box:
                            await box.fill(msg)
                            await page.keyboard.press('Enter')
                            sent += 1
                            st.session_state.message_count = sent
                            
                            if sent % 25 == 0:
                                await tg.send_admin(f"📨 *Progress: {sent} messages sent*", "progress")
                                log(f"Sent {sent} messages")
                            
                            await asyncio.sleep(delay)
                    except Exception as e:
                        log(f"Send error: {str(e)[:30]}", "WARN")
                        await asyncio.sleep(3)
                
                await browser.close()
                log("Clean shutdown")
                await tg.send_admin(f"✅ *BOT STOPPED*\nTotal messages: `{sent}`", "stop")
                break
                
        except MemoryError:
            attempt += 1
            if browser:
                try: await browser.close()
                except: pass
            mm.cleanup()
            gc.collect()
            await tg.send_admin(f"💀 *MEMORY CRASH #{attempt}*\nRestarting in 10s...", "critical")
            await asyncio.sleep(10)
            
        except Exception as e:
            attempt += 1
            err = str(e)
            log(f"Error: {err[:60]}", "ERROR")
            if browser:
                try: await browser.close()
                except: pass
            if attempt % 5 == 0:
                await tg.send_admin(f"⚠️ *ERROR #{attempt}*\n`{err[:100]}`", "error")
            await asyncio.sleep(5)
    
    st.session_state.bot_running = False
    if attempt >= 100:
        await tg.send_admin("🚫 *MAX RESTARTS!* Bot stopped. Check manually.", "fatal")

# ============== PROCESS TELEGRAM COMMANDS ==============
def process_tg():
    cmd = st.session_state.get('tg_command')
    if not cmd:
        return
    
    if cmd == "START" and not st.session_state.bot_running:
        st.session_state.tg_command = None
        t, m, s = read('thread.txt'), read('message.txt'), read('speed.txt')
        if all([t, m, s]):
            url = f"https://www.facebook.com/messages/t/{t}"
            threading.Thread(target=lambda: asyncio.run(super_bot(url, m, float(s))), daemon=True).start()
            st.session_state.bot_running = True
            log("Bot started via Telegram")
            st.rerun()
    
    elif cmd == "STOP" and st.session_state.bot_running:
        st.session_state.tg_command = None
        st.session_state.bot_running = False
        log("Bot stopped via Telegram")
        st.rerun()
    
    elif cmd == "RESTART":
        st.session_state.tg_command = None
        st.session_state.restart_count += 1
        st.session_state.bot_running = False
        log("Restart via Telegram", "RESTART")
        st.rerun()

# ============== KEEP ALIVE ==============
def keep_alive():
    while True:
        try:
            if mm.need_restart():
                st.session_state.trigger_restart = True
                try:
                    asyncio.run(tg.send_admin(f"🔥 *AUTO-RESTART: {mm.get_ram()}% RAM*", "critical"))
                except: pass
            
            time.sleep(300)
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

# ============== UI ==============
# Telegram Status Badge
st.markdown(f'<div class="tg-status">📱 Telegram: 🟢 Connected</div>', unsafe_allow_html=True)

# Server Header
st.markdown(f"""
    <div class="server-header">
        <h1 class="server-title">🤖 {SERVER_NAME}</h1>
        <div class="server-meta">
            <span class="meta-badge">🆔 {SERVER_ID}</span>
            <span class="meta-badge">{'🟢 ONLINE' if st.session_state.bot_running else '⚪ STANDBY'}</span>
            <span class="meta-badge">💾 RAM: {mm.get_ram()}%</span>
            <span class="meta-badge">📨 {st.session_state.message_count} msgs</span>
        </div>
    </div>
""", unsafe_allow_html=True)

process_tg()

# Status Grid
ram = mm.get_ram()
running = st.session_state.bot_running

st.markdown('<div class="status-grid">', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    status_class = "status-running" if running else "status-idle"
    status_text = "RUNNING" if running else "IDLE"
    st.markdown(f"""
        <div class="status-card {status_class}">
            <div class="metric-label">STATUS</div>
            <div class="metric-value" style="font-size: 1.5rem;">{status_text}</div>
            <div style="color: {'#00f5d4' if running else '#fee440'}">{'<span class="pulse-dot"></span>Active' if running else 'Standby'}</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    ram_color = "#ef233c" if ram > CRITICAL_MEMORY else "#f15bb5" if ram > MAX_MEMORY_PERCENT else "#00f5d4"
    st.markdown(f"""
        <div class="status-card {'status-critical' if ram > CRITICAL_MEMORY else 'status-warning' if ram > MAX_MEMORY_PERCENT else ''}">
            <div class="metric-label">MEMORY</div>
            <div class="metric-value" style="color: {ram_color}">{ram:.1f}%</div>
            <div style="color: {ram_color}">{'CRITICAL' if ram > CRITICAL_MEMORY else 'HIGH' if ram > MAX_MEMORY_PERCENT else 'NORMAL'}</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div class="status-card">
            <div class="metric-label">RESTARTS</div>
            <div class="metric-value" style="color: #9b5de5">{st.session_state.restart_count}</div>
            <div style="color: #c77dff">Auto-healing</div>
        </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
        <div class="status-card">
            <div class="metric-label">CLEANUPS</div>
            <div class="metric-value" style="color: #00bbf9">{st.session_state.cleanup_count}</div>
            <div style="color: #74b9ff">Memory mgmt</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Controls Section
st.markdown('<div class="control-section">', unsafe_allow_html=True)
st.subheader("🎮 Control Panel")

c1, c2, c3, c4 = st.columns(4)

with c1:
    if st.button("🚀 START", disabled=running, use_container_width=True, key="start_btn"):
        t, m, s = read('thread.txt'), read('message.txt'), read('speed.txt')
        if all([t, m, s]):
            url = f"https://www.facebook.com/messages/t/{t}"
            threading.Thread(target=lambda: asyncio.run(super_bot(url, m, float(s))), daemon=True).start()
            st.session_state.bot_running = True
            st.rerun()
        else:
            st.error("Fill config first!")

with c2:
    if st.button("🛑 STOP", disabled=not running, use_container_width=True, key="stop_btn"):
        st.session_state.bot_running = False
        st.rerun()

with c3:
    if st.button("🔄 RESTART", use_container_width=True, key="restart_btn"):
        st.session_state.restart_count += 1
        st.session_state.bot_running = False
        st.rerun()

with c4:
    if st.button("🧹 CLEAN", use_container_width=True, key="clean_btn"):
        before = mm.get_ram()
        mm.cleanup()
        after = mm.get_ram()
        log(f"Manual clean: {before:.1f}% → {after:.1f}%")
        st.success(f"Cleaned! {before:.1f}% → {after:.1f}%")

st.markdown('</div>', unsafe_allow_html=True)

# Configuration
with st.expander("⚙️ Configuration", expanded=not running):
    st.markdown('<div class="config-card">', unsafe_allow_html=True)
    
    with st.form("config"):
        c1, c2 = st.columns(2)
        
        with c1:
            tid = st.text_input("📱 Thread ID", value=read('thread.txt'), placeholder="123456789")
            st.text_input("🔐 Bot Token", value=TELEGRAM_BOT_TOKEN[:25]+"...", disabled=True, type="password")
        
        with c2:
            spd = st.number_input("⏱️ Delay (sec)", value=float(read('speed.txt') or 5.0), min_value=1.0, max_value=300.0)
            st.text_input("💬 Admin Chat ID", value=TELEGRAM_CHAT_ID, disabled=True)
        
        mf = st.file_uploader("📄 Message File (.txt)", type=['txt'])
        if read('message.txt'):
            st.info(f"💬 Current: {read('message.txt')[:80]}...")
        
        ck = st.text_area("🍪 Cookies (JSON/String)", value=read('cookies_raw.txt'), height=120, 
                         placeholder='datr=xxx; c_user=123; xs=xxx...')
        
        if st.form_submit_button("💾 SAVE CONFIGURATION", use_container_width=True):
            if tid: save('thread.txt', tid)
            if spd: save('speed.txt', str(spd))
            if mf: save('message.txt', mf.read().decode('utf-8'))
            if ck:
                save('cookies_raw.txt', ck)
                try:
                    cj = json.loads(ck) if ck.strip().startswith('[') else parse_cookies(ck)
                    with open('cookies.json', 'w') as f:
                        json.dump(cj, f)
                except: pass
            
            st.success("✅ Configuration saved!")
            st.balloons()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Telegram Commands Help
with st.expander("📱 Telegram Commands (Admin Only)"):
    st.markdown("""
    | Command | Description |
    |---------|-------------|
    | `/servers` | List all active servers |
    | `/status` | This server status |
    | `/startbot` | **Start** this server |
    | `/stopbot` | **Stop** this server |
    | `/restart` | **Restart** this server |
    | `/restartall` | **Restart ALL** servers |
    | `/memory` | RAM usage details |
    | `/logs` | Recent logs |
    | `/broadcast [msg]` | Message all servers |
    | `/help` | Show all commands |
    
    ⚡ **You are the ADMIN** - Full control from Telegram!
    """)

# Live Logs
st.markdown('<div class="control-section">', unsafe_allow_html=True)
st.subheader("📋 Live Activity Logs")

st.markdown('<div class="log-container">', unsafe_allow_html=True)
if not st.session_state.logs:
    st.info("No activity yet. Start the bot to see logs.")
else:
    for log in st.session_state.logs[:20]:
        if "CRIT" in log or "FATAL" in log:
            log_class, icon = "log-error", "🔴"
        elif "ERROR" in log:
            log_class, icon = "log-error", "⚠️"
        elif "WARN" in log:
            log_class, icon = "log-warning", "⚡"
        elif "CLEAN" in log:
            log_class, icon = "log-success", "🧹"
        elif "TELEGRAM" in log or "command" in log.lower():
            log_class, icon = "log-telegram", "📱"
        else:
            log_class, icon = "log-info", "ℹ️"
        
        st.markdown(f'<div class="log-entry {log_class}">{icon} {log}</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Auto refresh
if running or (time.time() - st.session_state.last_health_check > 5):
    st.session_state.last_health_check = time.time()
    
    if st.session_state.get('trigger_restart', False):
        st.session_state.trigger_restart = False
        st.session_state.restart_count += 1
        st.rerun()
    
    time.sleep(3)
    st.rerun()

# Footer
st.divider()
st.caption(f"🔒 {SERVER_NAME} | 🤖 Auto-Healing | 📱 Telegram Control | v4.0 PRO")
