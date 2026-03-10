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
from telegram.ext import Application, CommandHandler

# ============== CONFIGURATION ==============
TELEGRAM_BOT_TOKEN = "8567425809:AAE67VWXbpfHpWurWH6tMlN_pNLoTu6R60k"
TELEGRAM_CHAT_ID = "8567425809"

MAX_MEMORY_PERCENT = 75
CRITICAL_MEMORY = 85
MAX_LOGS = 30
AUTO_PING_INTERVAL = 180  # 3 minutes
# ===========================================

# --- Page Config ---
st.set_page_config(page_title="FB Bot Pro", page_icon="⚡", layout="wide")

# --- SMOOTH PROFESSIONAL CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .main { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    
    .container {
        max-width: 800px;
        margin: 0 auto;
        padding: 2rem;
    }
    
    /* Glass Card Effect */
    .glass-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        border: 1px solid rgba(255,255,255,0.2);
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 30px 80px rgba(0,0,0,0.4);
    }
    
    /* Header */
    .app-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .app-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #fff 0%, #e0e0e0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 40px rgba(255,255,255,0.3);
    }
    
    .app-subtitle {
        color: rgba(255,255,255,0.8);
        font-size: 1rem;
        font-weight: 500;
    }
    
    /* Status Badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 12px 24px;
        border-radius: 50px;
        font-weight: 700;
        font-size: 0.9rem;
        margin-bottom: 1.5rem;
    }
    
    .status-active {
        background: linear-gradient(135deg, #00b894, #00cec9);
        color: #fff;
        box-shadow: 0 10px 30px rgba(0,184,148,0.4);
        animation: pulse-green 2s infinite;
    }
    
    .status-idle {
        background: linear-gradient(135deg, #636e72, #b2bec3);
        color: #fff;
    }
    
    @keyframes pulse-green {
        0%, 100% { box-shadow: 0 10px 30px rgba(0,184,148,0.4); }
        50% { box-shadow: 0 10px 50px rgba(0,184,148,0.6); }
    }
    
    .pulse-dot {
        width: 8px;
        height: 8px;
        background: #fff;
        border-radius: 50%;
        animation: blink 1s infinite;
    }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    
    /* Input Fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #f8f9fa !important;
        border: 2px solid #e9ecef !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        font-size: 1rem !important;
        transition: all 0.3s !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 4px rgba(102,126,234,0.1) !important;
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 12px !important;
        height: 50px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.3s !important;
        border: none !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.2) !important;
    }
    
    .btn-primary {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important;
    }
    
    .btn-success {
        background: linear-gradient(135deg, #00b894, #00cec9) !important;
        color: white !important;
    }
    
    .btn-danger {
        background: linear-gradient(135deg, #ff7675, #d63031) !important;
        color: white !important;
    }
    
    .btn-warning {
        background: linear-gradient(135deg, #fdcb6e, #e17055) !important;
        color: #2d3436 !important;
    }
    
    /* Logs */
    .logs-container {
        background: #2d3436;
        border-radius: 16px;
        padding: 1.5rem;
        max-height: 350px;
        overflow-y: auto;
    }
    
    .log-entry {
        padding: 10px 14px;
        margin: 6px 0;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        border-left: 3px solid;
        animation: slideIn 0.3s ease;
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-10px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    .log-success { background: rgba(0,184,148,0.15); border-color: #00b894; color: #00cec9; }
    .log-error { background: rgba(214,48,49,0.15); border-color: #ff7675; color: #ff7675; }
    .log-info { background: rgba(116,185,255,0.15); border-color: #74b9ff; color: #74b9ff; }
    .log-warning { background: rgba(253,203,110,0.15); border-color: #fdcb6e; color: #fdcb6e; }
    
    /* Metrics */
    .metric-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .metric-box {
        background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05));
        backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 16px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        color: #fff;
        margin-bottom: 0.3rem;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: rgba(255,255,255,0.7);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Telegram Badge */
    .tg-badge {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, #0088cc, #00a8e8);
        color: white;
        padding: 12px 20px;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.9rem;
        box-shadow: 0 10px 30px rgba(0,136,204,0.4);
        display: flex;
        align-items: center;
        gap: 8px;
        z-index: 999;
    }
    
    .tg-indicator {
        width: 8px;
        height: 8px;
        background: #00ff88;
        border-radius: 50%;
        animation: blink 1s infinite;
    }
    
    /* Section Headers */
    .section-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #2d3436;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .section-title::before {
        content: '';
        width: 4px;
        height: 24px;
        background: linear-gradient(135deg, #667eea, #764ba2);
        border-radius: 2px;
    }
    </style>
""", unsafe_allow_html=True)

# ============== TELEGRAM MANAGER ==============
class TelegramManager:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = str(chat_id)
        self.app = None
        self.enabled = True
        self.last_alert = 0
        self.alert_cooldown = 30
        
    async def init(self):
        try:
            self.app = Application.builder().token(self.token).build()
            
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("status", self.cmd_status))
            self.app.add_handler(CommandHandler("startbot", self.cmd_start_bot))
            self.app.add_handler(CommandHandler("stopbot", self.cmd_stop_bot))
            self.app.add_handler(CommandHandler("restart", self.cmd_restart))
            self.app.add_handler(CommandHandler("logs", self.cmd_logs))
            self.app.add_handler(CommandHandler("help", self.cmd_help))
            
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)
            
            await self.send("🔥 *FB Bot Controller Started*\n\nCommands:\n/status - Check status\n/startbot - Start bot\n/stopbot - Stop bot\n/restart - Restart\n/logs - View logs\n/help - Help", "system")
            return True
        except Exception as e:
            print(f"Telegram error: {e}")
            return False
    
    async def cmd_start(self, update, context):
        if str(update.effective_chat.id) != self.chat_id:
            return
        await update.message.reply_text("✅ *Welcome!* Use /help for commands", parse_mode='Markdown')
    
    async def cmd_status(self, update, context):
        if str(update.effective_chat.id) != self.chat_id:
            return
        mem = psutil.virtual_memory()
        status = "🟢 RUNNING" if st.session_state.get('bot_running') else "🔴 STOPPED"
        await update.message.reply_text(f"""
📊 *STATUS*

{status}
💾 RAM: `{mem.percent}%`
🔄 Restarts: `{st.session_state.get('restart_count', 0)}`
💬 Messages: `{st.session_state.get('message_count', 0)}`
        """, parse_mode='Markdown')
    
    async def cmd_start_bot(self, update, context):
        if str(update.effective_chat.id) != self.chat_id:
            return
        st.session_state.tg_command = "START"
        await update.message.reply_text("🚀 *Starting bot...*", parse_mode='Markdown')
        await self.send("🚀 *Start command received*", "command")
    
    async def cmd_stop_bot(self, update, context):
        if str(update.effective_chat.id) != self.chat_id:
            return
        st.session_state.tg_command = "STOP"
        await update.message.reply_text("🛑 *Stopping bot...*", parse_mode='Markdown')
        await self.send("🛑 *Stop command received*", "command")
    
    async def cmd_restart(self, update, context):
        if str(update.effective_chat.id) != self.chat_id:
            return
        st.session_state.tg_command = "RESTART"
        await update.message.reply_text("🔄 *Restarting...*", parse_mode='Markdown')
        await self.send("🔄 *Restart command received*", "command")
    
    async def cmd_logs(self, update, context):
        if str(update.effective_chat.id) != self.chat_id:
            return
        logs = st.session_state.get('logs', [])[:10]
        text = "📋 *RECENT LOGS*\n\n" + "\n".join([f"`{l[:60]}`" for l in logs])
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_help(self, update, context):
        if str(update.effective_chat.id) != self.chat_id:
            return
        await update.message.reply_text("""
🤖 *COMMANDS*

/status - System status
/startbot - Start bot
/stopbot - Stop bot  
/restart - Restart app
/logs - View logs
/help - This help

⚡ Auto-healing enabled
        """, parse_mode='Markdown')
    
    async def send(self, text, msg_type="info"):
        if not self.enabled or not self.app:
            return
        
        now = time.time()
        if msg_type not in ["system", "command", "critical"] and now - self.last_alert < self.alert_cooldown:
            return
        self.last_alert = now
        
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Send error: {e}")

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
    colors = {"SUCCESS": "✅", "ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}
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

# ============== KEEP ALIVE (NO SLEEP) ==============
def keep_alive():
    """Prevent Streamlit sleep with self-ping"""
    while True:
        try:
            if mm.need_restart():
                st.session_state.trigger_restart = True
                try:
                    asyncio.run(tg.send(f"🔥 *Critical memory: {mm.get_ram()}%*\nAuto-restarting...", "critical"))
                except:
                    pass
            
            # Self ping to keep awake
            # Add your Streamlit URL here if deployed
            # requests.get("https://your-app.streamlit.app", timeout=10)
            
            time.sleep(AUTO_PING_INTERVAL)
        except:
            time.sleep(60)

if 'ka_started' not in st.session_state:
    threading.Thread(target=keep_alive, daemon=True).start()
    st.session_state.ka_started = True
    log("Keep-alive system active", "SUCCESS")

# ============== START TELEGRAM ==============
if 'tg_started' not in st.session_state:
    def start_tg():
        asyncio.run(tg.init())
    threading.Thread(target=start_tg, daemon=True).start()
    st.session_state.tg_started = True
    log("Telegram connected", "SUCCESS")

# ============== BOT LOGIC ==============
async def smart_bot(url, msg, delay):
    st.session_state.bot_running = True
    attempt = 0
    
    await tg.send(f"""
🚀 *BOT STARTED*

🎯 Target: `{url.split('/')[-1]}`
⏱️ Delay: `{delay}s`
💾 RAM: `{mm.get_ram()}%`
    """, "start")
    
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
                log("Loading Facebook...")
                await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                await asyncio.sleep(10)
                
                if "login" in page.url:
                    await tg.send("❌ *Login failed!* Check cookies", "error")
                    break
                
                if attempt == 0:
                    await tg.send("✅ *Connected!* Sending messages...", "success")
                
                sent = 0
                last_clean = time.time()
                last_status = time.time()
                
                while st.session_state.get('bot_running', False):
                    # Check Telegram commands
                    cmd = st.session_state.get('tg_command')
                    if cmd == "STOP":
                        st.session_state.tg_command = None
                        st.session_state.bot_running = False
                        await tg.send("🛑 *Stopped by Telegram*", "command")
                        break
                    
                    if cmd == "RESTART":
                        st.session_state.tg_command = None
                        raise Exception("Restart requested")
                    
                    # Memory check every 30 sec
                    if time.time() - last_clean > 30:
                        ram = mm.get_ram()
                        if ram > CRITICAL_MEMORY:
                            await tg.send(f"🔥 *Critical: {ram}% RAM!*", "critical")
                            raise MemoryError("Critical RAM")
                        elif ram > MAX_MEMORY_PERCENT:
                            log(f"High memory: {ram}%", "WARNING")
                            mm.cleanup()
                            await page.close()
                            page = await ctx.new_page()
                            await page.goto(url, timeout=30000)
                        last_clean = time.time()
                    
                    # Hourly update
                    if time.time() - last_status > 3600:
                        await tg.send(f"⏰ *Hourly update*\nMessages: `{sent}`\nRAM: `{mm.get_ram()}%`", "info")
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
                                await tg.send(f"📨 *Progress: {sent} messages*", "success")
                                log(f"Sent {sent} messages", "SUCCESS")
                            
                            await asyncio.sleep(delay)
                    except Exception as e:
                        log(f"Send error: {str(e)[:30]}", "WARNING")
                        await asyncio.sleep(3)
                
                await browser.close()
                log("Clean shutdown")
                await tg.send(f"✅ *Stopped*\nTotal: `{sent}` messages", "success")
                break
                
        except MemoryError:
            attempt += 1
            if browser:
                try: await browser.close()
                except: pass
            mm.cleanup()
            gc.collect()
            await tg.send(f"💀 *Crash #{attempt}*\nRestarting...", "critical")
            await asyncio.sleep(10)
            
        except Exception as e:
            attempt += 1
            err = str(e)
            log(f"Error: {err[:60]}", "ERROR")
            if browser:
                try: await browser.close()
                except: pass
            if attempt % 5 == 0:
                await tg.send(f"⚠️ *Error #{attempt}*\n`{err[:100]}`", "error")
            await asyncio.sleep(5)
    
    st.session_state.bot_running = False
    if attempt >= 50:
        await tg.send("🚫 *Max restarts reached!*", "critical")

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
            threading.Thread(target=lambda: asyncio.run(smart_bot(url, m, float(s))), daemon=True).start()
            st.session_state.bot_running = True
            log("Bot started via Telegram", "SUCCESS")
            st.rerun()
    
    elif cmd == "STOP" and st.session_state.bot_running:
        st.session_state.tg_command = None
        st.session_state.bot_running = False
        log("Bot stopped via Telegram", "SUCCESS")
        st.rerun()
    
    elif cmd == "RESTART":
        st.session_state.tg_command = None
        st.session_state.restart_count += 1
        st.session_state.bot_running = False
        log("Restart via Telegram", "SUCCESS")
        st.rerun()

# ============== UI ==============

# Telegram Badge
st.markdown(f'<div class="tg-badge"><span class="tg-indicator"></span> Telegram Active</div>', unsafe_allow_html=True)

# Header
st.markdown(f"""
    <div class="container">
        <div class="app-header">
            <h1 class="app-title">⚡ FB Bot Pro</h1>
            <p class="app-subtitle">Professional Automation Controller by Anurag Mishra</p>
        </div>
    </div>
""", unsafe_allow_html=True)

process_tg()

# Main Container
st.markdown('<div class="container">', unsafe_allow_html=True)

# Status & Metrics
running = st.session_state.bot_running
ram = mm.get_ram()

# Status Badge
status_class = "status-active" if running else "status-idle"
status_text = "BOT RUNNING" if running else "BOT IDLE"
status_icon = "🟢" if running else "⚪"

st.markdown(f"""
    <div style="text-align: center;">
        <div class="status-badge {status_class}">
            <span class="pulse-dot"></span>
            {status_icon} {status_text}
        </div>
    </div>
""", unsafe_allow_html=True)

# Metrics
st.markdown(f"""
    <div class="metric-row">
        <div class="metric-box">
            <div class="metric-value">{st.session_state.restart_count}</div>
            <div class="metric-label">Restarts</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{st.session_state.message_count}</div>
            <div class="metric-label">Messages</div>
        </div>
        <div class="metric-box">
            <div class="metric-value">{ram:.0f}%</div>
            <div class="metric-label">RAM</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Controls
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🎮 Control Panel</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🚀 START", disabled=running, use_container_width=True, key="start"):
        t, m, s = read('thread.txt'), read('message.txt'), read('speed.txt')
        if all([t, m, s]):
            url = f"https://www.facebook.com/messages/t/{t}"
            threading.Thread(target=lambda: asyncio.run(smart_bot(url, m, float(s))), daemon=True).start()
            st.session_state.bot_running = True
            st.rerun()
        else:
            st.error("Fill all fields!")

with col2:
    if st.button("🛑 STOP", disabled=not running, use_container_width=True, key="stop"):
        st.session_state.bot_running = False
        st.rerun()

with c3:
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
    st.markdown('<div class="section-title">Settings</div>', unsafe_allow_html=True)
    
    with st.form("config"):
        thread_id = st.text_input("📱 Thread ID", value=read('thread.txt'), placeholder="123456789")
        speed = st.number_input("⏱️ Delay (seconds)", value=float(read('speed.txt') or 5.0), min_value=1.0, step=1.0)
        
        msg_file = st.file_uploader("📄 Message File (.txt)", type=['txt'])
        if read('message.txt'):
            st.info(f"Current message: {read('message.txt')[:60]}...")
        
        cookies = st.text_area("🍪 Cookies", value=read('cookies_raw.txt'), height=120, 
                              placeholder="datr=xxx; c_user=123; xs=xxx...")
        
        if st.form_submit_button("💾 Save Settings", use_container_width=True):
            if thread_id: save('thread.txt', thread_id)
            if speed: save('speed.txt', str(speed))
            if msg_file: save('message.txt', msg_file.read().decode('utf-8'))
            if cookies:
                save('cookies_raw.txt', cookies)
                try:
                    cj = json.loads(cookies) if cookies.strip().startswith('[') else parse_cookies(cookies)
                    with open('cookies.json', 'w') as f:
                        json.dump(cj, f)
                    st.success("✅ Settings saved!")
                except Exception as e:
                    st.error(f"Cookie error: {e}")
            st.balloons()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Telegram Commands
with st.expander("📱 Telegram Commands"):
    st.markdown("""
    | Command | Description |
    |---------|-------------|
    | `/status` | Check system status |
    | `/startbot` | **Start** the bot |
    | `/stopbot` | **Stop** the bot |
    | `/restart` | **Restart** the app |
    | `/logs` | View recent logs |
    | `/help` | Show all commands |
    
    💬 **Chat ID:** `8567425809`
    """)

# Logs
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📋 Activity Logs</div>', unsafe_allow_html=True)

st.markdown('<div class="logs-container">', unsafe_allow_html=True)
if not st.session_state.logs:
    st.info("No activity yet. Start the bot to see logs here.")
else:
    for log in st.session_state.logs[:15]:
        if "SUCCESS" in log:
            log_class = "log-success"
        elif "ERROR" in log:
            log_class = "log-error"
        elif "WARNING" in log:
            log_class = "log-warning"
        else:
            log_class = "log-info"
        
        st.markdown(f'<div class="log-entry {log_class}">{log}</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # Close container

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
st.caption(f"⚡ FB Bot Pro | Auto-Healing | Telegram Control | No-Sleep Mode | by Anurag Mishra")
