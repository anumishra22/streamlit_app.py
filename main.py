from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
import json
import asyncio
import os
import threading
from playwright.async_api import async_playwright
from werkzeug.utils import secure_filename
import time
import random

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# --- Setup Folders ---
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists('static'):
    os.makedirs('static')

# --- Global State ---
bot_running = False
bot_logs = []

def add_log(message):
    timestamp = time.strftime("%H:%M:%S")
    bot_logs.append(f"[{timestamp}] {message}")
    if len(bot_logs) > 50:
        bot_logs.pop(0)

# --- Helper Functions ---
def save_file(filename, content):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        add_log(f"❌ Save Error: {str(e)}")

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
        try:
            thread = request.form.get('thread')
            speed = request.form.get('speed')
            cookies_raw = request.form.get('cookies')
            
            if 'message_file' in request.files:
                file = request.files['message_file']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'message.txt')
                    file.save(filepath)
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        save_file('message.txt', f.read())
                    add_log("Message file updated.")

            if thread: save_file('thread.txt', thread)
            if speed: save_file('speed.txt', speed)
            if cookies_raw: save_file('cookies.txt', cookies_raw)
            
            add_log("✅ Settings Updated.")
        except Exception as e:
            add_log(f"❌ Update Error: {str(e)}")

        return redirect(url_for('index'))

    thread = read_file('thread.txt') or ""
    message = read_file('message.txt') or ""
    speed = read_file('speed.txt') or "5"
    cookies = read_file('cookies.txt') or ""
    
    return render_template('index.html', thread=thread, message=message, speed=speed, cookies=cookies, bot_running=bot_running)

@app.route('/logs')
def get_logs():
    return jsonify(bot_logs)

@app.route('/debug')
def view_debug():
    if os.path.exists('static/debug.png'):
        return send_from_directory('static', 'debug.png')
    return "No debug screenshot yet."

@app.route('/start_sending')
def start_sending():
    global bot_running
    if bot_running: return redirect(url_for('index'))
    
    thread_id = read_file('thread.txt')
    msg_content = read_file('message.txt')
    delay_time = read_file('speed.txt')
    cookies_txt = read_file('cookies.txt')
    
    if not all([thread_id, msg_content, delay_time]): 
        add_log("❌ Error: Missing Details.")
        return redirect(url_for('index'))
        
    add_log("🚀 Starting Stealth Bot...")
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
            add_log("Launching Stealth Browser...")
            
            # --- STEALTH MODE SETTINGS ---
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled', # Robot detection OFF
                    '--no-sandbox',
                    '--disable-infobars',
                    '--disable-dev-shm-usage',
                    '--start-maximized'
                ]
            )
            
            # Asli Computer User-Agent
            context = await browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            if cookies_str:
                try:
                    if cookies_str.startswith('['):
                        cookie_list = json.loads(cookies_str)
                    else:
                        cookie_list = []
                        for pair in cookies_str.split(';'):
                            if '=' in pair:
                                k, v = pair.split('=', 1)
                                cookie_list.append({'name': k.strip(), 'value': v.strip(), 'domain': '.facebook.com', 'path': '/'})
                    await context.add_cookies(cookie_list)
                    add_log("Cookies loaded.")
                except: pass

            page = await context.new_page()
            target_url = f"https://www.facebook.com/messages/t/{thread_id}"
            add_log(f"Opening Chat...")
            
            await page.goto(target_url, timeout=60000)
            await asyncio.sleep(10)

            if "login" in page.url:
                add_log("❌ Cookies Expired! Login page detected.")
                await page.screenshot(path='static/debug.png')
                bot_running = False
                await browser.close()
                return

            # --- Expanded Selectors List ---
            selectors = [
                'div[aria-label="Message"]', 
                'div[role="textbox"]', 
                'div[contenteditable="true"]',
                'div[data-lexical-editor="true"]', # New FB Editor
                'div[aria-label="Type a message..."]'
            ]
            
            retry_count = 0
            while bot_running:
                box_found = False
                
                # Anti-Popup: Click on blank space & press ESC
                try:
                    await page.mouse.click(10, 10)
                    await page.keyboard.press('Escape')
                except: pass

                for sel in selectors:
                    try:
                        # Wait for selector (Better than query)
                        if await page.query_selector(sel):
                            await page.click(sel)
                            box_found = True
                            retry_count = 0
                            break
                    except: continue
                
                if not box_found:
                     retry_count += 1
                     add_log(f"⚠️ Looking for box ({retry_count})...")
                     
                     if retry_count % 3 == 0:
                         await page.screenshot(path='static/debug.png')
                         add_log("📸 Taking screenshot to check...")
                     
                     if retry_count > 10:
                         add_log("❌ Failed. Check /debug for photo.")
                         bot_running = False
                         break
                         
                     await asyncio.sleep(3)
                     continue

                try:
                    await page.keyboard.type(msg_content)
                    await asyncio.sleep(0.5)
                    await page.keyboard.press('Enter')
                    add_log(f"📨 Sent: {msg_content[:10]}...")
                    await asyncio.sleep(delay)
                except Exception as e:
                    add_log(f"⚠️ Send Error: {str(e)}")
                    await asyncio.sleep(5)

            await browser.close()
            add_log("Bot Stopped.")
            
    except Exception as e:
        add_log(f"❌ Error: {str(e)}")
        bot_running = False

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
