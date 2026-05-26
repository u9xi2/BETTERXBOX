Import telebot
from playwright.sync_api import sync_playwright
import imaplib
import email
import re
import time
import json
import os
from bs4 import BeautifulSoup

BOT_TOKEN = '8991830245:AAGR_7t_XJ67hRU-OHh_kzpadWRnesucYAk'
ADMIN_ID = 1451811772  # 👈 ضع هنا الـ Chat ID الخاص بيك أنت كصاحب المتجر
bot = telebot.TeleBot(BOT_TOKEN)

XBOX_EMAIL = "jafar2322008@gmail.com"
XBOX_PASSWORD = "2322008@JaF"
IMAP_SERVER = "imap.gmail.com"
GMAIL_APP_PASSWORD = "ssmx batl adno ggbk"

DATA_FILE = 'codes.json'

# --- دالات إدارة ملف الـ JSON تلقائياً ---
def load_data():
    """تحميل الأكواد والزبائن المسموح لهم من الملف"""
    if not os.path.exists(DATA_FILE):
        return {"valid_codes": [], "verified_users": {}}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"valid_codes": [], "verified_users": {}}

def save_data(data):
    """حفظ البيانات الجديدة داخل الملف"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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
    str_chat_id = str(chat_id) # تحويل الـ ID لنص للتعامل مع الـ JSON بشكل صحيح

    data = load_data()

    # 1. إذا كنت أنت الآدمن وتريد إضافة كود جديد للملف
    # ترسل بال شات مثلاً: /add VIP-99
    if chat_id == ADMIN_ID and text.startswith('/add '):
        new_code = text.split('/add ')[1].strip()
        if new_code not in data["valid_codes"]:
            data["valid_codes"].append(new_code)
            save_data(data)
            bot.reply_to(message, f"✅ تم حفظ كود تفعيل جديد بملف الـ JSON:\n`{new_code}`")
        else:
            bot.reply_to(message, "⚠️ هذا الكود مضاف مسبقاً بالملف!")
        return

    # الفحص: هل هذا الزبون مسجل مسبقاً وقاعد ينتظر يدخل كود شاشة الاكسبوكس؟
    is_verified = str_chat_id in data["verified_users"]

    # 2. إذا كان الزبون غير متحقق (يدخل للبوت لأول مرة أو يريد استخدام جديد)
    if not is_verified:
        if text in data["valid_codes"]:
            # الزبون دخل كود شراء صحيح وموجود بالملف
            # نربط الكود بـ chat_id ماله مؤقتاً لحين إتمام العملية
            data["verified_users"][str_chat_id] = text 
            save_data(data)
            bot.reply_to(message, "🎉 تم تفعيل صلاحيتك بنجاح!\n\nالآن قم بتشغيل جهاز الاكس بوكس، اختر (تسجيل دخول من جهاز آخر) وأرسل كود الـ 8 رموز الظاهر على شاشتك هنا فوراً.")
        else:
            bot.reply_to(message, "👋 أهلاً بك في متجر الاكسبوكس.\n⚠️ البوت مخصص للمشترين فقط. يرجى إرسال كود الشراء الذي استلمته من المتجر لتفعيل البوت.")
        return

    # 3. إذا كان الزبون مسموح له ويرسل كود شاشة الاكسبوكس (8 رموز)
    if len(text) == 8:
        bot.reply_to(message, "⏳ الكود مستلم. جاري تشغيل الأتمتة وسحب الأمان من Gmail، انتظر ثواني...")
        
        # حفظ كود الشراء المستخدم حالياً لمسحه لاحقاً
        current_purchase_code = data["verified_users"][str_chat_id]
        success = False

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.goto('https://microsoft.com/link')
                page.wait_for_selector('input[name="otc"]')
                page.fill('input[name="otc"]', text)
                page.click('input[type="submit"]')

                page.wait_for_selector('input[type="email"]')
                page.fill('input[type="email"]', XBOX_EMAIL)
                page.click('input[type="submit"]')

                page.wait_for_selector('input[type="password"]')
                page.fill('input[type="password"]', XBOX_PASSWORD)
                page.click('input[type="submit"]')

                try:
                    page.wait_for_selector('input[type="submit"]', timeout=4000)
                    page.click('input[type="submit"]')
                except: pass

                try:
                    page.wait_for_selector('input[name="otc"]', timeout=6000)
                    bot.send_message(chat_id, "📩 تم إرسال الأمان.. جاري سحب الكود تلقائياً من الإيميل...")
                    security_code = get_verification_code()
                    
                    if security_code:
                        page.fill('input[name="otc"]', security_code)
                        page.click('input[type="submit"]')
                        time.sleep(5)
                        success = True
                    else:
                        bot.send_message(chat_id, "❌ فشل قراءة كود الأمان من الجيميل، يرجى إعادة المحاولة.")
                        browser.close()
                        return
                except:
                    # إذا لم تطلب مايكروسوفت رمز أمان وعبرت مباشرة
                    success = True

                browser.close()
            
            if success:
                bot.send_message(chat_id, "✅ تم تفعيل الحساب على جهازك بنجاح تام! استمتع باللعب. 🎮")
                
                # 🛑 [تطبيق ميزة الاستخدام الواحد]: حذف الكود وإلغاء صلاحية الزبون فوراً
                data = load_data() # إعادة تحميل للتأكد من التزامن
                if current_purchase_code in data["valid_codes"]:
                    data["valid_codes"].remove(current_purchase_code) # مسح كود الشراء نهائياً
                if str_chat_id in data["verified_users"]:
                    del data["verified_users"][str_chat_id] # مسح الزبون من قائمة المسموح لهم
                save_data(data) # حفظ التغييرات بالملف
                
                bot.send_message(ADMIN_ID, f"🔔 إشعار: تم استخدام الكود `{current_purchase_code}` بنجاح وتم تفعيله لزبون وحذفه من الملف.")

        except Exception as e:
            print(f"Error: {e}")
            bot.send_message(chat_id, "❌ حدث خطأ أو انتهت صلاحية كود الجهاز. أعد المحاولة من جديد.")
    else:
        bot.send_message(chat_id, "⚠️ يرجى إرسال كود الاكسبوكس المكون من 8 رموز بشكل صحيح.")

print("البوت ذو الاستخدام الواحد (JSON) يعمل الآن بنجاح...")
bot.polling(none_stop=True)
