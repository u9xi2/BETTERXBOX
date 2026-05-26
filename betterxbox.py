import telebot
import asyncio
import re
import requests
import sqlite3
import os
import sys
from playwright.async_api import async_playwright

# --- البيانات الأساسية الخاصة بك ---
BOT_TOKEN = '8840379258:AAGrzlu21gyUwflAXshTnD9VheFgBJf5XyM'
ADMIN_ID = 1451811772

bot = telebot.TeleBot(BOT_TOKEN)
DB_FILE = 'database.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS codes (code TEXT PRIMARY KEY, used INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_sessions (chat_id INTEGER PRIMARY KEY, purchase_code TEXT)''')
    conn.commit()
    conn.close()
    print("📦 تم تهيئة قاعدة البيانات بنجاح.")

async def run_playwright_logic(device_code_text):
    # ميزة سحرية: تنصيب المتصفح تلقائياً بداخل السيرفر إذا كان ممسوحاً
    print("🌐 جاري التحقق من وجود المتصفح وتنصيبه تلقائياً...")
    os.system("python3 -m playwright install chromium")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()
        try:
            await page.goto("https://login.live.com/oauth20_remoteconnect.srf")
            await page.fill('input[name="otc"]', device_code_text)
            await page.click('input[type="submit"]')
            await asyncio.sleep(5)
            print(f"✅ تم إرسال الكود {device_code_text} للمتصفح بنجاح.")
        except Exception as e:
            print(f"❌ خطأ داخل المتصفح: {e}")
            raise e
        finally:
            await browser.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    welcome_text = (
        "👋 أهلاً بك في بوت تفعيل إكسبوكس المطور!\n\n"
        "🎟️ يرجى إرسال كود الشراء أولاً لتفعيل صلاحيتك والبدء بالربط التلقائي."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if chat_id == ADMIN_ID:
        if text.startswith('/add '):
            new_code = text.split('/add ')[1].strip()
            try:
                cursor.execute("INSERT INTO codes (code) VALUES (?)", (new_code,))
                conn.commit()
                bot.reply_to(message, f"✅ تم حفظ كود الشراء في الـ DB:\n`{new_code}`", parse_mode="Markdown")
            except sqlite3.IntegrityError:
                bot.reply_to(message, "⚠️ هذا الكود مضاف مسبقاً في قاعدة البيانات!")
            except Exception as e:
                bot.reply_to(message, f"❌ حدث خطأ أثناء الإضافة: {e}")
            conn.close()
            return
        
        elif text == '/show':
            cursor.execute("SELECT code FROM codes WHERE used = 0")
            rows = cursor.fetchall()
            if rows:
                msg_list = "🎫 **أكواد الشراء المتوفرة وغير المستخدمة:**\n\n" + "\n".join([f"- `{r[0]}`" for r in rows])
                bot.reply_to(message, msg_list, parse_mode="Markdown")
            else:
                bot.reply_to(message, "📭 قاعدة البيانات فارغة حالياً، لا توجد أكواد متوفرة.")
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
            bot.reply_to(message, "🎉 ممتاز! تم تفعيل صلاحيتك بنجاح.\n\nالآن قم بتشغيل الإكسبوكس، واطلب كود الـ 8 رموز وأرسله هنا فوراً.")
        else:
            bot.reply_to(message, "⚠️ كود الشراء الذي أرسلته غير صحيح، أو مستخدم مسبقاً.")
        conn.close()
        return

    if len(text) == 8:
        bot.reply_to(message, "⏳ الكود مستلم، جاري تشغيل المتصفح السري والمصادقة تلقائياً عبر السيرفر...")
        current_purchase_code = session_row[0]
        
        try:
            asyncio.run(run_playwright_logic(text))
            
            cursor.execute("DELETE FROM codes WHERE code = ?", (current_purchase_code,))
            cursor.execute("DELETE FROM active_sessions WHERE chat_id = ?", (chat_id,))
            conn.commit()
            
            admin_alert = f"🔔 **تم تفعيل كود بنجاح!**\n🎫 كود الشراء المستهلك: `{current_purchase_code}`\n🆔 الـ Chat ID للمشتري: `{chat_id}`"
            bot.send_message(ADMIN_ID, admin_alert, parse_mode="Markdown")
            
            bot.send_message(chat_id, "✅ تم تسجيل الدخول وتفعيل الحساب على جهازك بنجاح تام! استمتع باللعب. 🎮")
        except Exception as e:
            bot.send_message(chat_id, f"❌ حدث خطأ أثناء تشغيل المتصفح على السيرفر: {e}\n\nيرجى إعادة المحاولة بعد ثوانٍ.")
    else:
        bot.send_message(chat_id, "⚠️ يرجى إرسال كود الـ 8 رموز الظاهر على شاشة الإكسبوكس بشكل صحيح.")
        
    conn.close()

if __name__ == '__main__':
    init_db()
    print("🔄 جاري تنظيف وحذف الـ Webhook المعلق إن وجد...")
    bot.remove_webhook()
    print("🚀 البوت الجديد شغال الآن على رندر وبانتظار الأوامر...")
    bot.polling(none_stop=True)
