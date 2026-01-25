import streamlit as st
import json
import asyncio
import os
import time
import threading
from datetime import datetime
from playwright.async_api import async_playwright

# --- Page Config ---
st.set_page_config(page_title="ANURAG MISHRA FILE UPLOADER", page_icon="📂", layout="centered")

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
        border-bottom: 2px solid #0084ff;
        padding-bottom: 10px;
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
    
    .log-container {
        background-color: #000;
        color: #00ff00;
        font-family: monospace;
        padding: 10px;
        border-radius: 8px;
        height: 250px;
        overflow-y: scroll;
        font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- File System ---
FILES = {
    'thread': 'thread.txt',
    'message': 'message.txt',
    'speed': 'speed.txt',
    'cookies': 'cookies.json',
    'status': 'status.txt',
    'logs': 'logs.txt'
}

# --- Helper Functions ---
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
    try:
        with open(FILES['logs'], 'a', encoding='utf-8') as f:
            f.write(entry)
    except: pass

def get_logs():
    if os.path.exists(FILES['logs']):
        with open(FILES['logs'], 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return "".join(lines[-50:]) 
    return "Waiting for logs..."

# --- Cookie Fixer ---
def fix_cookies(raw_data):
    try:
        # JSON Check
        if raw_data.strip().startswith('['):
            return json.loads(raw_data)
    except: pass
    
    # Raw Text Check
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
    if read_file(FILES['status']) != "running": return

    thread_id = read_file(FILES['thread'])
    msg_content = read_file(FILES['message'])
    
    if not thread_id or not msg_content:
        append_log("❌ Error: Thread ID or Message File Missing!")
        write_file(FILES['status'], "stopped")
        return

    append_log(f"🚀 Launching Browser...")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )
            context = await browser.new_context(viewport={'width': 1280, 'height': 800})
            
            if os.path.exists(FILES['cookies']):
                try:
                    with open(FILES['cookies'], 'r') as f:
                        await context.add_cookies(json.load(f))
                except: pass
            
            page = await context.new_page()
            
            try:
                await page.goto(f"https://www.facebook.com/messages/t/{thread_id}", timeout=60000)
            except: 
                append_log("⚠️ Timeout (Retrying...)")

            append_log("✅ Chat Open. Starting Messages...")
            await asyncio.sleep(5)
            
            msg_count = 0
            
            while read_file(FILES['status']) == "running":
                # --- STEP 1: READ SPEED FRESHLY ---
                try:
                    speed_val = float(read_file(FILES['speed']) or 60.0)
                except:
                    speed_val = 60.0

                # --- STEP 2: SEND MESSAGE ---
                try:
                    try: await page.click('div[aria-label="Message"]', timeout=2000)
                    except: 
                        try: await page.mouse.click(640, 750)
                        except: pass
                    
                    await page.keyboard.type(msg_content, delay=0)
                    await page.keyboard.press('Enter')
                    
                    msg_count += 1
                    append_log(f"📨 Msg #{msg_count} Sent! Waiting {int(speed_val)}s...")
                    
                except Exception as e:
                    append_log(f"⚠️ Send Failed: {e}")

                # --- STEP 3: RAM CLEANER ---
                if msg_count > 0 and msg_count % 30 == 0:
                    append_log("♻️ Cleaning RAM...")
                    await page.reload()
                    await asyncio.sleep(8)

                # --- STEP 4: STRICT SPEED CONTROL ---
                # This ensures instant stop and exact timing
                for _ in range(int(speed_val)):
                    if read_file(FILES['status']) != "running":
                        append_log("🛑 Stop Signal Received!")
                        break
                    await asyncio.sleep(1)
            
            await browser.close()
            append_log("🔒 Browser Closed.")

        except Exception as e:
            append_log(f"❌ Error: {str(e)}")
            write_file(FILES['status'], "stopped")

def start_background_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_logic())

# --- UI LAYOUT ---
st.markdown('<div class="main-header">ANURAG MISHRA (UPLOAD VERSION)</div>', unsafe_allow_html=True)

# Status
current_status = read_file(FILES['status'])
if current_status == "running":
    st.markdown('<div class="status-box running">🔥 BOT IS RUNNING 🔥</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-box stopped">⛔ BOT IS STOPPED</div>', unsafe_allow_html=True)

# Settings Form
with st.container(border=True):
    st.write("### ⚙️ Bot Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        tid = st.text_input("Thread ID", value=read_file(FILES['thread']))
    with col2:
        # SPEED INPUT
        spd = st.number_input("Speed (Seconds)", min_value=1, value=int(float(read_file(FILES['speed']) or 60)))
    
    # FILE UPLOADER FOR MESSAGE
    uploaded_file = st.file_uploader("📂 Upload Message File (.txt)", type=['txt'])
    if uploaded_file is not None:
        file_content = uploaded_file.read().decode("utf-8")
        write_file(FILES['message'], file_content)
        st.success(f"File Uploaded! Content: {file_content[:30]}...")
    elif read_file(FILES['message']):
        st.info(f"Saved Message: {read_file(FILES['message'])[:50]}...")
    
    ck = st.text_area("Paste Cookies (JSON/Text)", height=100)
    
    if st.button("✅ Save & Update Settings", use_container_width=True):
        write_file(FILES['thread'], tid)
        write_file(FILES['speed'], spd)
        
        if ck.strip():
            clean_cookies = fix_cookies(ck)
            if clean_cookies:
                with open(FILES['cookies'], 'w') as f:
                    json.dump(clean_cookies, f)
                st.success("Cookies Saved!")
            else:
                st.error("Invalid Cookies!")
        
        st.success(f"Settings Updated! Speed: {spd}s")

# Action Buttons
c1, c2 = st.columns(2)
with c1:
    if st.button("🚀 START BOT", use_container_width=True):
        if current_status != "running":
            write_file(FILES['status'], "running")
            with open(FILES['logs'], 'w') as f: f.write("--- STARTING ---\n")
            threading.Thread(target=start_background_thread, daemon=True).start()
            time.sleep(1)
            st.rerun()

with c2:
    if st.button("🛑 STOP BOT", use_container_width=True):
        write_file(FILES['status'], "stopped")
        st.rerun()

# Logs
st.write("### 📟 Live Logs")
st.code(get_logs(), language='text')

# Auto Refresh
if current_status == "running":
    time.sleep(2)
    st.rerun()
