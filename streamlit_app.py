import streamlit as st
import json
import asyncio
import os
import time
import threading
from datetime import datetime
from playwright.async_api import async_playwright

# --- Page Config ---
st.set_page_config(page_title="One-By-One Sender", page_icon="📩", layout="centered")

# --- UI CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; }
    .header { text-align: center; color: #0084ff; padding: 10px; border-bottom: 2px solid #0084ff; }
    .status-box { padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; font-size: 18px; }
    .running { background-color: #e7f3ff; color: #1877f2; border: 2px solid #1877f2; }
    .stopped { background-color: #ffebe9; color: #ff0000; border: 2px solid #ff0000; }
    .log-box { background: black; color: #00ff00; padding: 10px; height: 300px; overflow-y: scroll; font-family: monospace; font-size: 12px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- Files ---
FILES = {
    'thread': 'thread.txt',
    'message': 'message.txt',
    'speed': 'speed.txt',
    'cookies': 'cookies.json',
    'status': 'status.txt',
    'logs': 'logs.txt'
}

# --- Helper Functions ---
def read_file(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f: return f.read().strip()
    return ""

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f: f.write(str(content))

def append_log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(FILES['logs'], 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {msg}\n")

def get_logs():
    if os.path.exists(FILES['logs']):
        with open(FILES['logs'], 'r', encoding='utf-8') as f:
            return "".join(f.readlines()[-60:]) # Show last 60 lines
    return "Logs waiting..."

# --- Main Bot Logic (Line-by-Line) ---
async def run_bot_logic():
    if read_file(FILES['status']) != "running": return

    thread_id = read_file(FILES['thread'])
    file_content = read_file(FILES['message'])
    
    # --- FIX: SPLIT CONTENT INTO LINES ---
    if not file_content:
        append_log("❌ Message file is empty!")
        write_file(FILES['status'], "stopped")
        return
        
    # Create a list of non-empty lines
    lines = [line.strip() for line in file_content.split('\n') if line.strip()]
    
    if not lines:
        append_log("❌ No valid lines found in file!")
        return

    append_log(f"🚀 Loaded {len(lines)} messages. Starting One-by-One...")

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",
                args=['--no-sandbox', '--disable-gpu']
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
            except: append_log("⚠️ Page load timeout (continuing)...")
            
            await asyncio.sleep(5)
            msg_counter = 0

            # --- INFINITE LOOP FOR MESSAGES ---
            while read_file(FILES['status']) == "running":
                for line in lines:
                    # Check stop signal before every single message
                    if read_file(FILES['status']) != "running": break
                    
                    # 1. Get Fresh Speed
                    try: speed = float(read_file(FILES['speed']) or 60)
                    except: speed = 60.0

                    # 2. Send ONE Line
                    try:
                        try: await page.click('div[aria-label="Message"]', timeout=2000)
                        except: 
                            try: await page.mouse.click(640, 750)
                            except: pass
                        
                        # Type the specific line only
                        await page.keyboard.type(line, delay=0)
                        await page.keyboard.press('Enter')
                        
                        msg_counter += 1
                        append_log(f"✅ Sent Line: {line[:20]}... (Wait: {int(speed)}s)")
                        
                    except Exception as e:
                        append_log(f"❌ Failed to send: {e}")

                    # 3. Wait for the exact Speed time
                    # Using a loop to allow instant stopping
                    for _ in range(int(speed)):
                        if read_file(FILES['status']) != "running": break
                        await asyncio.sleep(1)
                    
                    # 4. RAM Cleaning Check
                    if msg_counter % 30 == 0:
                        append_log("♻️ Cleaning Browser Memory...")
                        await page.reload()
                        await asyncio.sleep(8)

            await browser.close()
            append_log("🛑 Process Stopped.")

        except Exception as e:
            append_log(f"❌ Error: {str(e)}")
            write_file(FILES['status'], "stopped")

def start_background():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_logic())

# --- UI Layout ---
st.markdown('<h1 class="header">ANURAG MISHRA (ONE-BY-ONE)</h1>', unsafe_allow_html=True)

# Status
status = read_file(FILES['status'])
if status == "running":
    st.markdown('<div class="status-box running">🔥 RUNNING (Line by Line)</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-box stopped">⛔ STOPPED</div>', unsafe_allow_html=True)

# Settings
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        tid = st.text_input("Thread ID", value=read_file(FILES['thread']))
    with col2:
        spd = st.number_input("Speed (Seconds)", min_value=1, value=int(float(read_file(FILES['speed']) or 60)))
    
    uploaded_file = st.file_uploader("📂 Upload Message File (Txt)", type=['txt'])
    if uploaded_file:
        content = uploaded_file.read().decode('utf-8')
        write_file(FILES['message'], content)
        st.success(f"File Saved! Total characters: {len(content)}")
    
    # Cookie Input (Auto Fixer Inline)
    ck = st.text_area("Cookies", height=100, placeholder="Paste JSON or Text Cookies here")
    
    if st.button("💾 Save Settings", use_container_width=True):
        write_file(FILES['thread'], tid)
        write_file(FILES['speed'], spd)
        
        # Cookie Logic
        if ck.strip():
            try:
                # Try JSON
                if ck.strip().startswith('['):
                    final_c = json.loads(ck)
                else:
                    # Try Text
                    final_c = []
                    for p in ck.split(';'):
                        if '=' in p:
                            n, v = p.strip().split('=', 1)
                            final_c.append({'name': n, 'value': v, 'domain': '.facebook.com', 'path': '/'})
                
                with open(FILES['cookies'], 'w') as f: json.dump(final_c, f)
                st.success("Cookies Saved!")
            except: st.error("Invalid Cookies!")
        st.success(f"Speed set to {spd} seconds!")

# Controls
c1, c2 = st.columns(2)
with c1:
    if st.button("🚀 START LINE-BY-LINE", use_container_width=True):
        if status != "running":
            write_file(FILES['status'], "running")
            with open(FILES['logs'], 'w') as f: f.write("--- STARTED ---\n")
            threading.Thread(target=start_background, daemon=True).start()
            time.sleep(1)
            st.rerun()

with c2:
    if st.button("🛑 STOP", use_container_width=True):
        write_file(FILES['status'], "stopped")
        st.rerun()

# Logs
st.write("### 📜 Live Logs")
st.code(get_logs(), language='text')

if status == "running":
    time.sleep(2)
    st.rerun()
