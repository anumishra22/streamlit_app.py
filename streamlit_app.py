import streamlit as st
import json
import asyncio
import os
import time
import threading
from datetime import datetime
from playwright.async_api import async_playwright

# --- Page Config ---
st.set_page_config(page_title="Simple FB Bot", page_icon="🤖", layout="centered")

# --- CSS for Clean UI ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; }
    .main-title { text-align: center; color: #1877f2; font-size: 30px; font-weight: bold; margin-bottom: 20px; }
    .status-box { padding: 20px; border-radius: 10px; text-align: center; font-size: 20px; font-weight: bold; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .running { background-color: #d4edda; color: #155724; border: 2px solid #c3e6cb; }
    .stopped { background-color: #f8d7da; color: #721c24; border: 2px solid #f5c6cb; }
    .log-container { background-color: #000; color: #00ff00; padding: 15px; border-radius: 8px; font-family: monospace; height: 250px; overflow-y: scroll; font-size: 13px; margin-top: 20px; }
    div[data-testid="stForm"] { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- File Handling ---
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
    with open(FILES['logs'], 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {msg}\n")
    # Keep logs short
    try:
        with open(FILES['logs'], 'r') as f: lines = f.readlines()
        if len(lines) > 50:
            with open(FILES['logs'], 'w') as f: f.writelines(lines[-50:])
    except: pass

def get_logs():
    if os.path.exists(FILES['logs']):
        with open(FILES['logs'], 'r') as f: return f.read()
    return "Logs will appear here..."

# --- Cookie Fixer ---
def parse_cookies(raw_data):
    try:
        # 1. Try JSON
        return json.loads(raw_data) if raw_data.startswith('[') else None
    except: pass
    
    try:
        # 2. Try Raw Text (key=value;)
        cookies = []
        for pair in raw_data.split(';'):
            if '=' in pair:
                k, v = pair.strip().split('=', 1)
                cookies.append({'name': k, 'value': v, 'domain': '.facebook.com', 'path': '/'})
        return cookies
    except: return []

# --- Bot Logic ---
async def run_bot():
    if read_file(FILES['status']) != "running": return

    thread_id = read_file(FILES['thread'])
    msg_content = read_file(FILES['message'])
    
    if not thread_id or not msg_content:
        append_log("❌ Data Missing! Please check Thread ID or Message.")
        write_file(FILES['status'], "stopped")
        return

    append_log(f"🚀 Starting Browser...")
    
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
                    with open(FILES['cookies']) as f:
                        cookies = json.load(f)
                        if isinstance(cookies, list): await context.add_cookies(cookies)
                except: append_log("⚠️ Cookie Error (Ignored)")
            
            page = await context.new_page()
            try:
                await page.goto(f"https://www.facebook.com/messages/t/{thread_id}", timeout=60000)
            except: append_log("⚠️ Page Load Timeout (Retrying...)")
            
            append_log("✅ Page Loaded. Starting...")
            await asyncio.sleep(5)
            
            count = 0
            while read_file(FILES['status']) == "running":
                # Read Speed Live
                try: sp = float(read_file(FILES['speed']) or 60)
                except: sp = 60.0
                
                try:
                    # Type & Send
                    await page.click('div[aria-label="Message"]', timeout=3000)
                    await page.keyboard.type(msg_content, delay=0)
                    await page.keyboard.press('Enter')
                    count += 1
                    append_log(f"📨 Msg #{count} Sent! Waiting {int(sp)}s...")
                except:
                    # Fallback
                    try: await page.mouse.click(640, 750)
                    except: pass
                
                # RAM Cleaner
                if count % 20 == 0:
                    append_log("♻️ Cleaning RAM...")
                    await page.reload()
                    await asyncio.sleep(5)

                # Smart Wait
                for _ in range(int(sp)):
                    if read_file(FILES['status']) != "running": break
                    await asyncio.sleep(1)

            await browser.close()
            append_log("🛑 Browser Closed.")
        except Exception as e:
            append_log(f"❌ Error: {e}")
            write_file(FILES['status'], "stopped")

def start_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot())

# --- UI Layout ---
st.markdown('<div class="main-title">ANURAG MISHRA BOT</div>', unsafe_allow_html=True)

# 1. Status Box
status = read_file(FILES['status'])
if status == "running":
    st.markdown('<div class="status-box running">🔥 BOT RUNNING 🔥</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-box stopped">⛔ BOT STOPPED</div>', unsafe_allow_html=True)

# 2. Main Controls Form
with st.form("settings_form"):
    st.write("### ⚙️ Bot Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        new_tid = st.text_input("Thread ID", value=read_file(FILES['thread']))
    with col2:
        new_speed = st.number_input("Speed (Seconds)", min_value=1, value=int(float(read_file(FILES['speed']) or 60)))
    
    new_msg = st.text_input("Message", value=read_file(FILES['message']))
    
    new_cookies = st.text_area("Paste Cookies (JSON or Text)", height=100)
    
    if st.form_submit_button("✅ Save & Update Settings"):
        write_file(FILES['thread'], new_tid)
        write_file(FILES['speed'], new_speed)
        write_file(FILES['message'], new_msg)
        
        # Smart Cookie Logic
        if new_cookies.strip():
            cleaned = parse_cookies(new_cookies)
            if cleaned:
                with open(FILES['cookies'], 'w') as f: json.dump(cleaned, f)
                st.success("Cookies Saved!")
            else:
                st.warning("Invalid Cookies Format!")
        st.success("Settings Updated!")

# 3. Action Buttons
c1, c2 = st.columns(2)
with c1:
    if st.button("🚀 START BOT", use_container_width=True):
        if status != "running":
            write_file(FILES['status'], "running")
            with open(FILES['logs'], 'w') as f: f.write("Starting...\n")
            threading.Thread(target=start_thread, daemon=True).start()
            st.rerun()

with c2:
    if st.button("🛑 STOP BOT", use_container_width=True):
        write_file(FILES['status'], "stopped")
        st.rerun()

# 4. Logs
st.write("### 📜 Live Activity")
st.code(get_logs(), language='text')

# Auto Refresh UI
if status == "running":
    time.sleep(2)
    st.rerun()
