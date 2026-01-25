from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import asyncio
import os
import threading
from playwright.async_api import async_playwright
from werkzeug.utils import secure_filename
import time
import gc # Garbage Collector for RAM cleaning

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

bot_running = False
bot_logs = []

def add_log(message):
    timestamp = time.strftime("%H:%M:%S")
    bot_logs.append(f"[{timestamp}] {message}")
    if len(bot_logs) > 50:
        bot_logs.pop(0)

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

# --- KEEP ALIVE ROUTE ---
@app.route('/keep_alive')
def keep_alive():
    return "I am alive"

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
        
    add_log("🚀 Starting Marathon Bot...")
    # Loop alag thread me chalega
    threading.Thread(target=start_background_loop, args=(thread_id, msg_content, delay_time, cookies_txt), daemon=True).start()
    return redirect(url_for('index'))

@app.route('/stop_bot')
def stop_bot():
    global bot_running
    bot_running = False
    add_log("🛑 Stop signal sent.")
    return redirect(url_for('index'))

def start_background_loop(thread_id, msg_content, delay, cookies_str):
    # This wrapper function keeps restarting the browser session
    global bot_running
    bot_running = True
    
    while bot_running:
        try:
            # Browser session start
            asyncio.run(run_bot_session(thread_id, msg_content, delay, cookies_str))
            
            # Session end hone ke baad RAM saaf karein
            gc.collect() 
            add_log("♻️ RAM Cleaned. Restarting browser...")
            time.sleep(5) # Thoda rest taaki CPU cool ho jaye
            
        except Exception as e:
            add_log(f"❌ Restart Error: {str(e)}")
            time.sleep(10)

async def run_bot_session(thread_id, msg_content, delay, cookies_str):
    global bot_running
    try:
        delay = float(delay)
        async with async_playwright() as p:
            add_log("Launching Mini Browser...")
            
            # --- SUPER LOW MEMORY CONFIG ---
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            # Mobile Viewport = Less RAM
            context = await browser.new_context(viewport={'width': 600, 'height': 800})
            
            if cookies_str:
                try:
                    if cookies_str.startswith('['):
                        cl = json.loads(cookies_str)
                    else:
                        cl = []
                        for pair in cookies_str.split(';'):
                            if '=' in pair:
                                k, v = pair.split('=', 1)
                                cl.append({'name': k.strip(), 'value': v.strip(), 'domain': '.facebook.com', 'path': '/'})
                    await context.add_cookies(cl)
                except: pass

            page = await context.new_page()
            
            try:
                await page.goto(f"https://www.facebook.com/messages/t/{thread_id}", timeout=45000)
                await asyncio.sleep(5)
            except:
                await browser.close()
                return # Network timeout handling

            # Cookie Banner Remover
            try:
                await page.click('span:has-text("Allow all cookies")', timeout=2000)
            except: pass

            selectors = ['div[aria-label="Message"]', 'div[role="textbox"]', 'div[contenteditable="true"]']
            box_found = False
            
            # --- Anti-Popup ---
            try:
                await page.keyboard.press('Escape')
            except: pass

            for sel in selectors:
                try:
                    if await page.query_selector(sel):
                        await page.click(sel)
                        box_found = True
                        break
                except: continue

            if not box_found:
                 add_log("⚠️ Box missing. Resetting...")
                 await browser.close()
                 return

            # --- SEND ONLY 20 MESSAGES PER SESSION ---
            # Browser ko 20 message ke baad band kar denge taaki RAM bhare na
            for i in range(20):
                if not bot_running: break
                
                try:
                    await page.keyboard.type(msg_content)
                    await asyncio.sleep(0.5)
                    await page.keyboard.press('Enter')
                    add_log(f"📨 Sent ({i+1}/20)...")
                    await asyncio.sleep(delay)
                except:
                    break
            
            # Browser close explicitly
            await context.close()
            await browser.close()
            
    except Exception as e:
        add_log(f"⚠️ Session Error: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
