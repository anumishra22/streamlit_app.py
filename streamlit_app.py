import streamlit as st
import json
import asyncio
import os
import time
import threading
from datetime import datetime
from playwright.async_api import async_playwright

# --- Page Config ---
st.set_page_config(page_title="ANURAG MISHRA END TO END", page_icon="⚡", layout="centered")

# --- UI Styling ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; }
    .main-header { 
        text-align: center; 
        color: #0084ff; 
        font-size: 28px; 
        font-weight: bold; 
        margin-bottom: 20px;
        text-transform: uppercase;
    }
    .status-box { 
        padding: 15px; 
        border-radius: 8px; 
        text-align: center; 
        font-size: 18px; 
        font-weight: bold; 
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .running { background-color: #e7f3ff; color: #1877f2; border: 2px solid #1877f2; }
    .stopped { background-color: #ffebe9; color: #ff0000; border: 2px solid #ff0000; }
    
    /* Log Box Style */
    .log-container {
        background-color: #1c1e21;
        color: #00ff00;
        font-family: 'Courier New', monospace;
        padding: 15px;
        border-radius: 8px;
        height: 300px;
        overflow-y: scroll;
        font-size: 12px;
        border: 1px solid #333;
    }
    </style>
    """, unsafe_allow_html=True)

# --- File Database System ---
FILES = {
    'thread': 'thread.txt',
    'message': 'message.txt',
    'speed': 'speed.txt',
    'cookies': 'cookies.json',
    'status': 'status.txt',
    'logs': 'logs.txt'
}

def read_file(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return ""

def write_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(str(content))

def append_log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}\n"
    # Append to file
    try:
        with open(FILES['logs'], 'a', encoding='utf-8') as f:
            f.write(entry)
    except: pass

def get_logs():
    if os.path.exists(FILES['logs']):
        with open(FILES['logs'], 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return "".join(lines[-50:]) # Show last 50 lines
    return "Logs waiting..."

# --- Smart Cookie Fixer ---
def fix_cookies(raw_data):
    try:
        # 1. Try JSON
        if raw_data.strip().startswith('['):
            return json.loads(raw_data)
    except: pass
    
    # 2. Try Raw Text (key=value)
    try:
        cookies = []
        for part in raw_data.split(';'):
            if '=' in part:
                name, value = part.strip().split('=', 1)
                cookies.append({
                    'name': name,
                    'value': value,
                    'domain': '.facebook.com',
                    'path': '/'
                })
        return cookies
    except: return []

# --- MAIN BOT ENGINE ---
async def run_bot_logic():
    # Double check status before launching browser
    if read_file(FILES['status']) != "running": return

    thread_id = read_file(FILES['thread'])
    msg_content = read_file(FILES['message'])
    
    if not thread_id or not msg_content:
        append_log("❌ Error: Thread ID or Message is missing!")
        write_file(FILES['status'], "stopped")
        return

    append_log(f"🚀 Initializing Browser...")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )
            context = await browser.new_context(viewport={'width': 1280, 'height': 800})
            
            # Load Cookies
            if os.path.exists(FILES['cookies']):
                try:
                    with open(FILES['cookies'], 'r') as f:
                        cookies = json.load(f)
                        await context.add_cookies(cookies)
                except: append_log("⚠️ Cookie Load Error (Continuing anyway)")
            
            page = await context.new_page()
            
            try:
                await page.goto(f"https://www.facebook.com/messages/t/{thread_id}", timeout=60000)
            except: 
                append_log("⚠️ Timeout loading page (Retrying operations...)")

            append_log("✅ Thread Loaded. Starting Loop...")
            await asyncio.sleep(5)
            
            msg_count = 0
            
            # --- INFINITE LOOP ---
            while read_file(FILES['status']) == "running":
                # 1. READ SPEED FRESHLY (Dynamic Update)
                try:
                    speed_val = float(read_file(FILES['speed']) or 60.0)
                except:
                    speed_val = 60.0

                # 2. SEND MESSAGE
                try:
                    # Find box
                    try: await page.click('div[aria-label="Message"]', timeout=2000)
                    except: 
                        try: await page.mouse.click(640, 750)
                        except: pass
                    
                    # Type & Enter
                    await page.keyboard.type(msg_content, delay=0)
                    await page.keyboard.press('Enter')
                    
                    msg_count += 1
                    append_log(f"📨 Msg #{msg_count} Sent! Speed: {int(speed_val)}s")
                    
                except Exception as e:
                    append_log(f"⚠️ Send Failed: {e}")

                # 3. RAM CLEANER (Every 30 msgs)
                if msg_count > 0 and msg_count % 30 == 0:
                    append_log("♻️ Cleaning RAM (Refresh)...")
                    await page.reload()
                    await asyncio.sleep(8)

                # 4. STRICT WAIT (Breakable Loop)
                # This prevents "Machine Gun" effect and allows instant Stop
                for _ in range(int(speed_val)):
                    if read_file(FILES['status']) != "running":
                        append_log("🛑 Stop Signal Received!")
                        break
                    await asyncio.sleep(1)
            
            await browser.close()
            append_log("🔒 Browser Closed.")

        except Exception as e:
            append_log(f"❌ Critical Error: {str(e)}")
            write_file(FILES['status'], "stopped")

def start_background_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_logic())

# --- FRONTEND UI ---

st.markdown('<div class="main-header">ANURAG MISHRA END TO END</div>', unsafe_allow_html=True)

# 1. Status Display
current_status = read_file(FILES['status'])
if current_status == "running":
    st.markdown('<div class="status-box running">🔥 SYSTEM ACTIVE - RUNNING 🔥</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-box stopped">⛔ SYSTEM OFFLINE - STOPPED</div>', unsafe_allow_html=True)

# 2. Control Panel
with st.container(border=True):
    st.write("### 🛠️ Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        tid = st.text_input("Thread ID", value=read_file(FILES['thread']))
    with col2:
        # SPEED CONTROL INPUT
        spd = st.number_input("Delay (Seconds)", min_value=5, value=int(float(read_file(FILES['speed']) or 60)))
    
    msg = st.text_input("Message Text", value=read_file(FILES['message']))
    
    ck = st.text_area("Paste Cookies (JSON or Raw Text)", height=100)
    
    if st.button("✅ Save Configuration", use_container_width=True):
        write_file(FILES['thread'], tid)
        write_file(FILES['speed'], spd)
        write_file(FILES['message'], msg)
        
        if ck.strip():
            clean_cookies = fix_cookies(ck)
            if clean_cookies:
                with open(FILES['cookies'], 'w') as f:
                    json.dump(clean_cookies, f)
                st.success("Cookies Saved & Fixed!")
            else:
                st.error("Invalid Cookie Format!")
        
        st.success(f"Settings Saved! Speed set to {spd} seconds.")

# 3. Action Buttons
c1, c2 = st.columns(2)
with c1:
    if st.button("🚀 START SERVER", use_container_width=True):
        if current_status != "running":
            write_file(FILES['status'], "running")
            # Clear old logs
            with open(FILES['logs'], 'w') as f: f.write("--- NEW SESSION STARTED ---\n")
            
            # Start Thread
            threading.Thread(target=start_background_thread, daemon=True).start()
            time.sleep(1)
            st.rerun()

with c2:
    if st.button("🛑 STOP SERVER", use_container_width=True):
        write_file(FILES['status'], "stopped")
        st.rerun()

# 4. Live Logs
st.write("### 📟 Live Terminal Logs")
st.code(get_logs(), language='text')

# 5. Auto Refresh (Keeps UI alive)
if current_status == "running":
    time.sleep(2)
    st.rerun()
