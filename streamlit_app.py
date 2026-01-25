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
    log_entry = f"[{timestamp}] {msg}\n"
    with open(FILES['logs'], 'a', encoding='utf-8') as f:
        f.write(log_entry)
    # Keep logs manageable
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

# --- NEW: SMART COOKIE PARSER ---
def parse_and_save_cookies(raw_data):
    try:
        # 1. Try treating it as JSON first
        json_data = json.loads(raw_data)
        if isinstance(json_data, dict):
            json_data = [json_data] # Wrap single dict in list
        return json_data
    except:
        # 2. If JSON fails, try parsing "key=value; key2=value2" string
        cookies = []
        for pair in raw_data.split(';'):
            if '=' in pair:
                try:
                    key, value = pair.strip().split('=', 1)
                    cookies.append({
                        'name': key,
                        'value': value,
                        'domain': '.facebook.com',
                        'path': '/'
                    })
                except: pass
        return cookies

# --- Bot Logic ---
async def run_bot():
    if read_file(FILES['status']) != "running": return
    
    thread_id = read_file(FILES['thread'])
    msg_content = read_file(FILES['message'])
    
    if not thread_id or not msg_content:
        append_log("❌ Error: Thread ID or Message missing!")
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
            
            # Load Cookies Safely
            if os.path.exists(FILES['cookies']):
                try:
                    with open(FILES['cookies'], 'r') as f:
                        cookies_data = json.load(f)
                        if cookies_data:
                            await context.add_cookies(cookies_data)
                            append_log(f"🍪 Loaded {len(cookies_data)} Cookies")
                except Exception as e:
                    append_log(f"⚠️ Cookie Warning: {e}")
            
            page = await context.new_page()
            url_target = f"https://www.facebook.com/messages/t/{thread_id}"
            try:
                await page.goto(url_target, timeout=60000)
            except:
                append_log("⚠️ Timeout loading page (Continuing...)")

            append_log("✅ Page Loaded. Starting loop...")
            await asyncio.sleep(5)

            msg_count = 0
            
            while read_file(FILES['status']) == "running":
                # 1. Dynamic Speed
                try: current_speed = float(read_file(FILES['speed']) or 60)
                except: current_speed = 60.0
                
                # 2. Find & Click Box
                box_found = False
                try:
                    await page.click('div[aria-label="Message"]', timeout=3000)
                    box_found = True
                except:
                    try: 
                        await page.mouse.click(640, 750) # Coordinate fallback
                        box_found = True
                    except: pass
                
                # 3. Type & Send
                if box_found:
                    try:
                        await page.keyboard.type(msg_content, delay=0)
                        await page.keyboard.press('Enter')
                        msg_count += 1
                        append_log(f"📨 Msg #{msg_count} Sent! Waiting {int(current_speed)}s...")
                    except Exception as e:
                        append_log(f"⚠️ Send Error: {e}")
                else:
                    append_log("⚠️ Message box not found, retrying...")

                # 4. RAM Cleaner
                if msg_count > 0 and msg_count % 25 == 0:
                    append_log("♻️ Reloading to clean RAM...")
                    await page.reload()
                    await asyncio.sleep(5)

                # 5. Smart Wait (Check Stop Signal every second)
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
st.markdown("<h1 style='text-align: center;'>🔊 SUN LO BOT (Cookie Fix)</h1>", unsafe_allow_html=True)

# Sidebar for Controls
with st.sidebar:
    st.header("⚙️ Settings")
    t_id = st.text_input("Thread ID", value=read_file(FILES['thread']))
    if st.button("Save Thread ID"): write_file(FILES['thread'], t_id)
    
    sp = st.number_input("Speed (Seconds)", min_value=1, value=int(float(read_file(FILES['speed']) or 60)))
    if st.button("Update Speed"): 
        write_file(FILES['speed'], str(sp))
        st.success("Speed Updated!")
        
    m_file = st.file_uploader("Message File", type=['txt'])
    if m_file:
        write_file(FILES['message'], m_file.read().decode('utf-8'))
        st.success("Message Saved!")

    # --- UPDATED COOKIE SECTION ---
    c_raw = st.text_area("Paste Cookies (JSON or Raw Text)", value=read_file(FILES['cookies_raw']), height=150)
    if st.button("Save & Process Cookies"):
        write_file(FILES['cookies_raw'], c_raw)
        
        # Auto-convert logic
        final_cookies = parse_and_save_cookies(c_raw)
        
        if final_cookies and len(final_cookies) > 0:
            with open(FILES['cookies'], 'w') as f:
                json.dump(final_cookies, f)
            st.success(f"✅ Valid! {len(final_cookies)} cookies saved.")
        else:
            st.warning("⚠️ Could not detect cookies. Check format.")

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

st.subheader("📝 Live Logs")
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
