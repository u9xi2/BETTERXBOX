import telebot
import asyncio
import imaplib
import email
import re
import time
import sqlite3
import os
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# --- البيانات الأساسية الخاصة بك (التوكن الجديد مالتك) ---
BOT_TOKEN = '8840379258:AAGrzlu21gyUwflAXshTnD9VheFgBJf5XyM'
ADMIN_ID = 1451811772  

bot = telebot.TeleBot(BOT_TOKEN)
DB_FILE = 'database.db'

# --- تهيئة قاعدة البيانات SQLite ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS codes (code TEXT PRIMARY KEY, used INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_sessions (chat_id INTEGER PRIMARY KEY, purchase_code TEXT)''')
    conn.commit()
    conn.close()
    print("📦 تم تهيئة قاعدة البيانات database.db بنجاح.")

XBOX_EMAIL = "jafar2322008@gmail.com"
XBOX_PASSWORD = "2322008@JaF"
IMAP_SERVER = "imap.gmail.com"
GMAIL_APP_PASSWORD = "ssmx batl adno ggbk"

# --- دالة جلب كود الـ 2FA من الجيميل تلقائياً ---
def get_verification_code():
    time.sleep(7)
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(XBOX_EMAIL, GMAIL_APP_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, '(FROM "accountprotection.microsoft.com")')
        msg_ids = messages[0].split()
        if not msg_ids: return None
        latest_msg_id = msg_ids[-1]
        status, data = mail.fetch(latest_msg_id, '(RFC822)')
        for response_part in data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type in ["text/plain", "text/html"]:
                            body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                else:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                soup = BeautifulSoup(body, "html.parser")
                code_match = re.search(r'\b\d{6,7}\b', soup.get_text())
                if code_match: return code_match.group(0)
        mail.close()
        mail.logout()
    except Exception as e: 
        print(f"خطأ بالجيميل: {e}")
    return None

# --- دالة الأتمتة الكاملة والدخول التلقائي عبر Playwright ---
async def run_xbox_automation(device_code_text, chat_id):
    print("🌐 جاري التحقق من وجود المتصفح وتنصيبه تلقائياً...")
    os.system("python3 -m playwright install chromium")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()
        success = False
        try:
            await page.goto('https://microsoft.com/link')
            await page.wait_for_selector('input[name="otc"]')
            await page.fill('input[name="otc"]', device_code_text)
            await page.click('input[type="submit"]')

            await page.wait_for_selector('input[type="email"]')
            await page.fill('input[type="email"]', XBOX_EMAIL)
            await page.click('input[type="submit"]')

            await page.wait_for_selector('input[type="password"]')
            await page.fill('input[type="password"]', XBOX_PASSWORD)
            await page.click('input[type="submit"]')

            try:
                await page.wait_for_selector('input[type="submit"]', timeout=4000)
                await page.click('input[type="submit"]')
            except: pass

            try:
                await page.wait_for_selector('input[name="otc"]', timeout=6000)
                bot.send_message(chat_id, "📩 تم طلب رمز الأمان.. جاري سحبه تلقائياً من الإيميل وبدون تدخل منك...")
                
                # جلب كود الأمان تلقائياً من الجيميل
                security_code = get_verification_code()
                
                if security_code:
                    await page.fill('input[name="otc"]', security_code)
                    await page.click('input[type="submit"]')
                    await asyncio.sleep(5)
                    success = True
                else:
                    bot.send_message(chat_id, "❌ فشل سحب كود الأمان من الجيميل، أعد المحاولة بكود جهاز جديد.")
                    await browser.close()
                    return False
            except:
                # إذا تجاوز الحساب خطوة الأمان ودخل مباشرة
                success = True

            # فحص نهائي للتأكد أن مايكروسوفت وافقت على الـ 8 رموز ولم تظهر خطأ
            page_content = await page.content()
            if "error" in page_content.lower() or "not found" in page_content.lower():
                print("❌ رفضت مايكروسوفت الرموز الـ 8 المدخلة.")
                success = False

        except Exception as e:
            print(f"خطأ داخل متصفح السيرفر: {e}")
            success = False
        finally:
            await browser.close()
        
        return success

# --- أمر البداية /start ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = "👋 أهلاً بك في بوت تفعيل إكسبوكس المطور!\n\n🎟️ يرجى إرسال كود الشراء أولاً لتفعيل صلاحيتك والبدء بالربط التلقائي."
    bot.reply_to(message, welcome_text)

# --- معالجة الرسائل والشات ---
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. لوحة تحكم الأدمن (أنت) لإدارة أكواد الشراء بالـ database.db
    if chat_id == ADMIN_ID:
        if text.startswith('/add '):
            new_code = text.split('/add ')[1].strip()
            try:
                cursor.execute("INSERT INTO codes (code) VALUES (?)", (new_code,))
                conn.commit()
                bot.reply_to(message, f"✅ تم حفظ كود الشراء في الـ DB القديم مالتك:\n`{new_code}`", parse_mode="Markdown")
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
                msg_list = "🎫 **أكواد الشراء المتاحة داخل database.db:**\n\n" + "\n".join([f"- `{r[0]}`" for r in rows])
                bot.reply_to(message, msg_list, parse_mode="Markdown")
            else:
                bot.reply_to(message, "📭 قاعدة البيانات database.db فارغة حالياً.")
            conn.close()
            return

    # فحص هل المشتري مسجل مسبقاً؟
    cursor.execute("SELECT purchase_code FROM active_sessions WHERE chat_id = ?", (chat_id,))
    session_row = cursor.fetchone()
    is_verified = session_row is not None

    # 2. فحص كود الشراء للزبون الجديد من الـ DB مالتك
    if not is_verified:
        cursor.execute("SELECT used FROM codes WHERE code = ?", (text,))
        code_row = cursor.fetchone()
        
        if code_row and code_row[0] == 0:
            cursor.execute("INSERT INTO active_sessions (chat_id, purchase_code) VALUES (?, ?)", (chat_id, text))
            conn.commit()
            bot.reply_to(message, "🎉 تم تفعيل صلاحيتك بنجاح!\n\nالآن قم بتشغيل جهاز الاكس بوكس، اختر (تسجيل دخول من جهاز آخر) وأرسل كود الـ 8 رموز هنا فوراً.")
        else:
            bot.reply_to(message, "⚠️ كود الشراء غير صحيح، أو مستخدم مسبقاً بـ database.db.")
        conn.close()
        return

    # 3. استقبال كود الـ 8 رموز وتشغيل الأتمتة وسحب الأمان
    if len(text) == 8:
        bot.reply_to(message, "⏳ الكود مستلم. جاري تشغيل المتصفح السري وسحب الأمان تلقائياً من Gmail، انتظر ثواني...")
        current_purchase_code = session_row[0]

        # تشغيل دالة الأتمتة (Async)
        success = asyncio.run(run_xbox_automation(text, chat_id))
        
        if success:
            bot.send_message(chat_id, "✅ تم تفعيل الحساب وتدوير الأمان على جهازك بنجاح تام! استمتع باللعب. 🎮")
            
            # [الاستخدام الواحد]: حذف كود الشراء المستهلك وجلسة الزبون من قاعدة بياناتك
            cursor.execute("DELETE FROM codes WHERE code = ?", (current_purchase_code,))
            cursor.execute("DELETE FROM active_sessions WHERE chat_id = ?", (chat_id,))
            conn.commit()
            
            bot.send_message(ADMIN_ID, f"🔔 إشعار الأدمن: تم استخدام كود الشراء `{current_purchase_code}` وتفعيل جهاز المشتري بنجاح!")
        else:
            bot.send_message(chat_id, "❌ فشل التفعيل التلقائي. الكود المدخل قد يكون خاطئاً أو منتهي الصلاحية من شاشة الاكس بوكس.")
    else:
        bot.send_message(chat_id, "⚠️ يرجى إرسال كود الاكس بوكس المكون من 8 رموز بشكل صحيح.")
        
    conn.close()

if __name__ == '__main__':
    init_db()
    print("🔄 جاري تنظيف وحذف الـ Webhook المعلق...")
    bot.remove_webhook()
    print("🚀 البوت المتكامل (الأتمتة + database.db) يعمل الآن بنجاح على رندر بالتوكن الجديد...")
    bot.polling(none_stop=True)
