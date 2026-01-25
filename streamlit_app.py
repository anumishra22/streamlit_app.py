import streamlit as st
import json
import asyncio
import os
import time
import threading
import gc  # Garbage Collector for RAM Cleaning
from datetime import datetime
from playwright.async_api import async_playwright

# --- Page Config ---
st.set_page_config(page_title="ANURAG MISHRA END TO END", page_icon="🚀", layout="centered")

# --- PREMIUM UI CSS ---
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #f0f2f5;
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* Header Style */
    .main-header { 
        text-align: center; 
        background: linear-gradient(90deg, #00C6FF 0%, #0072FF 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        margin-bottom: 25px;
    }
    .main-header h1 {
        margin: 0;
        font-size: 26px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .main-header p {
        margin: 5px 0 0;
        font-size: 14px;
        opacity: 0.9;
    }

    /* Status Boxes */
    .status-box { 
        padding: 15px; 
        border-radius: 12px; 
        text-align: center; 
        font-weight: bold; 
        font-size: 18px;
        margin-bottom: 20px;
        transition: transform 0.3s ease;
    }
    .running { 
        background-color: #d1e7dd; 
        color: #0f5132; 
        border: 2px solid #badbcc;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .stopped { 
        background-color: #f8d7da; 
        color: #842029; 
        border: 2px solid #f5c2c7;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }

    /* Logs Terminal */
    .log-container {
        background-color: #1e1e1e;
        color: #00ff9d;
        font-family: 'Courier New', monospace;
        padding: 15px;
        border-radius: 10px;
        height: 300px;
        overflow-y: scroll;
        font-size: 13px;
        border: 2px solid #333;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
    }

    /* WhatsApp Button */
    .wa-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #25D366;
        color: white !important;
        padding: 12px;
        border-radius: 50px;
        text-decoration: none;
        font-weight: bold;
        margin-top: 20px;
        box-shadow: 0 4px 10px rgba(37, 211, 102, 0.4);
        transition: all 0.3s;
    }
    .wa-btn:hover {
        background-color: #128C7E;
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(37, 211, 102, 0.6);
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
            return "".join(f.readlines()[-60:]) 
    return "🚀 Logs will appear here..."

# --- Main Bot Logic (Optimized) ---
async def run_bot_logic():
    if read_file(FILES['status']) != "running": return

    thread_id = read_file(FILES['thread'])
    file_content = read_file(FILES['message'])
    
    if not file_content:
        append_log("❌ Message file is empty!")
        write_file(FILES['status'], "stopped")
        return
        
    lines = [line.strip() for line in file_content.split('\n') if line.strip()]
    
    if not lines:
        append_log("❌ No valid lines found!")
        return

    append_log(f"🚀 Loaded {len(lines)} messages. Mode: One-by-One")

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
            except: append_log("⚠️ Timeout (Continuing...)")
            
            await asyncio.sleep(5)
            msg_counter = 0

            # --- INFINITE LOOP ---
            while read_file(FILES['status']) == "running":
                for line in lines:
                    if read_file(FILES['status']) != "running": break
                    
                    try: speed = float(read_file(FILES['speed']) or 60)
                    except: speed = 60.0

                    try:
                        # Find Box
                        try: await page.click('div[aria-label="Message"]', timeout=2000)
                        except: 
                            try: await page.mouse.click(640, 750)
                            except: pass
                        
                        # Type & Send
                        await page.keyboard.type(line, delay=0)
                        await page.keyboard.press('Enter')
                        
                        msg_counter += 1
                        append_log(f"✅ Sent: {line[:15]}... (Wait: {int(speed)}s)")
                        
                    except Exception as e:
                        append_log(f"❌ Error: {e}")

                    # --- RAM OPTIMIZATION STRATEGY ---
                    # 1. Force Garbage Collection
                    gc.collect() 
                    
                    # 2. Wait Loop (Check Stop every second)
                    for _ in range(int(speed)):
                        if read_file(FILES['status']) != "running": break
                        await asyncio.sleep(1)
                    
                    # 3. Heavy RAM Cleaning (Page Reload)
                    if msg_counter % 20 == 0:
                        append_log("🧹 Deep Cleaning RAM (Reloading)...")
                        await page.reload()
                        await asyncio.sleep(8)

            await browser.close()
            append_log("🛑 Process Stopped.")

        except Exception as e:
            append_log(f"❌ Critical Error: {str(e)}")
            write_file(FILES['status'], "stopped")

def start_background():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_logic())

# --- UI LAYOUT ---

# Header
st.markdown("""
<div class="main-header">
    <h1>ANURAG MISHRA END TO END</h1>
    <p>Premium Facebook Automation • Memory Optimized • Secure</p>
</div>
""", unsafe_allow_html=True)

# Status
status = read_file(FILES['status'])
if status == "running":
    st.markdown('<div class="status-box running">⚡ SYSTEM ACTIVE: RUNNING</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-box stopped">🛑 SYSTEM OFFLINE: STOPPED</div>', unsafe_allow_html=True)

# Settings Panel
with st.container(border=True):
    st.markdown("### ⚙️ Control Panel")
    col1, col2 = st.columns(2)
    with col1:
        tid = st.text_input("Target Thread ID", value=read_file(FILES['thread']), placeholder="e.g. 10000...")
    with col2:
        spd = st.number_input("Delay Speed (Seconds)", min_value=1, value=int(float(read_file(FILES['speed']) or 60)))
    
    uploaded_file = st.file_uploader("📂 Message File (One-by-One)", type=['txt'])
    if uploaded_file:
        content = uploaded_file.read().decode('utf-8')
        write_file(FILES['message'], content)
        st.success(f"✅ File Loaded: {len(content)} chars")
    
    ck = st.text_area("🍪 Cookies (Auto-Fixer)", height=100, placeholder="Paste your cookies here...")
    
    if st.button("💾 Save Configuration", use_container_width=True):
        write_file(FILES['thread'], tid)
        write_file(FILES['speed'], spd)
        
        # Cookie Logic
        if ck.strip():
            try:
                if ck.strip().startswith('['):
                    final_c = json.loads(ck)
                else:
                    final_c = []
                    for p in ck.split(';'):
                        if '=' in p:
                            n, v = p.strip().split('=', 1)
                            final_c.append({'name': n, 'value': v, 'domain': '.facebook.com', 'path': '/'})
                with open(FILES['cookies'], 'w') as f: json.dump(final_c, f)
                st.success("Cookies Saved & Fixed!")
            except: st.error("Invalid Cookies!")
        st.success("Settings Updated Successfully!")

# Control Buttons
c1, c2 = st.columns(2)
with c1:
    if st.button("🚀 START SERVER", use_container_width=True):
        if status != "running":
            write_file(FILES['status'], "running")
            with open(FILES['logs'], 'w') as f: f.write("--- NEW SESSION STARTED ---\n")
            threading.Thread(target=start_background, daemon=True).start()
            time.sleep(1)
            st.rerun()

with c2:
    if st.button("🛑 STOP SERVER", use_container_width=True):
        write_file(FILES['status'], "stopped")
        st.rerun()

# Logs
st.markdown("### 📟 Live Terminal")
st.code(get_logs(), language='text')

# Contact Button
st.markdown("""
<a href="https://wa.me/916394812128" target="_blank" class="wa-btn">
    📱 Contact Admin (Anurag Mishra) on WhatsApp
</a>
""", unsafe_allow_html=True)

# Auto Refresh
if status == "running":
    time.sleep(2)
    st.rerun()
