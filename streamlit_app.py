
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
from telegram import Bot
import streamlit.components.v1 as components

# ============== CONFIGURATION ==============
TELEGRAM_BOT_TOKEN = "8566154217:AAG-Y2dEOD2G6dDPGIJGUI_5YGHRT0XaXXQ"
TELEGRAM_ADMIN_ID = "8567425809"  # Aapka ID

MAX_MEMORY_PERCENT = 75
CRITICAL_MEMORY = 85
MAX_LOGS = 30
AUTO_PING_INTERVAL = 180
# ===========================================

# ============== SIMPLE DATABASE ==============
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    password TEXT,
                    name TEXT,
                    created_at TEXT,
                    last_login TEXT,
                    total_messages INTEGER DEFAULT 0
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS logins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    username TEXT,
                    name TEXT,
                    ip TEXT,
                    device TEXT,
                    login_time TEXT
                )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    username TEXT,
                    count INTEGER,
                    timestamp TEXT
                )''')
    
    conn.commit()
    conn.close()

init_db()

# ============== TELEGRAM SENDER ==============
class TelegramAlert:
    def __init__(self, token, admin_id):
        self.token = token
        self.admin_id = admin_id
        self.bot = Bot(token)
        self.last_msg_time = 0
        self.cooldown = 15  # seconds between non-critical messages
        
    def send(self, text, priority="normal"):
        """Send message to Telegram with rate limiting"""
        try:
            now = time.time()
            
            # Rate limit for normal messages
            if priority == "normal" and now - self.last_msg_time < self.cooldown:
                return
            
            self.last_msg_time = now
            
            # Run in separate thread to not block
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
            
        except Exception as e:
            print(f"Send failed: {e}")
    
    def send_login(self, username, name, user_id, ip, device, total_users):
        """URGENT: Send login alert immediately"""
        text = f"""🔔 <b>NEW LOGIN ALERT</b>

👤 <b>{name}</b> (@{username})
🆔 ID: <code>{user_id}</code>
📍 IP: <code>{ip}</code>
💻 Device: {device}
🕐 Time: {datetime.now().strftime('%H:%M:%S')}

📊 Total Users: {total_users}"""
        
        # High priority - no cooldown
        try:
            threading.Thread(
                target=lambda: asyncio.run(self.bot.send_message(
                    chat_id=self.admin_id,
                    text=text,
                    parse_mode='HTML'
                )),
                daemon=True
            ).start()
        except Exception as e:
            print(f"Login alert error: {e}")
    
    def send_message_update(self, username, count, total_messages):
        """Send message count update"""
        text = f"""📨 <b>MESSAGE UPDATE</b>

👤 User: <b>{username}</b>
📩 Sent: <b>{count}</b> messages
📊 Total Global: <b>{total_messages}</b>
🕐 {datetime.now().strftime('%H:%M:%S')}"""
        self.send(text, "normal")
    
    def send_stats(self, total_users, total_messages, active_sessions, ram):
        """Send periodic stats"""
        text = f"""📊 <b>SYSTEM STATS</b>

👥 Users: <b>{total_users}</b>
💬 Messages: <b>{total_messages}</b>
🖥️ Active: <b>{active_sessions}</b>
🧠 RAM: <b>{ram}%</b>

⏰ {datetime.now().strftime('%H:%M:%S')}"""
        self.send(text, "normal")

# ============== DATABASE HELPERS ==============
def get_db():
    return sqlite3.connect('bot_data.db')

def create_user(username, password, name):
    conn = get_db()
    c = conn.cursor()
    user_id = "U" + hashlib.md5((username + str(time.time())).encode()).hexdigest()[:6].upper()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, 0)",
                (user_id, username, password, name, datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return user_id
    except:
        conn.close()
        return None

def verify_user(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name FROM users WHERE username=? AND password=?", (username, password))
    result = c.fetchone()
    if result:
        c.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now().isoformat(), result[0]))
        conn.commit()
    conn.close()
    return result

def record_login(user_id, username, name, ip, device):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO logins VALUES (NULL, ?, ?, ?, ?, ?, ?)",
              (user_id, username, name, ip, device, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT SUM(total_messages) FROM users")
    total_messages = c.fetchone()[0] or 0
    conn.close()
    return total_users, total_messages

def update_messages(user_id, count):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET total_messages = total_messages + ? WHERE id = ?", (count, user_id))
    c.execute("INSERT INTO messages VALUES (NULL, ?, ?, ?, ?)",
              (user_id, "batch", count, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ============== MEMORY MANAGER ==============
class MemoryManager:
    def __init__(self):
        self.last_restart = 0
        
    def get_ram(self):
        return psutil.virtual_memory().percent
    
    def cleanup(self):
        if 'logs' in st.session_state and len(st.session_state.logs) > MAX_LOGS:
            st.session_state.logs = st.session_state.logs[:MAX_LOGS]
        gc.collect()
        gc.collect()
        return self.get_ram()

# ============== INIT ==============
if 'tg' not in st.session_state:
    st.session_state.tg = TelegramAlert(TELEGRAM_BOT_TOKEN, TELEGRAM_ADMIN_ID)
    st.session_state.mm = MemoryManager()
    st.session_state.logs = []
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.name = None
    st.session_state.bot_running = False
    st.session_state.message_count = 0

tg = st.session_state.tg
mm = st.session_state.mm

def log(msg):
    t = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.insert(0, f"[{t}] {msg}")
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

def get_ip():
    try:
        return requests.get('https://api.ipify.org?format=json', timeout=5).json().get('ip', 'Unknown')
    except:
        return 'Unknown'

# ============== KEEP ALIVE ==============
def keep_alive():
    while True:
        try:
            # Send stats every 10 minutes
            if int(time.time()) % 600 == 0:
                users, msgs = get_stats()
                tg.send_stats(users, msgs, 0, mm.get_ram())
            time.sleep(AUTO_PING_INTERVAL)
        except:
            time.sleep(60)

if 'ka' not in st.session_state:
    threading.Thread(target=keep_alive, daemon=True).start()
    st.session_state.ka = True

# ============== BOT LOGIC ==============
async def run_bot(url, msg, delay, username):
    st.session_state.bot_running = True
    attempt = 0
    
    # Notify start
    users, total_msgs = get_stats()
    tg.send(f"""🚀 <b>BOT STARTED</b>
👤 User: <b>{username}</b>
📱 Target: {url.split('/')[-1]}
⏱️ Delay: {delay}s""", "normal")
    
    while attempt < 30 and st.session_state.get('bot_running'):
        browser = None
        try:
            if mm.get_ram() > MAX_MEMORY_PERCENT:
                mm.cleanup()
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    executable_path="/usr/bin/chromium",
                    args=['--no-sandbox', '--disable-gpu', '--single-process', '--no-zygote']
                )
                
                ctx = await browser.new_context(viewport={'width': 1280, 'height': 720})
                
                if os.path.exists('cookies.json'):
                    with open('cookies.json', 'r') as f:
                        c = json.load(f)
                        await ctx.add_cookies([x for x in c if x.get('name') in ['c_user', 'xs']][:2])
                
                page = await ctx.new_page()
                await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                await asyncio.sleep(10)
                
                if "login" in page.url:
                    log("Login failed")
                    break
                
                sent = 0
                last_update = time.time()
                
                while st.session_state.get('bot_running'):
                    if time.time() - last_update > 30:
                        if mm.get_ram() > CRITICAL_MEMORY:
                            raise MemoryError("Critical")
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
                                users, total = get_stats()
                                tg.send_message_update(username, sent, total + sent)
                                update_messages(st.session_state.user_id, 50)
                            
                            await asyncio.sleep(delay)
                    except:
                        await asyncio.sleep(3)
                
                await browser.close()
                
                # Final update
                if sent > 0:
                    update_messages(st.session_state.user_id, sent % 50)
                    tg.send(f"""✅ <b>BOT STOPPED</b>
👤 {username}
📩 Total: {sent} messages""", "normal")
                break
                
        except MemoryError:
            attempt += 1
            if browser:
                try: await browser.close()
                except: pass
            mm.cleanup()
            tg.send(f"💀 <b>Crash #{attempt}</b> - {username}", "normal")
            await asyncio.sleep(10)
            
        except Exception as e:
            attempt += 1
            if browser:
                try: await browser.close()
                except: pass
            await asyncio.sleep(5)
    
    st.session_state.bot_running = False

# ============== UI - SIMPLE ==============
st.set_page_config(page_title="Bot Controller", page_icon="🤖", layout="centered")

# Hide all Streamlit default
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp {background: #1a1a2e;}
    .stTextInput > div > div > input, .stNumberInput > div > div > input {
        background: #16213e !important;
        color: white !important;
        border-radius: 10px !important;
    }
    .stButton > button {
        border-radius: 10px !important;
        background: #0f3460 !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# ============== AUTH ==============
if not st.session_state.authenticated:
    st.title("🤖 Bot Login")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            
            if st.form_submit_button("Login"):
                result = verify_user(user, pwd)
                if result:
                    user_id, name = result
                    
                    # CRITICAL: Send login alert FIRST
                    ip = get_ip()
                    import platform
                    device = platform.system()
                    
                    # Record in DB
                    record_login(user_id, user, name, ip, device)
                    
                    # Get stats
                    total_users, total_msgs = get_stats()
                    
                    # ========== TELEGRAM LOGIN ALERT ==========
                    tg.send_login(user, name, user_id, ip, device, total_users)
                    
                    # Update session
                    st.session_state.authenticated = True
                    st.session_state.user_id = user_id
                    st.session_state.username = user
                    st.session_state.name = name
                    
                    log(f"Login: {name}")
                    st.rerun()
                else:
                    st.error("Wrong credentials!")
    
    with tab2:
        with st.form("register"):
            new_user = st.text_input("Username")
            new_pwd = st.text_input("Password", type="password")
            name = st.text_input("Full Name")
            
            if st.form_submit_button("Register"):
                if len(new_pwd) < 4:
                    st.error("Password too short!")
                else:
                    uid = create_user(new_user, new_pwd, name)
                    if uid:
                        # Notify new user
                        users, _ = get_stats()
                        tg.send(f"""👤 <b>NEW USER</b>
Name: {name}
User: @{new_user}
Total Users: {users}""", "normal")
                        st.success("Account created! Login now.")
                    else:
                        st.error("Username exists!")

# ============== DASHBOARD ==============
else:
    st.title(f"Welcome, {st.session_state.name}!")
    
    # Simple stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Your Messages", st.session_state.message_count)
    with col2:
        st.metric("RAM", f"{mm.get_ram():.0f}%")
    with col3:
        users, msgs = get_stats()
        st.metric("Total Users", users)
    
    # Status
    running = st.session_state.bot_running
    st.write(f"Status: {'🟢 RUNNING' if running else '🔴 STOPPED'}")
    
    # Controls
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 START", disabled=running):
            t, m, s = read('thread.txt'), read('message.txt'), read('speed.txt')
            if all([t, m, s]):
                url = f"https://www.facebook.com/messages/t/{t}"
                threading.Thread(
                    target=lambda: asyncio.run(run_bot(url, m, float(s), st.session_state.username)),
                    daemon=True
                ).start()
                st.session_state.bot_running = True
                st.rerun()
    
    with c2:
        if st.button("🛑 STOP", disabled=not running):
            st.session_state.bot_running = False
            st.rerun()
    
    # Config
    with st.expander("Settings"):
        with st.form("config"):
            thread = st.text_input("Thread ID", value=read('thread.txt'))
            speed = st.number_input("Delay", value=float(read('speed.txt') or 5.0), min_value=1.0)
            msg_file = st.file_uploader("Message File", type=['txt'])
            cookies = st.text_area("Cookies", value=read('cookies_raw.txt'), height=100)
            
            if st.form_submit_button("Save"):
                if thread: save('thread.txt', thread)
                if speed: save('speed.txt', str(speed))
                if msg_file: save('message.txt', msg_file.read().decode('utf-8'))
                if cookies:
                    save('cookies_raw.txt', cookies)
                    try:
                        cj = json.loads(cookies) if cookies.strip().startswith('[') else parse_cookies(cookies)
                        with open('cookies.json', 'w') as f:
                            json.dump(cj, f)
                    except: pass
                st.success("Saved!")
    
    # Logs
    st.subheader("Logs")
    for log in st.session_state.logs[:10]:
        st.text(log)
    
    # Logout
    if st.button("Logout"):
        for key in list(st.session_state.keys()):
            if key not in ['tg', 'mm', 'ka']:
                del st.session_state[key]
        st.rerun()

# Auto refresh
if st.session_state.bot_running:
    time.sleep(3)
    st.rerun()
