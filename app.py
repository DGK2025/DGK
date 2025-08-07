from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import requests
import json
import os
import re


app = Flask(__name__)
app.secret_key = 'your-super-secret-key'

AVALAI_API_KEY = "aa-Mjv2UvpPr7XUrpjsLyvnmh1UPfSdJh1Ha3ibXrr4pEm0wnBB"
AVALAI_BASE_URL = "https://api.avalai.ir/v1"


USERS_FILE = 'users.json'


def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def find_user(username):
    users = load_users()
    for u in users:
        if u['username'] == username:
            return u
    return None

def check_user(username, password):
    u = find_user(username)
    if u and u['password'] == password:
        return True
    return False

def add_user(username, password):
    users = load_users()
    if find_user(username):
        return False, 'این نام کاربری قبلاً ثبت شده!'
    users.append({'username': username, 'password': password})
    save_users(users)
    return True, None



def ai_output_to_html(text):
    """
    تبدیل خروجی AI به HTML با پشتیبانی کامل از فارسی
    """
    if not text or not isinstance(text, str):
        return ""
    
    # یکسان‌سازی خطوط جدید و حذف فاصله‌های اضافی
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r' +\n', '\n', text)  # حذف فاصله قبل از خط جدید
    text = re.sub(r'\n +', '\n', text)  # حذف فاصله بعد از خط جدید
    
    # کاهش خطوط خالی متوالی به حداکثر دو خط
    normalized_text = re.sub(r'\n{3,}', '\n\n', text.strip())
    
    # تقسیم پاراگراف‌ها
    paragraphs = [p.strip() for p in normalized_text.split('\n\n') if p.strip()]
    
    # تولید HTML
    html_paragraphs = [
        f'<p style="text-align: right; direction: rtl; line-height: 1.6;">{p}</p>'
        for p in paragraphs
    ]
    
    return '\n'.join(html_paragraphs)



# --- ROUTES --------------------

@app.route('/')
def main_page():
    return render_template('1-MainPage.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['email_or_mobile']
        password = request.form['password']
        if check_user(username, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            flash('نام کاربری یا رمز عبور صحیح نیست!')
    return render_template('2-loginPage.html')



@app.route('/signup', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        username = request.form['email_or_mobile']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')
        if not username or not password or not confirm_password:
            flash('همه فیلدها الزامیست!')
            return render_template('3-SignupPage.html')
        if password != confirm_password:
            flash('رمز و تکرار آن یکسان نیست!')
            return render_template('3-SignupPage.html')
        success, message = add_user(username, password)
        if success:
            flash('ثبت‌نام با موفقیت انجام شد. حالا وارد شوید!')
            return redirect(url_for('login'))
        else:
            flash(message)
            return render_template('3-SignupPage.html')
    return render_template('3-SignupPage.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('username'):
        return redirect(url_for('login'))
    return render_template('5-DashboardPage2.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    password = None
    if request.method == 'POST':
        username = request.form.get('email_or_mobile')
        user = find_user(username)
        if user:
            password = user['password']
        else:
            flash('کاربری با این ایمیل یا شماره پیدا نشد.')
    return render_template('forgot_password.html', password=password)



def call_avayl_ai(messages, max_tokens=1700, temperature=0.75, model="gpt-4.1-mini"):
    headers = {
        "Authorization": f"Bearer {AVALAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    try:
        response = requests.post(
            f"{AVALAI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content or "پاسخی یافت نشد."
        else:
            return f"خطای ارتباط با AvaL AI: {response.text}"
    except Exception as e:
        return f"خطای سرور یا افزونه Avayl: {str(e)}"

@app.route('/businessplan', methods=['POST'])
def businessplan():
    if not session.get('username'):
        return redirect(url_for('login'))

    data = request.form
    prompt = f"""
می‌خواهم یک بیزنس‌پلن کامل و حرفه‌ای به زبان فارسی برای کسب‌وکاری با مشخصات زیر داشته باشم.
لطفاً متن را با زبان رسمی، ساختارمند و قابل ارائه برای سرمایه‌گذار یا بانک تنظیم کن.

**مشخصات کسب‌وکار:**
- **نام کسب‌وکار:** {data.get('business_name')}
- **حوزه فعالیت:** {data.get('field')}
- **وضعیت فعلی:** {data.get('status')}
- **محصول یا خدمت اصلی:** {data.get('main_product')}
- **ویژگی متمایز:** {data.get('unique_feature')}
- **مشتریان هدف:** {data.get('target_customers')}
- **بازار هدف:** {data.get('target_market')}
- **درآمد فعلی یا پیش‌بینی:** {data.get('income')}
- **سرمایه مورد نیاز:** {data.get('needed_investment')}
- **هدف از تهیه بیزنس‌پلن:** {data.get('businessplan_goal')}

**ساختار موردنظر (خروجی دقیقاً بر اساس این تیترها باشد):**
1. **خلاصه مدیریتی**
2. **معرفی کسب‌وکار و ضرورت راه‌اندازی آن**
3. **محصول یا خدمت و ارزش پیشنهادی**
4. **تحلیل بازار و رقبا**
5. **برنامه بازاریابی و فروش**
6. **مدل درآمدی و مالی**
7. **برنامه عملیاتی و اجرایی (Roadmap)**
8. **تیم مؤسس و ساختار سازمانی**
9. **تحلیل ریسک‌‌ها و برنامه مدیریت ریسک**
10. **پیش‌بینی مالی (در صورت نبود دیتا به‌صورت فرضی نمونه بزن)**
11. **جمع‌بندی و درخواست نهایی**

در هر بخش نهایتاً ۴ تا ۷ پاراگراف بنویس و اگر نیاز بود اطلاعات فرضی و واقعی ترکیب کن تا متن کامل و حرفه‌ای شود.
سبک متن رسمی و مناسب جلسه کاری یا سرمایه‌گذار باشد و بر نکات اصلی متمرکز شو.
رزومه (Bio) کوتاهی هم برای مؤسسین در بخش ۸ اضافه کن.
    """

    messages = [
        {"role": "system", "content": "شما یک مشاور بیزینس و تولید محتوا هستید."},
        {"role": "user", "content": prompt},
    ]

    result = call_avayl_ai(messages, max_tokens=1900, temperature=0.8)
    pretty_result = ai_output_to_html(result)
    return render_template('5-DashboardPage2.html', businessplan_result=pretty_result)

@app.route('/resume', methods=['POST'])
def resume():
    if not session.get('username'):
        return redirect(url_for('login'))

    data = request.form
    prompt = f"""
می‌خواهم یک رزومه کامل و حرفه‌ای به زبان فارسی برای شخصی با مشخصات زیر بنویسی.
خروجی باید قالب استاندارد رزومه قابل ارائه به شرکت یا سازمان باشد و سبک متن رسمی، فشرده و دقیق با تمرکز بر دستاوردها و مهارت‌ها نوشته شود. بخش‌ها با تیتر مناسب و جزییات خلاصه ولی کامل باشد.

**مشخصات فردی:**
- **نام و نام خانوادگی:** {data.get('fullname')}
- **سمت یا شغل موردنظر:** {data.get('job')}
- **تحصیلات:** {data.get('education')}
- **تجربه‌های شغلی:** {data.get('jobs')}
- **مهارت‌ها:** {data.get('skills')}
- **دستاوردها/گواهینامه‌ها:** {data.get('achievements')}
- **زبان‌ها:** {data.get('languages')}
- **ویژگی‌های فردی:** {data.get('personal')}
- **اطلاعات تماس:** {data.get('contact')}

**ساختار خروجی دقیقاً بر اساس این سرفصل‌ها باشد:**
1. **اطلاعات فردی و تماس**
2. **معرفی و هدف شغلی**
3. **تحصیلات**
4. **سوابق کاری و تجربیات**
5. **مهارت‌ها**
6. **دستاوردها و افتخارات**
7. **زبان‌ها**
8. **علایق و ویژگی‌های شخصیتی (اختیاری)**
9. **جمع‌بندی (یک پاراگراف پایانی کوتاه برای معرفی نهایی و هدف ارسال)**

در هر بخش، بین ۲ تا ۵ پاراگراف رسمی و بدون کلی‌گویی، با جزییات واقعی یا فرضی متعارف بازار کار ایران بنویس. اگر داده نبود، اطلاعات فرضی مناسب جایگزین کن. قالب نهایی در متن خروجی رعایت شود.
    """
    messages = [
        {"role": "system", "content": "شما یک رزومه‌ساز حرفه‌ای هستید."},
        {"role": "user", "content": prompt}
    ]
    result = call_avayl_ai(messages, max_tokens=1500, temperature=0.7)
    pretty_result = ai_output_to_html(result)
    return render_template('5-DashboardPage2.html', resume_result=pretty_result)

# ------------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)