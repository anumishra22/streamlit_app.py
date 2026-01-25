import streamlit as st
import json
import asyncio
import os
import time
import threading
from playwright.async_api import async_playwright

# --- Page Config ---
st.set_page_config(page_title="ANURAG MISHRA HERE:)", page_icon="⚡", layout="wide")

# --- HTML/CSS for UI ---
st.markdown("""
    <style>
    .main { background: #f0f2f5; }
    .stApp { max-width: 600px; margin: 0 auto; padding-top: 2rem; }
    .stButton>button { width: 100%; font-weight: bold; border-radius: 8px; }
    
    /* Custom Button Styles */
    .save-btn>div>button { background-color: #42b72a; color: white; border: none; }
    .start-btn>div>button { background-color: #1877f2; color: white; border: none; }
    .stop-btn>div>button { background-color: #f02849; color: white; border: none; }
    
    /* WhatsApp Button Style */
    .wa-btn {
        display: block;
        width: 100%;
        background-color: #25D366;
        color: white;
        text-align: center;
        padding: 12px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: bold;
        font-family: sans-serif;
        margin-top: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    .wa-btn:hover { background-color: #128C7E; color: white; }

    .status-box { 
        padding: 15px; 
        border-radius: 8px; 
        text-align: center; 
        margin-bottom: 20px;
        font-weight: bold;
    }
    .running { background-color: #e7f3ff; color: #1877f2; border: 1px solid #1877f2; }
    .idle { background-color: #f0f2f5; color: #65676b; border: 1px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def save_file(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

def read_file(filename):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except Exception:
        pass
    return ""

def log_message(msg):
    timestamp = time.strftime("%H:%M:%S")
    new_log = f"[{timestamp}] {msg}"
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    st.session_state.logs.insert(0, new_log)
    # Limit logs to save RAM
    if len(st.session_state.logs) > 30:
        st.session_state.logs.pop()

def parse_cookie_string(cookie_str):
    cookies = []
    pairs = cookie_str.split(';')
    for pair in pairs:
        if '=' in pair:
            try:
                name, value = pair.strip().split('=', 1)
                cookies.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.facebook.com',
                    'path': '/'
                })
            except:
                continue
    return cookies

# --- Bot Logic ---
async def run_playwright_bot_loop(target_url, msg_content, delay):
    st.session_state.bot_running = True
    log_message("Starting browser...")
    msg_count = 0
    
    async with async_playwright() as p:
        try:
            launch_args = ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            
            # Pointing to System Chromium (Required for Streamlit Cloud)
            browser = await p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",
                args=launch_args
            )
            
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            if os.path.exists('cookies.json'):
                with open('cookies.json', 'r') as f:
                    await context.add_cookies(json.load(f))
            
            page = await context.new_page()
            log_message(f"Navigating to thread...")
            await page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(8)
            
            selectors = ['div[aria-label="Message"]', 'div[role="textbox"]', 'div[contenteditable="true"]', 'textarea']

            log_message(f"Bot Started! Speed: {delay} seconds")
            
            while st.session_state.get('bot_running', False):
                # --- RAM OPTIMIZATION STRATEGY ---
                # Every 25 messages, reload the page to clear DOM memory (RAM cleaning)
                if msg_count > 0 and msg_count % 25 == 0:
                    log_message("♻️ Cleaning RAM (Reloading Page)...")
                    await page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(5)
                    log_message("✅ RAM Cleaned. Resuming...")

                msg_box = None
                for sel in selectors:
                    try:
                        msg_box = await page.query_selector(sel)
                        if msg_box:
                            await msg_box.focus()
                            await msg_box.click()
                            break
                    except: continue
                
                if not msg_box:
                    # Fallback click
                    await page.mouse.click(640, 750)
                
                # Typing message
                await page.keyboard.type(msg_content, delay=0)
                await page.keyboard.press('Enter')
                
                msg_count += 1
                log_message(f"Msg #{msg_count} Sent! Waiting {delay}s...")
                
                # Exact delay control
                await asyncio.sleep(delay)
                
            await browser.close()
            log_message("Bot stopped.")
        except Exception as e:
            log_message(f"Error: {str(e)}")
            st.session_state.bot_running = False

# --- UI Layout ---
st.markdown("<h1 style='text-align: center; color: #1877f2;'>ANURAG MISHRA END TO END</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'>Secure FB Automator • Memory Optimized</p>", unsafe_allow_html=True)

if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'logs' not in st.session_state:
    st.session_state.logs = []

# Status Indicator
if st.session_state.bot_running:
    st.markdown('<div class="status-box running">🔥 Bot is RUNNING 🔥</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-box idle">😴 Bot is STOPPED</div>', unsafe_allow_html=True)

# --- Input Form ---
with st.form("bot_form"):
    st.markdown("### ⚙️ Dashboard Settings")
    
    # Thread ID
    thread_id = st.text_input("Target Thread ID", value=read_file('thread.txt'), placeholder="e.g. 100082...")
    
    # Message File
    message_file = st.file_uploader("Upload Message File (.txt)", type=['txt'])
    current_msg = read_file('message.txt')
    if current_msg:
        st.info(f"Loaded Message: {current_msg[:50]}...")
    
    # Speed Control
    st.markdown("**Select Speed (Seconds):**")
    speed = st.number_input("Time gap between messages", value=float(read_file('speed.txt') or 60.0), min_value=1.0, step=1.0)
    
    # Cookies
    cookies_input = st.text_area("Paste Cookies Here", value=read_file('cookies_raw.txt'), height=100)

    # Save Button
    st.markdown('<div class="save-btn">', unsafe_allow_html=True)
    submitted = st.form_submit_button("✅ Save Configuration")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if submitted:
        if thread_id: save_file('thread.txt', thread_id)
        save_file('speed.txt', str(speed)) # Explicitly save speed
        
        if message_file:
            msg_content = message_file.read().decode('utf-8')
            save_file('message.txt', msg_content)
            
        if cookies_input:
            save_file('cookies_raw.txt', cookies_input)
            try:
                cookies_raw = cookies_input.strip()
                if cookies_raw.startswith('['):
                    cookies_json = json.loads(cookies_raw)
                else:
                    cookies_json = parse_cookie_string(cookies_raw)
                with open('cookies.json', 'w') as f:
                    json.dump(cookies_json, f)
                st.toast("Settings Saved Successfully!")
            except Exception as e:
                st.error(f"Cookie Error: {str(e)}")
        else:
            st.toast("Settings Saved!")

st.divider()

# --- Controls ---
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="start-btn">', unsafe_allow_html=True)
    if st.button("🚀 START BOT", use_container_width=True, disabled=st.session_state.bot_running):
        t_id = read_file('thread.txt')
        m_con = read_file('message.txt')
        # Load speed freshly from file to ensure sync
        try:
            s_val = float(read_file('speed.txt'))
        except:
            s_val = 60.0
        
        if all([t_id, m_con]):
            url = f"https://www.facebook.com/messages/t/{t_id}"
            threading.Thread(target=lambda: asyncio.run(run_playwright_bot_loop(url, m_con, s_val)), daemon=True).start()
            st.session_state.bot_running = True
            st.rerun()
        else:
            st.error("Please Save Settings First!")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
    if st.button("🛑 STOP BOT", use_container_width=True, disabled=not st.session_state.bot_running):
        st.session_state.bot_running = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- Live Logs ---
st.subheader("📝 Activity Logs")
log_placeholder = st.empty()
with log_placeholder.container():
    if not st.session_state.logs:
        st.write("Waiting for action...")
    for log in st.session_state.logs:
        st.text(log)

# --- CONTACT ADMIN BUTTON ---
st.markdown("""
    <a href="https://wa.me/916394812128" target="_blank" class="wa-btn">
        📞 Contact Admin (Anurag Mishra) on WhatsApp
    </a>
""", unsafe_allow_html=True)

# Auto-refresh UI
if st.session_state.bot_running:
    time.sleep(2)
    st.rerun()
