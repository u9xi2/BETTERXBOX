import telebot
import asyncio
import re
import requests
import sqlite3
from playwright.async_api import async_playwright

# --- التوكن والبيانات مالتك ---
BOT_TOKEN ='8991830245:AAFECOoZIICy5U4AYDuQSuJzDvBmWGx2xoo'
ADMIN_ID = 1451811772
bot = telebot.TeleBot(BOT_TOKEN)

# رابط القناة للاشتراك الإجباري
CHANNEL_URL = "https://t.me/A_ToolsX"
CHANNEL_USERNAME = "@A_ToolsX"

DB_FILE = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS codes (code TEXT PRIMARY KEY, used INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_sessions (chat_id INTEGER PRIMARY KEY, purchase_code TEXT)''')
    conn.commit()
    conn.close()

init_db()

def check_membership(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception as e:
        print(f"خطأ في فحص القناة: {e}")
    return False

async def run_playwright_logic(device_code_text):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()
        try:
            await page.goto("https://login.live.com/oauth20_remoteconnect.srf")
            # إدخال الـ 8 رموز مالت المشتري تلقائياً بالسيرفر
            await page.fill('input[name="otc"]', device_code_text)
            await page.click('input[type="submit"]')
            await asyncio.sleep(5)
        except Exception as e:
            print(f"خطأ أثناء تشغيل المتصفح: {e}")
        finally:
            await browser.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if not check_membership(chat_id):
        markup = telebot.types.InlineKeyboardMarkup()
        btn = telebot.types.InlineKeyboardButton("اضغط هنا للاشتراك بقناتنا 🚀", url=CHANNEL_URL)
        markup.add(btn)
        bot.send_message(chat_id, f"🚀 لاستخدام هذا البوت، يجب عليك أولاً الاشتراك في قناتنا الرسمية:\n{CHANNEL_URL}", reply_markup=markup)
        return
    bot.reply_to(message, "👋 أهلاً بك في بوت تفعيل إكسبوكس المطور!\nيرجى إرسال كود الشراء أولاً لتفعيل صلاحياتك.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()

    if not check_membership(chat_id):
        send_welcome(message)
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if chat_id == ADMIN_ID:
        if text.startswith('/add '):
            new_code = text.split('/add ')[1].strip()
            try:
                cursor.execute("INSERT INTO codes (code) VALUES (?)", (new_code,))
                conn.commit()
                bot.reply_to(message, f"✅ تم حفظ الكود في الـ DB:\n`{new_code}`")
            except:
                bot.reply_to(message, "⚠️ مضاف مسبقاً!")
            conn.close()
            return
        
        elif text == '/show':
            cursor.execute("SELECT code FROM codes WHERE used = 0")
            rows = cursor.fetchall()
            if rows:
                msg_list = "🎫 **الأكواد المتوفرة:**\n\n" + "\n".join([f"- `{r[0]}`" for r in rows])
                bot.reply_to(message, msg_list, parse_mode="Markdown")
            else:
                bot.reply_to(message, "📭 الـ DB فارغة.")
            conn.close()
            return

    cursor.execute("SELECT purchase_code FROM active_sessions WHERE chat_id = ?", (chat_id,))
    session_row = cursor.fetchone()
    is_verified = session_row is not None

    if not is_verified:
        cursor.execute("SELECT used FROM codes WHERE code = ?", (text,))
        code_row = cursor.fetchone()
        if code_row and code_row[0] == 0:
            cursor.execute("INSERT INTO active_sessions (chat_id, purchase_code) VALUES (?, ?)", (chat_id, text))
            conn.commit()
            bot.reply_to(message, "🎉 تم تفعيل صلاحيتك لعملية الدخول!\n\nالآن قم بتشغيل الإكسبوكس وأرسل كود الـ 8 رموز هنا فوراً.")
        else:
            bot.reply_to(message, "⚠️ كود الشراء غير صحيح أو مستخدم مسبقاً.")
        conn.close()
        return

    if len(text) == 8:
        bot.reply_to(message, "⏳ الكود مستلم، جاري فتح المتصفح السري والمصادقة تلقائياً عبر السيرفر...")
        current_purchase_code = session_row[0]
        
        try:
            # تشغيل المتصفح المخفي Playwright بالسيرفر لتسجيل الدخول تلقائياً
            asyncio.run(run_playwright_logic(text))
            
            cursor.execute("DELETE FROM codes WHERE code = ?", (current_purchase_code,))
            cursor.execute("DELETE FROM active_sessions WHERE chat_id = ?", (chat_id,))
            conn.commit()
            
            admin_alert = f"🔔 **تم تفعيل كود بنجاح!**\n🎫 كود الشراء: `{current_purchase_code}`\n🆔 الـ Chat ID: `{chat_id}`"
            bot.send_message(ADMIN_ID, admin_alert, parse_mode="Markdown")
            
            bot.send_message(chat_id, "✅ تم تسجيل الدخول وتفعيل الحساب على جهازك بنجاح تام! استمتع. 🎮")
        except Exception as e:
            bot.send_message(chat_id, f"❌ حدث خطأ أثناء التفعيل: {e}")
    else:
        bot.send_message(chat_id, "⚠️ يرجى إرسال كود الـ 8 رموز بشكل صحيح.")
        
    conn.close()

print("🤖 البوت الأصلي (Playwright Server) يعمل الآن على رندر...")
bot.polling(none_stop=True)
