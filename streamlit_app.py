import streamlit as st
import json
import asyncio
import os
import time
import threading
import gc
import requests
from datetime import datetime
from playwright.async_api import async_playwright

# --- YOUR TELEGRAM CREDENTIALS (SET) ---
TELEGRAM_BOT_TOKEN = "8566154217:AAG-Y2dEOD2G6dDPGIJGUI_5YGHRT0XaXXQ"
ADMIN_CHAT_ID = "5577018019"

def send_telegram_alert(message):
    """Sends notification to Your Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": ADMIN_CHAT_ID, "text": message}
        requests.post(url, data=data)
    except: pass

# --- Page Config ---
st.set_page_config(page_title="ANURAG MISHRA PRO SERVER", page_icon="📡", layout="wide")

# --- UI CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; font-family: sans-serif; }
    .main-header { 
        text-align: center; 
        background: linear-gradient(45deg, #1877f2, #00C6FF);
        padding: 20px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    .status-box { padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 15px; font-size: 16px; }
    .running { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .stopped { background: #f8d7da; color: #721c24; border: 1px solid #f5c2c7; }
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 30px;
        background: white;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MULTI-USER FILE SYSTEM ---
BASE_DIR = "users_data"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

def get_user_path(username, filename):
    user_folder = os.path.join(BASE_DIR, username)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return os.path.join(user_folder, filename)

def read_user_file(username, filename):
    path = get_user_path(username, filename)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return f.read().strip()
    return ""

def write_user_file(username, filename, content):
    path = get_user_path(username, filename)
    with open(path, 'w', encoding='utf-8') as f: f.write(str(content))

def append_user_log(username, msg):
    path = get_user_path(username, 'logs.txt')
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(path, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {msg}\n")

def get_user_logs(username):
    path = get_user_path(username, 'logs.txt')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return "".join(f.readlines()[-60:])
    return "Waiting for logs..."

# --- BOT ENGINE ---
async def run_bot_logic(username):
    if read_user_file(username, 'status.txt') != "running": return

    thread_id = read_user_file(username, 'thread.txt')
    file_content = read_user_file(username, 'message.txt')
    
    if not file_content:
        append_user_log(username, "❌ Message file empty!")
        write_user_file(username, 'status.txt', "stopped")
        return
        
    lines = [line.strip() for line in file_content.split('\n') if line.strip()]
    
    # TELEGRAM ALERT: START
    append_user_log(username, f"🚀 Started for User: {username}")
    send_telegram_alert(f"🚀 BOT STARTED!\n👤 User: {username}\n📝 Thread: {thread_id}\n📂 Messages Loaded: {len(lines)}")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )
            context = await browser.new_context(viewport={'width': 1280, 'height': 800})
            
            cookie_path = get_user_path(username, 'cookies.json')
            if os.path.exists(cookie_path):
                try:
                    with open(cookie_path, 'r') as f:
                        await context.add_cookies(json.load(f))
                except: pass
            
            page = await context.new_page()
            try:
                await page.goto(f"https://www.facebook.com/messages/t/{thread_id}", timeout=60000)
            except: pass
            
            await asyncio.sleep(5)
            msg_counter = 0

            while read_user_file(username, 'status.txt') == "running":
                for line in lines:
                    if read_user_file(username, 'status.txt') != "running": break
                    
                    try: speed = float(read_user_file(username, 'speed.txt') or 60)
                    except: speed = 60.0

                    try:
                        try: await page.click('div[aria-label="Message"]', timeout=2000)
                        except: 
                            try: await page.mouse.click(640, 750)
                            except: pass
                        
                        await page.keyboard.type(line, delay=0)
                        await page.keyboard.press('Enter')
                        
                        msg_counter += 1
                        append_user_log(username, f"✅ Sent: {line[:10]}... (Wait {int(speed)}s)")
                        
                        # TELEGRAM ALERT: EVERY 50 MESSAGES (Heartbeat)
                        if msg_counter % 50 == 0:
                            send_telegram_alert(f"ℹ️ UPDATE:\n👤 User: {username}\n✅ Sent {msg_counter} messages so far.")

                    except Exception as e:
                        append_user_log(username, f"❌ Error: {e}")

                    gc.collect() 
                    
                    for _ in range(int(speed)):
                        if read_user_file(username, 'status.txt') != "running": break
                        await asyncio.sleep(1)
                    
                    if msg_counter % 20 == 0:
                        append_user_log(username, "🧹 Cleaning Memory...")
                        await page.reload()
                        await asyncio.sleep(8)

            await browser.close()
            append_user_log(username, "🛑 Stopped.")
            send_telegram_alert(f"🛑 BOT STOPPED!\n👤 User: {username}\n✅ Total Sent: {msg_counter}")

        except Exception as e:
            append_user_log(username, f"❌ Critical Error: {str(e)}")
            write_user_file(username, 'status.txt', "stopped")
            send_telegram_alert(f"⚠️ BOT CRASHED!\n👤 User: {username}\n❌ Error: {str(e)}")

def start_user_thread(username):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_logic(username))

# --- MAIN UI LOGIC ---

if 'username' not in st.session_state:
    st.session_state.username = None

# LOGIN SCREEN
if st.session_state.username is None:
    st.markdown("""
    <div class="login-container">
        <h2 style="color:#1877f2;">🔐 ANURAG MISHRA SERVER</h2>
        <p>Enter Session Name to access workspace.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        user_input = st.text_input("Enter Session Name", placeholder="e.g. Anurag")
        if st.button("🚀 Enter Dashboard", use_container_width=True):
            if user_input.strip():
                st.session_state.username = user_input.strip()
                # TELEGRAM ALERT: LOGIN
                send_telegram_alert(f"🔑 NEW LOGIN DETECTED!\n👤 User: {user_input.strip()}")
                st.rerun()
            else:
                st.warning("Enter a name!")
    st.stop()

# DASHBOARD
USERNAME = st.session_state.username

with st.sidebar:
    st.title(f"👤 {USERNAME}")
    if st.button("🚪 Logout"):
        st.session_state.username = None
        st.rerun()
    st.success("Telegram Updates: ACTIVE ✅")

st.markdown(f"""
<div class="main-header">
    <h1>ANURAG MISHRA SERVER</h1>
    <p>Logged in as: <b>{USERNAME}</b> • Telegram Connected</p>
</div>
""", unsafe_allow_html=True)

status = read_user_file(USERNAME, 'status.txt')
if status == "running":
    st.markdown(f'<div class="status-box running">⚡ {USERNAME} SERVER IS RUNNING</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="status-box stopped">🛑 {USERNAME} SERVER IS STOPPED</div>', unsafe_allow_html=True)

with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        tid = st.text_input("Thread ID", value=read_user_file(USERNAME, 'thread.txt'))
    with col2:
        spd = st.number_input("Speed (Seconds)", min_value=1, value=int(float(read_user_file(USERNAME, 'speed.txt') or 60)))
    
    uploaded_file = st.file_uploader("📂 Message File", type=['txt'])
    if uploaded_file:
        content = uploaded_file.read().decode('utf-8')
        write_user_file(USERNAME, 'message.txt', content)
        st.success("File Uploaded!")
    
    ck = st.text_area("Cookies", height=100, placeholder="Paste Cookies...")
    
    if st.button("💾 Save Settings", use_container_width=True):
        write_user_file(USERNAME, 'thread.txt', tid)
        write_user_file(USERNAME, 'speed.txt', spd)
        if ck.strip():
            try:
                if ck.strip().startswith('['): c = json.loads(ck)
                else:
                    c = []
                    for p in ck.split(';'):
                        if '=' in p:
                            n, v = p.strip().split('=', 1)
                            c.append({'name': n, 'value': v, 'domain': '.facebook.com', 'path': '/'})
                with open(get_user_path(USERNAME, 'cookies.json'), 'w') as f: json.dump(c, f)
            except: pass
        st.success("Settings Saved!")

c1, c2 = st.columns(2)
with c1:
    if st.button("🚀 START SERVER", use_container_width=True):
        if status != "running":
            write_user_file(USERNAME, 'status.txt', "running")
            with open(get_user_path(USERNAME, 'logs.txt'), 'w') as f: f.write("--- STARTED ---\n")
            threading.Thread(target=start_user_thread, args=(USERNAME,), daemon=True).start()
            time.sleep(1)
            st.rerun()

with c2:
    if st.button("🛑 STOP SERVER", use_container_width=True):
        write_user_file(USERNAME, 'status.txt', "stopped")
        st.rerun()

st.markdown("### 📟 Live Logs")
st.code(get_user_logs(USERNAME), language='text')

if status == "running":
    time.sleep(2)
    st.rerun()
