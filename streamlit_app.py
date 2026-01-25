import streamlit as st
import json
import asyncio
import os
import time
import threading
from datetime import datetime
from playwright.async_api import async_playwright

# --- Page Config ---
st.set_page_config(page_title="Sun Lo Bot", page_icon="🔊", layout="wide")

# --- HTML/CSS ---
st.markdown("""
    <style>
    .main { background: #f0f2f5; }
    .stApp { max-width: 600px; margin: 0 auto; padding-top: 2rem; }
    .status-box { padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    .running { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .stopped { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .log-box { background: #000; color: #0f0; padding: 10px; border-radius: 5px; font-family: monospace; height: 200px; overflow-y: scroll; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- Files Management ---
FILES = {
    'thread': 'thread.txt',
    'message': 'message.txt',
    'speed': 'speed.txt',
    'cookies': 'cookies.json',
    'cookies_raw': 'cookies_raw.txt',
    'status': 'status.txt',  # Controls Start/Stop
    'logs': 'logs.txt'       # File based logging
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
    log_entry = f"[{timestamp}] {msg}\n"
    # Append to file
    with open(FILES['logs'], 'a', encoding='utf-8') as f:
        f.write(log_entry)
    # Keep only last 50 lines to save space
    try:
        with open(FILES['logs'], 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if len(lines) > 50:
            with open(FILES['logs'], 'w', encoding='utf-8') as f:
                f.writelines(lines[-50:])
    except: pass

def get_logs():
    if os.path.exists(FILES['logs']):
        with open(FILES['logs'], 'r', encoding='utf-8') as f:
            return f.read()
    return "No logs yet..."

# --- Clear Logs on Start ---
def clear_logs():
    with open(FILES['logs'], 'w', encoding='utf-8') as f:
        f.write("--- Bot Logs Started ---\n")

# --- Bot Logic ---
async def run_bot():
    url_base = "https://www.facebook.com/messages/t/"
    
    # Check Status immediately
    if read_file(FILES['status']) != "running":
        return

    thread_id = read_file(FILES['thread'])
    msg_content = read_file(FILES['message'])
    
    if not thread_id or not msg_content:
        append_log("❌ Error: Thread ID or Message missing!")
        write_file(FILES['status'], "stopped")
        return

    append_log(f"🚀 Launching Browser for Thread: {thread_id}")
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )
            context = await browser.new_context(viewport={'width': 1280, 'height': 800})
            
            if os.path.exists(FILES['cookies']):
                with open(FILES['cookies'], 'r') as f:
                    await context.add_cookies(json.load(f))
            
            page = await context.new_page()
            await page.goto(url_base + thread_id, timeout=60000)
            append_log("✅ Page Loaded. Checking input box...")
            await asyncio.sleep(5)

            msg_count = 0
            
            # --- MAIN LOOP ---
            while read_file(FILES['status']) == "running":
                # 1. DYNAMIC SPEED CHECK (Read speed from file continuously)
                try:
                    current_speed = float(read_file(FILES['speed']))
                except:
                    current_speed = 60.0
                
                # 2. FIND BOX
                try:
                    await page.click('div[aria-label="Message"]', timeout=2000)
                except:
                    try:
                        await page.mouse.click(640, 750)
                    except: pass
                
                # 3. TYPE & SEND
                try:
                    await page.keyboard.type(msg_content, delay=0)
                    await page.keyboard.press('Enter')
                    msg_count += 1
                    append_log(f"📨 Msg #{msg_count} Sent! Waiting {current_speed}s...")
                except Exception as e:
                    append_log(f"⚠️ Send Error: {e}")

                # 4. RAM CLEANER (Reload every 20 messages)
                if msg_count % 20 == 0:
                    append_log("♻️ Cleaning RAM...")
                    await page.reload()
                    await asyncio.sleep(5)

                # 5. SMART WAIT (Allows stopping in between wait time)
                # Instead of sleeping 60s at once, sleep in 1s chunks to check Stop status
                for _ in range(int(current_speed)):
                    if read_file(FILES['status']) != "running":
                        append_log("🛑 Stop Signal Received!")
                        break
                    await asyncio.sleep(1)
                
            await browser.close()
            append_log("🔒 Browser Closed.")
            
        except Exception as e:
            append_log(f"❌ Critical Error: {str(e)}")
            write_file(FILES['status'], "stopped")

def start_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

# --- UI Layout ---
st.markdown("<h1 style='text-align: center;'>🔊 SUN LO BOT (LIVE)</h1>", unsafe_allow_html=True)

# Sidebar for Controls
with st.sidebar:
    st.header("⚙️ Settings")
    t_id = st.text_input("Thread ID", value=read_file(FILES['thread']))
    if st.button("Save Thread ID"): write_file(FILES['thread'], t_id)
    
    sp = st.number_input("Speed (Seconds)", min_value=1, value=int(float(read_file(FILES['speed']) or 60)))
    if st.button("Update Speed (Live)"): 
        write_file(FILES['speed'], str(sp))
        st.success("Speed Updated!")
        
    m_file = st.file_uploader("Message File", type=['txt'])
    if m_file:
        write_file(FILES['message'], m_file.read().decode('utf-8'))
        st.success("Message Saved!")

    c_raw = st.text_area("Cookies", value=read_file(FILES['cookies_raw']))
    if st.button("Save Cookies"):
        write_file(FILES['cookies_raw'], c_raw)
        try:
            # Simple conversion logic
            import json
            # Assuming user pastes array or netscape format, basic try:
            if c_raw.strip().startswith('['):
                with open(FILES['cookies'], 'w') as f:
                    f.write(c_raw)
                st.success("JSON Cookies Saved!")
            else:
                st.error("Please paste valid JSON cookies (starts with [ )")
        except: pass

# Main Dashboard
current_status = read_file(FILES['status'])

if current_status == "running":
    st.markdown('<div class="status-box running">🔥 BOT IS RUNNING</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-box stopped">⛔ BOT IS STOPPED</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 START BOT", use_container_width=True):
        if current_status != "running":
            write_file(FILES['status'], "running")
            clear_logs()
            threading.Thread(target=start_thread, daemon=True).start()
            st.rerun()

with col2:
    if st.button("🛑 STOP BOT", use_container_width=True):
        write_file(FILES['status'], "stopped")
        st.rerun()

st.subheader("📝 Live Logs (Auto-Refresh)")
log_placeholder = st.empty()

# Create files if not exist
for f in FILES.values():
    if not os.path.exists(f):
        with open(f, 'w') as file: pass

# Live Log Updater
log_placeholder.code(get_logs())

if current_status == "running":
    time.sleep(2)
    st.rerun()
