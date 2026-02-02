from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import sqlite3
import random
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- DATABASE INITIALIZATION & FIX ---
def init_db():
    conn = sqlite3.connect('glycoguardian.db')
    cursor = conn.cursor()
    # Users Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, phone TEXT, password TEXT, join_date TEXT)''')
    # Reports Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT, result TEXT, risk_color TEXT, type TEXT, date TEXT)''')
    
    # Missing Columns Automatic Fix
    try: cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    except: pass
    try: cursor.execute("ALTER TABLE reports ADD COLUMN type TEXT")
    except: pass
    
    conn.commit()
    conn.close()
    print(">>> Database Synced Successfully!")

# DB Connection Helper
def get_db():
    conn = sqlite3.connect('glycoguardian.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Login Guard
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Please login first!", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('first_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash("Passwords not matched!", "danger")
            return redirect(url_for('register'))

        db = get_db()
        if db.execute('SELECT email FROM users WHERE email=?', (email,)).fetchone():
            flash("Email already exists!", "info")
            return redirect(url_for('login'))

        otp_code = str(random.randint(1000, 9999))
        session['otp'] = otp_code
        session['temp_user'] = {
            'name': name, 'email': email, 'phone': phone, 
            'password': password, 'date': datetime.now().strftime("%B %Y")
        }

        # Terminal OTP Print
        print("\n" + "="*30)
        print(f"  OTP FOR {email}: {otp_code}")
        print("="*30 + "\n")
        
        flash(f"OTP Sent! (Check Terminal: {otp_code})", "info")
        return redirect(url_for('verify_otp'))
    return render_template('register.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'otp' not in session: return redirect(url_for('register'))
    if request.method == 'POST':
        u_otp = "".join([request.form.get(f'otp{i}', '') for i in range(1, 5)])
        if u_otp == session.get('otp'):
            u = session.get('temp_user')
            db = get_db()
            try:
                db.execute('INSERT INTO users (name, email, phone, password, join_date) VALUES (?,?,?,?,?)',
                           (u['name'], u['email'], u['phone'], u['password'], u['date']))
                db.commit()
                session.pop('otp', None)
                flash("Registered! Please Login.", "success")
                return redirect(url_for('login'))
            except Exception as e:
                flash(f"Error: {e}", "danger")
        else:
            flash("Invalid OTP!", "danger")
    return render_template('otp.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, pwd = request.form.get('email'), request.form.get('password')
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email=? AND password=?', (email, pwd)).fetchone()
        if user:
            session['user'], session['user_name'] = user['email'], user['name']
            return redirect(url_for('dashboard'))
        flash("Invalid Credentials", "danger")
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', name=session['user_name'])

@app.route('/predict_clinical', methods=['GET', 'POST'])
@login_required
def predict_clinical():
    if request.method == 'POST':
        try:
            glucose = float(request.form.get('glucose', 0))
            if glucose > 180: res, col, msg = "High Risk", "danger", "Urgent medical checkup needed."
            elif 140 <= glucose <= 180: res, col, msg = "Medium Risk", "warning", "Monitor your diet."
            else: res, col, msg = "Low Risk", "success", "You are healthy."

            session['report'] = {'p_name': session['user_name'], 'result': res, 'color': col, 'msg': msg, 'type': 'Clinical'}
            
            db = get_db()
            db.execute('INSERT INTO reports (user_email, result, risk_color, type, date) VALUES (?,?,?,?,?)',
                       (session['user'], res, col, "Clinical", datetime.now().strftime("%Y-%m-%d")))
            db.commit()
            return redirect(url_for('show_result'))
        except:
            flash("Enter valid numbers!", "warning")
    return render_template('healthprediction.html')

@app.route('/predict_symptoms', methods=['GET', 'POST'])
@login_required
def predict_symptoms():
    if request.method == 'POST':
        p_name = request.form.get('p_name')
        score = sum(1 for s in ['polyuria', 'polydipsia', 'polyphagia'] if request.form.get(s) == 'Yes')
        res, col = ("High Risk", "danger") if score >= 2 else ("Low Risk", "success")
        msg = "Multiple symptoms detected." if col == "danger" else "Stable."

        session['report'] = {'p_name': p_name, 'result': res, 'color': col, 'msg': msg, 'type': 'Symptom'}
        
        db = get_db()
        db.execute('INSERT INTO reports (user_email, result, risk_color, type, date) VALUES (?,?,?,?,?)',
                   (session['user'], res, col, "Symptom", datetime.now().strftime("%Y-%m-%d")))
        db.commit()
        return redirect(url_for('show_result'))
    return render_template('symptomsprediction.html')

@app.route('/result')
@login_required
def show_result():
    data = session.get('report')
    return render_template('result.html', **data) if data else redirect(url_for('dashboard'))

@app.route('/food_chart')
@login_required
def food_chart():
    data = session.get('report')
    if not data: 
        return redirect(url_for('dashboard'))
    
    risk = data.get('color', 'success')
    
    if risk == 'danger': # HIGH RISK
        dos = [
            "Bitter Gourd (Kakarakaya)", "Fenugreek (Menthulu)", "Spinach & Amaranth (Thotakura)", 
            "Cinnamon (Dalchina Chekka)", "Barley Water", "Garlic & Ginger", 
            "Raw Vegetables (Salads)", "Flax Seeds (Avise Ginnalu)", "Nuts (Walnuts/Almonds)"
        ]
        donts = [
            "White Rice & Biryani", "Sweets & Jaggery", "Soft Drinks & Energy Drinks", 
            "White Bread & Maida", "Deep Fried Foods (Bajjilu/Pukodi)", "Red Meat", 
            "Full-fat Dairy", "Alcohol", "Artificial Sweeteners"
        ]
    elif risk == 'warning': # MEDIUM RISK
        dos = [
            "Brown Rice / Millets (Korralu)", "Oats & Broken Wheat (Upma Rava)", "Sprouts (Molakalu)", 
            "Guava & Papaya", "Curd & Buttermilk", "Beans & Lentils", 
            "Boiled Eggs (White part)", "Green Tea", "Chia Seeds"
        ]
        donts = [
            "Potatoes & Yam (Kandagadda)", "Bakery Items (Cakes/Puffs)", "Excess Salt (Pickles)", 
            "Honey & Dates", "Ice Creams", "Oily Curries", 
            "Pizza & Burgers", "Mangoes & Grapes (Limit)", "Flavored Yogurts"
        ]
    else: # LOW RISK / NORMAL
        dos = [
            "Whole Grains", "Fresh Fruits (Seasonal)", "Lean Protein (Fish/Chicken)", 
            "Plenty of Water", "Low-fat Milk", "Seeds & Nuts", 
            "Fiber-rich Veggies", "Herbal Tea", "Coconut Water"
        ]
        donts = [
            "Junk Food", "Processed Meat", "Excess Sugar", 
            "Too much Caffeine", "Salty Snacks (Chips)", "Late Night Heavy Meals",
            "Trans Fats", "Canned Juices"
        ]
        
    return render_template('food.html', dos=dos, donts=donts, risk=risk, name=data.get('p_name'))

@app.route('/profile')
@login_required
def profile():
    db = get_db()
    u = db.execute('SELECT * FROM users WHERE email=?', (session['user'],)).fetchone()
    r = db.execute('SELECT * FROM reports WHERE user_email=? ORDER BY id DESC', (session['user'],)).fetchall()
    return render_template('profile.html', user=u, reports=r)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)