from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import asyncio
import os
import threading
from playwright.async_api import async_playwright
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Global State ---
bot_running = False
bot_logs = []  # लाइव लॉग्स यहाँ सेव होंगे

def add_log(message):
    timestamp = time.strftime("%H:%M:%S")
    bot_logs.append(f"[{timestamp}] {message}")
    if len(bot_logs) > 50:  # सिर्फ आखिरी 50 लाइन्स रखें
        bot_logs.pop(0)

# --- Helper Functions ---
def save_file(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

def read_file(filename):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except:
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    global bot_running
    if request.method == 'POST':
        thread = request.form.get('thread')
        speed = request.form.get('speed')
        cookies_raw = request.form.get('cookies')
        
        # Files Handling
        if 'message_file' in request.files:
            file = request.files['message_file']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'message.txt')
                file.save(filepath)
                # Sync content
                file.seek(0)
                save_file('message.txt', file.read().decode('utf-8'))
                add_log("Message file updated.")

        if thread: 
            save_file('thread.txt', thread)
            add_log(f"Thread ID updated: {thread}")
        if speed: 
            save_file('speed.txt', speed)
        
        if cookies_raw:
            save_file('cookies.txt', cookies_raw) # Raw save for simplicity
            try:
                # Convert logic handled in bot loop
                pass 
            except:
                pass
            add_log("Cookies updated.")

        return redirect(url_for('index'))

    # Load current values
    thread = read_file('thread.txt') or ""
    message = read_file('message.txt') or ""
    speed = read_file('speed.txt') or "5"
    cookies = read_file('cookies.txt') or ""
    
    return render_template('index.html', thread=thread, message=message, speed=speed, cookies=cookies, bot_running=bot_running)

@app.route('/logs')
def get_logs():
    return jsonify(bot_logs)

@app.route('/start_sending')
def start_sending():
    global bot_running
    if bot_running: return redirect(url_for('index'))
    
    thread_id = read_file('thread.txt')
    msg_content = read_file('message.txt')
    delay_time = read_file('speed.txt')
    cookies_txt = read_file('cookies.txt')
    
    if not all([thread_id, msg_content, delay_time]): 
        add_log("❌ Error: Missing Thread ID, Message, or Speed.")
        return redirect(url_for('index'))
        
    add_log("🚀 Starting Bot...")
    threading.Thread(target=lambda: asyncio.run(run_bot(thread_id, msg_content, delay_time, cookies_txt)), daemon=True).start()
    return redirect(url_for('index'))

@app.route('/stop_bot')
def stop_bot():
    global bot_running
    bot_running = False
    add_log("🛑 Stop signal sent.")
    return redirect(url_for('index'))

async def run_bot(thread_id, msg_content, delay, cookies_str):
    global bot_running
    bot_running = True
    
    try:
        delay = float(delay)
        async with async_playwright() as p:
            add_log("Launching Browser...")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={'width': 1280, 'height': 800})
            
            # Cookie Parsing logic
            try:
                if cookies_str.startswith('['):
                    cookie_list = json.loads(cookies_str)
                else:
                    # Simple parser for Key=Value string
                    cookie_list = []
                    for pair in cookies_str.split(';'):
                        if '=' in pair:
                            k, v = pair.split('=', 1)
                            cookie_list.append({'name': k.strip(), 'value': v.strip(), 'domain': '.facebook.com', 'path': '/'})
                
                await context.add_cookies(cookie_list)
                add_log("Cookies loaded.")
            except Exception as e:
                add_log(f"❌ Cookie Error: {str(e)}")
                bot_running = False
                return

            page = await context.new_page()
            target_url = f"https://www.facebook.com/messages/t/{thread_id}"
            add_log(f"Opening: {target_url}")
            
            await page.goto(target_url, timeout=60000)
            await asyncio.sleep(10) # Initial load wait

            # Check if login required
            if "login" in page.url:
                add_log("❌ Login Failed! Check cookies.")
                bot_running = False
                await browser.close()
                return

            add_log("✅ Page loaded. searching for input box...")
            
            selectors = ['div[aria-label="Message"]', 'div[role="textbox"]', 'div[contenteditable="true"]']
            box_found = False
            
            while bot_running:
                try:
                    # Try to focus
                    for sel in selectors:
                        if await page.query_selector(sel):
                            await page.click(sel)
                            box_found = True
                            break
                    
                    if not box_found:
                         add_log("⚠️ Input box not found, retrying...")
                         await asyncio.sleep(5)
                         continue

                    await page.keyboard.type(msg_content)
                    await asyncio.sleep(0.5)
                    await page.keyboard.press('Enter')
                    add_log(f"📨 Sent: {msg_content[:10]}...")
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    add_log(f"⚠️ Loop Error: {str(e)}")
                    await asyncio.sleep(5)

            await browser.close()
            add_log("Bot Stopped.")
            
    except Exception as e:
        add_log(f"❌ Critical Error: {str(e)}")
        bot_running = False

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
