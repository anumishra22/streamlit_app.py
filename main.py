from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import asyncio
import os
import time
import sys
import threading
from playwright.async_api import async_playwright
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Global Bot State ---
bot_running = False

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
    return None

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

@app.route('/', methods=['GET', 'POST'])
def index():
    global bot_running
    if request.method == 'POST':
        thread = request.form.get('thread')
        speed = request.form.get('speed')
        cookies_raw = request.form.get('cookies')
        
        # Handle file upload for messages
        if 'message_file' in request.files:
            file = request.files['message_file']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'message.txt')
                file.save(filepath)
                # Also save to current dir for compatibility with existing logic
                file.seek(0)
                save_file('message.txt', file.read().decode('utf-8'))

        if thread: save_file('thread.txt', thread)
        if speed: save_file('speed.txt', speed)
        
        if cookies_raw:
            try:
                if cookies_raw.strip().startswith('['):
                    cookies_json = json.loads(cookies_raw)
                else:
                    cookies_json = parse_cookie_string(cookies_raw)
                with open('cookies.json', 'w') as f:
                    json.dump(cookies_json, f)
            except Exception as e:
                return f"Invalid Cookies format: {str(e)}", 400
        
        return redirect(url_for('index'))

    thread = read_file('thread.txt') or ""
    message = read_file('message.txt') or ""
    speed = read_file('speed.txt') or "5"
    cookies = ""
    if os.path.exists('cookies.json'):
        try:
            with open('cookies.json', 'r') as f:
                cookies_data = json.load(f)
                if isinstance(cookies_data, list):
                    cookies = json.dumps(cookies_data)
        except:
            pass

    return render_template('index.html', thread=thread, message=message, speed=speed, cookies=cookies, bot_running=bot_running)

async def run_playwright_bot_loop(target_url, msg_content, delay):
    global bot_running
    bot_running = True
    
    async with async_playwright() as p:
        try:
            launch_args = ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            browser = await p.chromium.launch(headless=True, args=launch_args)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            if os.path.exists('cookies.json'):
                with open('cookies.json', 'r') as f:
                    await context.add_cookies(json.load(f))
            
            page = await context.new_page()
            await page.goto(target_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(15)
            
            selectors = ['div[aria-label="Message"]', 'div[role="textbox"]', 'div[contenteditable="true"]', 'textarea']

            while bot_running:
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
                    await page.mouse.click(640, 750)
                    await asyncio.sleep(1)
                
                await page.keyboard.type(msg_content, delay=0)
                await asyncio.sleep(0.01)
                await page.keyboard.press('Enter')
                await asyncio.sleep(delay)
                
            await browser.close()
        except Exception as e:
            print(f"Loop Error: {str(e)}")
            bot_running = False

@app.route('/start_sending', methods=['GET'])
def start_sending():
    global bot_running
    if bot_running: return redirect(url_for('index'))
    thread_id = read_file('thread.txt')
    msg_content = read_file('message.txt')
    delay_time = read_file('speed.txt')
    if not all([thread_id, msg_content, delay_time]): return "Config missing."
    target_url = f"https://www.facebook.com/messages/t/{thread_id}"
    try: delay = float(delay_time)
    except: delay = 1.0
    threading.Thread(target=lambda: asyncio.run(run_playwright_bot_loop(target_url, msg_content, delay)), daemon=True).start()
    return redirect(url_for('index'))

@app.route('/stop_bot')
def stop_bot():
    global bot_running
    bot_running = False
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
