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
from datetime import datetime
from playwright.async_api import async_playwright
from telegram import Bot

# ============== CONFIGURATION ==============
TELEGRAM_BOT_TOKEN = "8566154217:AAG-Y2dEOD2G6dDPGIJGUI_5YGHRT0XaXXQ"
TELEGRAM_ADMIN_ID = "8567425809"

MAX_MEMORY_PERCENT = 75
CRITICAL_MEMORY = 85
AUTO_PING_INTERVAL = 180  # 3 minutes
# ===========================================

# ============== TELEGRAM SENDER ==============
class TelegramAlert:
    def __init__(self, token, admin_id):
        self.token = token
        self.admin_id = admin_id
        self.bot = Bot(token)
        
    def send(self, text):
        """Send message to Telegram in background"""
        def send_msg():
            try:
                asyncio.run(self.bot.send_message(
                    chat_id=self.admin_id,
                    text=text,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                ))
            except Exception as e:
                print(f"Telegram error: {e}")
        
        threading.Thread(target=send_msg, daemon=True).start()
    
    def send_login(self, name, user_id, ip, total_users):
        """Send login alert"""
        text = f"""🔔 <b>NEW USER LOGIN</b>

👤 <b>{name}</b>
🆔 ID: <code>{user_id}</code>
📍 IP: <code>{ip}</code>
📊 Total Users: <b>{total_users}</b>
🕐 {datetime.now().strftime('%H:%M:%S')}"""
        self.send(text)
    
    def send_message_update(self, name, count, total_messages):
        """Send message update"""
        text = f"""📨 <b>MESSAGE UPDATE</b>

👤 <b>{name}</b>
📩 Sent: <b>{count}</b> messages
📊 Total Global: <b>{total_messages}</b>
🕐 {datetime.now().strftime('%H:%M:%S')}"""
        self.send(text)
    
    def send_bot_start(self, name, group, delay):
        """Send bot start alert"""
        text = f"""🚀 <b>BOT STARTED</b>

👤 <b>{name}</b>
📱 Group: <b>{group}</b>
⏱️ Delay: <b>{delay}s</b>
🕐 {datetime.now().strftime('%H:%M:%S')}"""
        self.send(text)
    
    def send_bot_stop(self, name, total_sent):
        """Send bot stop alert"""
        text = f"""🛑 <b>BOT STOPPED</b>

👤 <b>{name}</b>
📩 Total Sent: <b>{total_sent}</b>
🕐 {datetime.now().strftime('%H:%M:%S')}"""
        self.send(text)

# ============== SIMPLE STORAGE ==============
class UserStorage:
    def __init__(self):
        self.data_file = "user_data.json"
        self.users = self.load()
    
    def load(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def get_or_create(self, name):
        """Get existing user or create new"""
        # Create ID from name
        user_id = hashlib.md5(name.encode()).hexdigest()[:8].upper()
        
        if user_id not in self.users:
            # New user
            self.users[user_id] = {
                "name": name,
                "created_at": datetime.now().isoformat(),
                "total_messages": 0,
                "config": {
                    "thread_id": "",
                    "speed": "5.0",
                    "message": "",
                    "cookies": "",
                    "group_name": ""
                }
            }
            self.save()
            is_new = True
        else:
            is_new = False
        
        return user_id, self.users[user_id], is_new
    
    def update_config(self, user_id, key, value):
        """Update user config"""
        if user_id in self.users:
            self.users[user_id]["config"][key] = value
            self.save()
    
    def add_messages(self, user_id, count):
        """Add to message count"""
        if user_id in self.users:
            self.users[user_id]["total_messages"] += count
            self.save()
    
    def get_total_stats(self):
        """Get global stats"""
        total_users = len(self.users)
        total_messages = sum(u["total_messages"] for u in self.users.values())
        return total_users, total_messages

# ============== INIT ==============
if 'tg' not in st.session_state:
    st.session_state.tg = TelegramAlert(TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID)
    st.session_state.storage = UserStorage()
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.user_data = None
    st.session_state.bot_running = False
    st.session_state.message_count = 0
    st.session_state.logs = []

tg = st.session_state.tg
storage = st.session_state.storage

def log(msg):
    t = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.insert(0, f"[{t}] {msg}")
    if len(st.session_state.logs) > 30:
        st.session_state.logs.pop()

# ============== FILE HELPERS ==============
def save_file(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

def read_file(filename):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except:
        pass
    return ""

def parse_cookie_string(cookie_str):
    cookies = []
    pairs = cookie_str.split(';')
    for pair in pairs:
        if '=' in pair:
            try:
                name, value = pair.strip().split('=', 1)
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.facebook.com',
                    'path': '/'
                })
            except:
                continue
    return cookies

def get_ip():
    try:
        return requests.get('https://api.ipify.org?format=json', timeout=5).json().get('ip', 'Unknown')
    except:
        return 'Unknown'

# ============== MEMORY CLEANER ==============
class MemoryCleaner:
    def __init__(self):
        self.last_clean = 0
    
    def get_ram(self):
        return psutil.virtual_memory().percent
    
    def clean(self):
        gc.collect()
        gc.collect()
        return self.get_ram()
    
    def check_critical(self):
        ram = self.get_ram()
        if ram > CRITICAL_MEMORY:
            return True
        return False

if 'cleaner' not in st.session_state:
    st.session_state.cleaner = MemoryCleaner()

cleaner = st.session_state.cleaner

# ============== KEEP ALIVE ==============
def keep_alive():
    """Keep server awake"""
    while True:
        try:
            # Clean memory if needed
            if cleaner.check_critical():
                cleaner.clean()
            
            time.sleep(AUTO_PING_INTERVAL)
        except:
            time.sleep(60)

if 'ka_started' not in st.session_state:
    threading.Thread(target=keep_alive, daemon=True).start()
    st.session_state.ka_started = True

# ============== BOT LOGIC ==============
async def run_bot(url, msg, delay, group_name, user_name):
    st.session_state.bot_running = True
    st.session_state.message_count = 0
    
    # Notify Telegram
    tg.send_bot_start(user_name, group_name, delay)
    
    attempt = 0
    while attempt < 30 and st.session_state.get('bot_running'):
        browser = None
        try:
            # Check memory
            if cleaner.get_ram() > MAX_MEMORY_PERCENT:
                cleaner.clean()
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    executable_path="/usr/bin/chromium",
                    args=['--no-sandbox', '--disable-gpu', '--single-process', '--no-zygote', '--disable-images']
                )
                
                ctx = await browser.new_context(viewport={'width': 1280, 'height': 720})
                
                # Load cookies if exist
                cookie_file = f"cookies_{st.session_state.user_id}.json"
                if os.path.exists(cookie_file):
                    with open(cookie_file, 'r') as f:
                        c = json.load(f)
                        await ctx.add_cookies([x for x in c if x.get('name') in ['c_user', 'xs']][:2])
                
                page = await ctx.new_page()
                log(f"Loading {group_name}...")
                await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                await asyncio.sleep(10)
                
                if "login" in page.url:
                    log("Login failed - check cookies")
                    break
                
                if attempt == 0:
                    log(f"Connected to {group_name}")
                
                sent = 0
                last_update = time.time()
                
                while st.session_state.get('bot_running'):
                    # Memory check every 30 sec
                    if time.time() - last_update > 30:
                        if cleaner.check_critical():
                            raise MemoryError("Critical RAM")
                        last_update = time.time()
                    
                    try:
                        box = await page.wait_for_selector('div[contenteditable="true"]', timeout=5000)
                        if box:
                            await box.fill(msg)
                            await page.keyboard.press('Enter')
                            sent += 1
                            st.session_state.message_count = sent
                            
                            # Send update every 50 messages
                            if sent % 50 == 0:
                                total_users, total_msgs = storage.get_total_stats()
                                tg.send_message_update(user_name, sent, total_msgs + sent)
                                storage.add_messages(st.session_state.user_id, 50)
                            
                            await asyncio.sleep(delay)
                    except Exception as e:
                        log(f"Send error: {str(e)[:30]}")
                        await asyncio.sleep(3)
                
                await browser.close()
                
                # Final update
                if sent > 0:
                    remaining = sent % 50
                    if remaining > 0:
                        storage.add_messages(st.session_state.user_id, remaining)
                    tg.send_bot_stop(user_name, sent)
                    log(f"Stopped. Total: {sent}")
                break
                
        except MemoryError:
            attempt += 1
            if browser:
                try: await browser.close()
                except: pass
            cleaner.clean()
            log(f"Crash #{attempt}, restarting...")
            await asyncio.sleep(10)
            
        except Exception as e:
            attempt += 1
            if browser:
                try: await browser.close()
                except: pass
            log(f"Error: {str(e)[:50]}")
            await asyncio.sleep(5)
    
    st.session_state.bot_running = False

# ============== UI ==============
st.set_page_config(page_title="Bot Controller", page_icon="🤖", layout="centered")

# Simple CSS
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);}
    .login-box {
        max-width: 400px;
        margin: 100px auto;
        background: rgba(255,255,255,0.95);
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        text-align: center;
    }
    .title {
        font-size: 2.5rem;
        font-weight: 800;
        color: #333;
        margin-bottom: 10px;
    }
    .subtitle {
        color: #666;
        margin-bottom: 30px;
    }
    .stTextInput > div > div > input {
        font-size: 1.2rem !important;
        padding: 15px !important;
        border-radius: 10px !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        font-size: 1.2rem !important;
        padding: 15px 40px !important;
        border-radius: 10px !important;
    }
    .dashboard {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }
    .header {
        background: rgba(255,255,255,0.95);
        padding: 30px;
        border-radius: 20px;
        margin-bottom: 20px;
        text-align: center;
    }
    .user-name {
        font-size: 2rem;
        font-weight: 800;
        color: #333;
    }
    .stats {
        display: flex;
        justify-content: space-around;
        margin-top: 20px;
    }
    .stat {
        text-align: center;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: 800;
        color: #667eea;
    }
    .stat-label {
        color: #666;
        font-size: 0.9rem;
    }
    .card {
        background: rgba(255,255,255,0.95);
        padding: 25px;
        border-radius: 20px;
        margin-bottom: 20px;
    }
    .status {
        display: inline-block;
        padding: 10px 20px;
        border-radius: 50px;
        font-weight: 700;
    }
    .status-run {
        background: #00b894;
        color: white;
    }
    .status-stop {
        background: #b2bec3;
        color: #333;
    }
    .btn-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
        margin: 20px 0;
    }
    .log-box {
        background: #2d3436;
        color: #dfe6e9;
        padding: 20px;
        border-radius: 15px;
        font-family: monospace;
        font-size: 0.9rem;
        max-height: 300px;
        overflow-y: auto;
    }
    </style>
""", unsafe_allow_html=True)

# ============== LOGIN PAGE ==============
if not st.session_state.authenticated:
    st.markdown("""
        <div class="login-box">
            <div class="title">🤖 Bot Controller</div>
            <div class="subtitle">Enter your name to access your panel</div>
        </div>
    """, unsafe_allow_html=True)
    
    name = st.text_input("", placeholder="Your Name", key="login_name")
    
    if st.button("Enter Your Panel →", use_container_width=True):
        if name.strip():
            # Get or create user
            user_id, user_data, is_new = storage.get_or_create(name.strip())
            
            # Send Telegram alert
            total_users, total_msgs = storage.get_total_stats()
            ip = get_ip()
            tg.send_login(name.strip(), user_id, ip, total_users)
            
            # Set session
            st.session_state.authenticated = True
            st.session_state.user_id = user_id
            st.session_state.user_data = user_data
            st.session_state.name = name.strip()
            
            log(f"Login: {name}")
            st.rerun()
        else:
            st.error("Please enter your name!")

# ============== DASHBOARD ==============
else:
    user = st.session_state.user_data
    name = st.session_state.name
    config = user["config"]
    
    # Get stats
    total_users, total_msgs = storage.get_total_stats()
    
    st.markdown(f"""
        <div class="dashboard">
            <div class="header">
                <div class="user-name">👤 {name}</div>
                <div style="color:#666;margin-top:5px;">Your Personal Bot Panel</div>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">{user['total_messages'] + st.session_state.message_count}</div>
                        <div class="stat-label">Your Messages</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{total_users}</div>
                        <div class="stat-label">Total Users</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">{total_msgs}</div>
                        <div class="stat-label">Global Messages</div>
                    </div>
                </div>
            </div>
    """, unsafe_allow_html=True)
    
    # Status Card
    running = st.session_state.bot_running
    status_class = "status-run" if running else "status-stop"
    status_text = "🟢 RUNNING" if running else "⚪ STOPPED"
    
    st.markdown(f"""
        <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span class="status {status_class}">{status_text}</span>
                <span style="font-size:1.2rem;font-weight:600;">{config.get('group_name', 'No Group')}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 START BOT", disabled=running, use_container_width=True):
            # Load config
            thread = config.get('thread_id', '')
            msg = config.get('message', '')
            speed = float(config.get('speed', 5.0))
            group = config.get('group_name', 'Unknown')
            
            if thread and msg:
                url = f"https://www.facebook.com/messages/t/{thread}"
                threading.Thread(
                    target=lambda: asyncio.run(run_bot(url, msg, speed, group, name)),
                    daemon=True
                ).start()
                st.session_state.bot_running = True
                st.rerun()
            else:
                st.error("Please configure settings first!")
    
    with col2:
        if st.button("🛑 STOP BOT", disabled=not running, use_container_width=True):
            st.session_state.bot_running = False
            st.rerun()
    
    # Configuration
    with st.expander("⚙️ Settings", expanded=not running):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        with st.form("settings"):
            group_name = st.text_input("Group Name", value=config.get('group_name', ''))
            thread_id = st.text_input("Thread ID", value=config.get('thread_id', ''))
            speed = st.number_input("Delay (seconds)", value=float(config.get('speed', 5.0)), min_value=1.0)
            
            msg_file = st.file_uploader("Message File (.txt)", type=['txt'])
            if msg_file:
                msg_content = msg_file.read().decode('utf-8')
            else:
                msg_content = config.get('message', '')
                if msg_content:
                    st.info(f"Current message: {msg_content[:50]}...")
            
            cookies = st.text_area("Cookies", value=config.get('cookies', ''), height=100)
            
            if st.form_submit_button("💾 Save Settings"):
                storage.update_config(st.session_state.user_id, 'group_name', group_name)
                storage.update_config(st.session_state.user_id, 'thread_id', thread_id)
                storage.update_config(st.session_state.user_id, 'speed', str(speed))
                if msg_file:
                    storage.update_config(st.session_state.user_id, 'message', msg_content)
                if cookies:
                    storage.update_config(st.session_state.user_id, 'cookies', cookies)
                    # Save cookies to file
                    try:
                        cj = json.loads(cookies) if cookies.strip().startswith('[') else parse_cookie_string(cookies)
                        with open(f"cookies_{st.session_state.user_id}.json", 'w') as f:
                            json.dump(cj, f)
                    except: pass
                
                # Reload user data
                st.session_state.user_data = storage.users[st.session_state.user_id]
                st.success("Saved!")
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Logs
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📋 Activity Logs")
    st.markdown('<div class="log-box">', unsafe_allow_html=True)
    for log in st.session_state.logs[:15]:
        st.text(log)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Logout
    if st.button("🚪 Exit Panel"):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.user_data = None
        st.session_state.bot_running = False
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Auto refresh
if st.session_state.bot_running:
    time.sleep(3)
    st.rerun()
