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
    with open(FILES['logs'], 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {msg}\n")

def get_logs():
    if os.path.exists(FILES['logs']):
        with open(FILES['logs'], 'r', encoding='utf-8') as f:
            return f.read()
    return "Logs will appear here..."

# --- SMART COOKIE PARSER (Ye hai naya magic) ---
def parse_and_save_cookies(raw_data):
    try:
        # 1. Try JSON directly
        json_data = json.loads(raw_data)
        if isinstance(json_data, dict): # If single object, wrap in list
            json_data = [json_data]
        return json_data
    except:
        # 2. If JSON fails, try parsing "name=value; name=value" string
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
        append_log("❌ Data missing!")
        write_file(FILES['status'], "stopped")
        return

    append_log(f"🚀 Starting Browser...")
    
    async with async_playwright() as p:
        try:
            # Browser Launch
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
                        append_log(f"🍪 Loaded {len(cookies)} Cookies")
                except Exception as e: 
                    append_log(f"⚠️ Cookie Error: {e}")
            
            page = await context.new_page()
            try:
                await page.goto(f"https://www.facebook.com/messages/t/{thread_id}", timeout=60000)
            except:
                append_log("⚠️ Page timeout, but retrying...")
            
            append_log("✅ Checking Login...")
            await asyncio.sleep(5)

            msg_count = 0
            
            while read_file(FILES['status']) == "running":
                # Get dynamic speed
                try: speed = float(read_file(FILES['speed']) or 60)
                except: speed = 60.0

                # Type & Send
                try:
                    await page.click('div[aria-label="Message"]', timeout=3000)
                    await page.keyboard.type(msg_content)
                    await page.keyboard.press('Enter')
                    msg_count += 1
                    append_log(f"📨 Msg #{msg_count} Sent! Waiting {int(speed)}s")
                except:
                    # Fallback click
                    try: await page.mouse.click(640, 750)
                    except: pass
                
                # Smart Wait (Checks stop every second)
                for _ in range(int(speed)):
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

# --- UI ---
st.title("🔊 SUN LO BOT V3 (Auto-Cookie)")

# Sidebar
with st.sidebar:
    st.header("Settings")
    t_id = st.text_input("Thread ID", value=read_file(FILES['thread']))
    if st.button("Save ID"): write_file(FILES['thread'], t_id)
    
    sp = st.number_input("Speed (Sec)", min_value=1, value=int(float(read_file(FILES['speed']) or 60)))
    if st.button("Update Speed"): write_file(FILES['speed'], sp); st.success("Updated!")
    
    msg = st.text_input("Message", value=read_file(FILES['message']))
    if st.button("Save Msg"): write_file(FILES['message'], msg)
    
    # --- FIXED COOKIE SECTION ---
    cookies_raw = st.text_area("Paste Cookies (JSON or Raw Text)", value=read_file(FILES['cookies_raw']), height=150)
    if st.button("Save & Fix Cookies"):
        write_file(FILES['cookies_raw'], cookies_raw)
        
        # Auto-convert logic
        final_cookies = parse_and_save_cookies(cookies_raw)
        
        if final_cookies and len(final_cookies) > 0:
            with open(FILES['cookies'], 'w') as f:
                json.dump(final_cookies, f)
            st.success(f"✅ Success! {len(final_cookies)} Cookies saved.")
        else:
            st.warning("⚠️ Could not detect valid cookies. Check format.")

# Main
status = read_file(FILES['status'])
if status == "running":
    st.markdown('<div class="status-box running">🔥 RUNNING</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-box stopped">⛔ STOPPED</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)
if c1.button("🚀 START"):
    write_file(FILES['status'], "running")
    with open(FILES['logs'], 'w') as f: f.write("Starting...\n")
    threading.Thread(target=start_thread, daemon=True).start()
    st.rerun()
    
if c2.button("🛑 STOP"):
    write_file(FILES['status'], "stopped")
    st.rerun()

st.code(get_logs(), language='text')

if status == "running":
    time.sleep(2)
    st.rerun()
