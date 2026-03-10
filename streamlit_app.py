import streamlit as st
import json
import asyncio
import os
import time
import threading
from playwright.async_api import async_playwright

# --- Page Config ---
st.set_page_config(page_title="FB Thread Bot", page_icon="⚡", layout="wide")

# --- HTML/CSS for UI ---
st.markdown("""
    <style>
    .main { background: #f0f2f5; }
    .stApp { max-width: 600px; margin: 0 auto; padding-top: 2rem; }
    .stButton>button { width: 100%; font-weight: bold; border-radius: 8px; }
    .save-btn>div>button { background-color: #42b72a; color: white; border: none; }
    .start-btn>div>button { background-color: #1877f2; color: white; border: none; }
    .stop-btn>div>button { background-color: #f02849; color: white; border: none; }
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
    if len(st.session_state.logs) > 50:
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
    
    async with async_playwright() as p:
        try:
            launch_args = ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            
            # --- IMPORTANT FIX: Pointing to System Chromium ---
            browser = await p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",  # This is the key fix for Streamlit Cloud
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
            await asyncio.sleep(10)
            
            selectors = ['div[aria-label="Message"]', 'div[role="textbox"]', 'div[contenteditable="true"]', 'textarea']

            log_message("Bot is now sending messages...")
            while st.session_state.get('bot_running', False):
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
                    # Fallback click if selector fails
                    await page.mouse.click(640, 750)
                
                await page.keyboard.type(msg_content, delay=0)
                await page.keyboard.press('Enter')
                log_message(f"Message sent! Next in {delay}s")
                await asyncio.sleep(delay)
                
            await browser.close()
            log_message("Bot stopped.")
        except Exception as e:
            log_message(f"Error: {str(e)}")
            st.session_state.bot_running = False

# --- UI Layout ---
st.markdown("<h1 style='text-align: center; color: #1877f2;'>FB Bot Dashboard</h1>", unsafe_allow_html=True)

if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'logs' not in st.session_state:
    st.session_state.logs = []

# Status Indicator
if st.session_state.bot_running:
    st.markdown('<div class="status-box running">Bot is currently active ⚡</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-box idle">Bot is currently idle 💤</div>', unsafe_allow_html=True)

# --- Input Form ---
with st.form("bot_form"):
    st.markdown("### Configuration")
    thread_id = st.text_input("Thread ID", value=read_file('thread.txt'), placeholder="e.g. 864762722992677")
    
    message_file = st.file_uploader("Upload Message File (.txt)", type=['txt'])
    current_msg = read_file('message.txt')
    if current_msg:
        st.info(f"Current Message: {current_msg[:100]}...")
    
    speed = st.number_input("Speed (Seconds)", value=float(read_file('speed.txt') or 5.0), min_value=0.1, step=0.1)
    
    cookies_input = st.text_area("Cookies (String or JSON)", value=read_file('cookies_raw.txt'), height=150)

    st.markdown('<div class="save-btn">', unsafe_allow_html=True)
    submitted = st.form_submit_button("Save & Update Settings")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if submitted:
        if thread_id: save_file('thread.txt', thread_id)
        if speed: save_file('speed.txt', str(speed))
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
                st.toast("Cookies saved!")
            except Exception as e:
                st.error(f"Cookie error: {str(e)}")
        st.success("Settings updated!")

st.divider()

# --- Controls ---
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="start-btn">', unsafe_allow_html=True)
    if st.button("🚀 Launch Bot", use_container_width=True, disabled=st.session_state.bot_running):
        t_id = read_file('thread.txt')
        m_con = read_file('message.txt')
        s_val = read_file('speed.txt')
        
        if all([t_id, m_con, s_val]):
            url = f"https://www.facebook.com/messages/t/{t_id}"
            dly = float(s_val)
            # Running in a separate thread so UI doesn't freeze
            threading.Thread(target=lambda: asyncio.run(run_playwright_bot_loop(url, m_con, dly)), daemon=True).start()
            st.session_state.bot_running = True
            st.rerun()
        else:
            st.error("Please fill all fields first!")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
    if st.button("🛑 Terminate Bot", use_container_width=True, disabled=not st.session_state.bot_running):
        st.session_state.bot_running = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- Live Logs ---
st.subheader("Live Activity Logs")
log_placeholder = st.empty()
with log_placeholder.container():
    if not st.session_state.logs:
        st.write("No activity yet.")
    for log in st.session_state.logs:
        st.text(log)

# Auto-refresh UI when bot is running to show logs
if st.session_state.bot_running:
    time.sleep(2)
    st.rerun()
