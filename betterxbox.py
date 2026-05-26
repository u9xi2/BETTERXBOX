import telebot
from playwright.sync_api import sync_playwright
import imaplib
import email
import re
import time
import sqlite3
import os
from bs4 import BeautifulSoup

# --- بياناتك الثابتة المدمجة بالكامل ---
BOT_TOKEN = '8991830245:AAGR_7t_XJ67hRU-OHh_kzpadWRnesucYAk'
ADMIN_ID = 1451811772  # حسابك الآدمن لتلقي الإشعارات والـ Chat ID
bot = telebot.TeleBot(BOT_TOKEN)

XBOX_EMAIL = "jafar2322008@gmail.com"
XBOX_PASSWORD = "2322008@JaF"
IMAP_SERVER = "imap.gmail.com"
GMAIL_APP_PASSWORD = "ssmx batl adno ggbk"

DB_FILE = 'database.db'

# --- إنشاء قاعدة البيانات والجداول على السيرفر تلقائياً ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS codes (code TEXT PRIMARY KEY, used INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_sessions (chat_id INTEGER PRIMARY KEY, purchase_code TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- دالة جلب كود الـ 2FA من الجيميل ---
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
    except Exception as e: print(f"خطأ بالجيميل: {e}")
    return None

# --- معالجة الرسائل والشات ---
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()
    first_name = message.from_user.first_name or "مشتري"

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. أوامر التحكم الخاصة بك (الآدمن)
    if chat_id == ADMIN_ID:
        if text.startswith('/add '):
            new_code = text.split('/add ')[1].strip()
            try:
                cursor.execute("INSERT INTO codes (code) VALUES (?)", (new_code,))
                conn.commit()
                bot.reply_to(message, f"✅ تم حفظ الكود الجديد في الـ DB:\n`{new_code}`")
            except:
                bot.reply_to(message, "⚠️ هذا الكود مضاف مسبقاً بقاعدة البيانات!")
            conn.close()
            return
        
        elif text == '/show':
            cursor.execute("SELECT code FROM codes WHERE used = 0")
            rows = cursor.fetchall()
            if rows:
                msg_list = "🎫 **الأكواد المتوفرة بالـ DB حالياً:**\n\n" + "\n".join([f"- `{r[0]}`" for r in rows])
                bot.reply_to(message, msg_list, parse_mode="Markdown")
            else:
                bot.reply_to(message, "📭 قاعدة البيانات فارغة، لا توجد أكواد متوفرة حالياً.")
            conn.close()
            return

    # الفحص الأمني للزبون
    cursor.execute("SELECT purchase_code FROM active_sessions WHERE chat_id = ?", (chat_id,))
    session_row = cursor.fetchone()
    is_verified = session_row is not None

    # 2. خطوة التحقق من كود الشراء للزبون لأول مرة
    if not is_verified:
        cursor.execute("SELECT used FROM codes WHERE code = ?", (text,))
        code_row = cursor.fetchone()

        if code_row and code_row[0] == 0:
            cursor.execute("INSERT INTO active_sessions (chat_id, purchase_code) VALUES (?, ?)", (chat_id, text))
            conn.commit()
            bot.reply_to(message, "🎉 تم تفعيل صلاحيتك بنجاح!\n\nالآن قم بتشغيل جهاز الاكس بوكس، اختر (تسجيل دخول من جهاز آخر) وأرسل كود الـ 8 رموز الظاهر على شاشتك هنا فوراً.")
        else:
            bot.reply_to(message, "👋 أهلاً بك في متجر الاكسبوكس.\n⚠️ البوت مخصص للمشترين فقط. يرجى إرسال كود الشراء لتفعيل البوت.")
        conn.close()
        return

    # 3. خطوة استلام الـ 8 رموز وتشغيل الأتمتة الحقيقية عبر المتصفح المخفي
    if len(text) == 8:
        bot.reply_to(message, "⏳ الكود مستلم. جاري تشغيل الأتمتة وسحب الأمان من Gmail، انتظر ثواني...")
        
        current_purchase_code = session_row[0]
        success = False

        try:
            with sync_playwright() as p:
                # تشغيل المتصفح على السيرفر
                browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                page = browser.new_page()

                # فتح موقع الربط وإدخال الـ 8 رموز مالت الزبون
                page.goto('https://microsoft.com/link')
                page.wait_for_selector('input[name="otc"]')
                page.fill('input[name="otc"]', text)
                page.click('input[type="submit"]')

                # إدخال إيميل الحساب المشترك
                page.wait_for_selector('input[type="email"]')
                page.fill('input[type="email"]', XBOX_EMAIL)
                page.click('input[type="submit"]')

                # إدخال باسورد الحساب المشترك
                page.wait_for_selector('input[type="password"]')
                page.fill('input[type="password"]', XBOX_PASSWORD)
                page.click('input[type="submit"]')

                try:
                    page.wait_for_selector('input[type="submit"]', timeout=4000)
                    page.click('input[type="submit"]')
                except: pass

                # التعامل مع حماية مايكروسوفت الـ 2FA وسحب الرمز من الجيميل تلقائياً
                try:
                    page.wait_for_selector('input[name="otc"]', timeout=6000)
                    bot.send_message(chat_id, "📩 تم إرسال الأمان.. جاري سحب الكود تلقائياً من الإيميل...")
                    security_code = get_verification_code()
                    
                    if security_code:
                        page.fill('input
