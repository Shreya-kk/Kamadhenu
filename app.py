from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import uuid
import os
import google.generativeai as genai
import os
from googletrans import Translator
import google.generativeai as genai
import time
# Configure Gemini
genai.configure(api_key="AIzaSyDxqOcGguN1q6pXF81eB2UCoqWKj7m5OlQ")

app = Flask(__name__)
app.secret_key = "kamadhenu_secret"

DB_NAME = "kamadhenu.db"
# Upload folders
COW_UPLOAD_FOLDER = os.path.join("static", "uploads", "cow")
VET_UPLOAD_FOLDER = os.path.join("static", "uploads", "vets")

os.makedirs(COW_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VET_UPLOAD_FOLDER, exist_ok=True)

app.config["COW_UPLOAD_FOLDER"] = COW_UPLOAD_FOLDER
app.config["VET_UPLOAD_FOLDER"] = VET_UPLOAD_FOLDER

import qrcode

QR_FOLDER = "static/qrcodes"
if not os.path.exists(QR_FOLDER):
    os.makedirs(QR_FOLDER)

# Ensure uploads folder exists


# ---------------- Database Setup ----------------
def init_db():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""CREATE TABLE farmers (
            farmer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            state TEXT NOT NULL,
            city TEXT NOT NULL,
            address TEXT,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        cursor.execute("""CREATE TABLE cows (
            cow_id TEXT PRIMARY KEY,
            farmer_id INTEGER,
            breed TEXT,
            age INTEGER,
            weight REAL,
            color TEXT,
            health_records TEXT,
            vaccination_history TEXT,
            milk_yield REAL,
            special_notes TEXT,
            photo TEXT,  -- store photo filename
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (farmer_id) REFERENCES farmers(farmer_id)
        )""")

        cursor.execute("""CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER NOT NULL,
            vet_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )""")

        conn.commit()
        conn.close()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn
@app.route("/")
def home():
    return render_template("main.html")   # landing page with 3 cards


# ✅ Admin credentials (hardcoded)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin@123"

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid Admin Credentials", "danger")
            return redirect(url_for("admin_login"))

    return render_template("admin_login.html")  # make a login form

@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()
    cursor = conn.cursor()

    # ✅ Count total farmers
    cursor.execute("SELECT COUNT(*) as total FROM farmers")
    farmer_count = cursor.fetchone()["total"]

    # ✅ Count total cows (across all farmers)
    cursor.execute("SELECT COUNT(*) as total FROM cows")
    cow_count = cursor.fetchone()["total"]

    # Count vets
    cursor.execute("SELECT COUNT(*) FROM veterinarians")
    vet_count = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        farmer_count=farmer_count,
        cow_count=cow_count,
        vet_count=vet_count
        
    )

@app.route("/admin/farmers")
def admin_farmers():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, email, phone, created_at, farmer_id FROM farmers")
    farmers = cursor.fetchall()
    conn.close()
    return render_template("admin_farmers.html", farmers=farmers)



@app.route("/admin/delete_farmer/<int:farmer_id>", methods=["POST"])
def delete_farmer(farmer_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM farmers WHERE farmer_id = ?", (farmer_id,))
    conn.commit()
    conn.close()

    flash("Farmer deleted successfully!", "success")
    return redirect(url_for("admin_farmers"))



@app.route("/farmer")
def farmer():
    return render_template("index.html")

@app.route("/veterinarian")
def veterinarian():
    return render_template("index2.html")

@app.route("/manage_vets")
def manage_vets():
    if "admin" not in session:  # ✅ match with admin login
        flash("Please login first!", "danger")
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("kamadhenu.db")
    cursor = conn.cursor()
    cursor.execute("SELECT vet_id, name, email, phone, clinic, photo, created_at FROM veterinarians")
    vets = cursor.fetchall()
    conn.close()

    return render_template("admin_vets.html", vets=vets)



# ---------------- Farmer Registration ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        state = request.form["state"]
        city = request.form["city"]
        address = request.form["address"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("""INSERT INTO farmers 
                              (name, email, phone, state, city, address, password) 
                              VALUES (?, ?, ?, ?, ?, ?, ?)""",
                           (name, email, phone, state, city, address, password))
            conn.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email or Phone already registered!")
        finally:
            conn.close()
    return render_template("register.html")

# ---------------- Farmer Login ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM farmers WHERE email=? AND password=?", (email, password))
        farmer = cursor.fetchone()
        conn.close()

        if farmer:
            session["farmer_id"] = farmer["farmer_id"]
            session["farmer_name"] = farmer["name"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials!")
    return render_template("login.html")

# ---------------- Dashboard ----------------
@app.route("/dashboard")
def dashboard():
    if "farmer_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    # ✅ Count total cows for this farmer
    cursor.execute("SELECT COUNT(*) as total FROM cows WHERE farmer_id=?", (session["farmer_id"],))
    total_cows = cursor.fetchone()["total"]

    # ✅ Sum of milk yield for this farmer
    cursor.execute("SELECT SUM(milk_yield) as total_milk FROM cows WHERE farmer_id=?", (session["farmer_id"],))
    total_milk = cursor.fetchone()["total_milk"] or 0

    conn.close()

    return render_template(
        "dashboard.html",
        farmer_name=session["farmer_name"],
        total_cows=total_cows,
        total_milk=total_milk
    )

# ---------------- Add Cow (with Photo) ----------------
@app.route("/add_cow", methods=["GET", "POST"])
def add_cow():
    if "farmer_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        cow_id = "COW-" + str(uuid.uuid4().hex[:6].upper())
        farmer_id = session["farmer_id"]
        breed = request.form["breed"]
        age = request.form["age"]
        weight = request.form["weight"]
        color = request.form["color"]
        health_records = request.form["health_records"]
        vaccination_history = request.form["vaccination_history"]
        milk_yield = request.form["milk_yield"]
        special_notes = request.form["special_notes"]

        # -------- Handle photo upload --------
        photo = None
        if "photo" in request.files:
            file = request.files["photo"]
            if file.filename != "":
                filename = f"{cow_id}_{file.filename}"
                filepath = os.path.join(app.config["COW_UPLOAD_FOLDER"], filename)
                file.save(filepath)
                photo = filename   # store only filename in DB


        # -------- Insert into DB --------
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO cows 
                          (cow_id, farmer_id, breed, age, weight, color, health_records, 
                           vaccination_history, milk_yield, special_notes, photo) 
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (cow_id, farmer_id, breed, age, weight, color, health_records,
                        vaccination_history, milk_yield, special_notes, photo))
        conn.commit()
        conn.close()

        # -------- Generate QR Code --------
        qr_data = f"http://127.0.0.1:5000/cow/{cow_id}"   # replace with your deployed domain later
        qr_img = qrcode.make(qr_data)
        qr_path = os.path.join(QR_FOLDER, f"{cow_id}.png")
        qr_img.save(qr_path)

        flash("Cow profile added successfully with QR code!")
        return redirect(url_for("list_cows"))

    return render_template("add_cow.html")

@app.route("/cow/<cow_id>")
def cow_details(cow_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cows WHERE cow_id=?", (cow_id,))
    cow = cursor.fetchone()
    conn.close()

    if cow:
        qr_path = f"/static/qrcodes/{cow_id}.png"
        return render_template("cow_details.html", cow=cow, qr=qr_path)
    else:
        return "Cow not found!", 404

# ---------------- List Cows ----------------
@app.route("/cows")
def list_cows():
    if "farmer_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cows WHERE farmer_id=?", (session["farmer_id"],))
    cows = cursor.fetchall()
    conn.close()
    return render_template("list_cows.html", cows=cows)

# ---------------- Delete Cow ----------------
@app.route("/delete_cow/<cow_id>", methods=["POST"])
def delete_cow(cow_id):
    if "farmer_id" not in session:
        flash("Unauthorized access!", "danger")
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    # Fetch cow details to check ownership and files
    cursor.execute("SELECT * FROM cows WHERE cow_id=? AND farmer_id=?", (cow_id, session["farmer_id"]))
    cow = cursor.fetchone()

    if not cow:
        conn.close()
        flash("Cow not found or you don't have permission!", "danger")
        return redirect(url_for("list_cows"))

    # Delete from DB
    cursor.execute("DELETE FROM cows WHERE cow_id=? AND farmer_id=?", (cow_id, session["farmer_id"]))
    conn.commit()
    conn.close()

    # Remove photo if exists
    if cow["photo"]:
        photo_path = os.path.join(app.config["UPLOAD_FOLDER"], cow["photo"])
        if os.path.exists(photo_path):
            os.remove(photo_path)

    # Remove QR code if exists
    qr_path = os.path.join(QR_FOLDER, f"{cow_id}.png")
    if os.path.exists(qr_path):
        os.remove(qr_path)

    flash("Cow deleted successfully!", "success")
    return redirect(url_for("list_cows"))


translator = Translator()



def get_gemini_response(prompt):
    full_prompt = (
        f"You are an expert agriculture assistant. "
        f"Answer ONLY questions related to farming, crops, soil, fertilizers, irrigation, "
        f"plant diseases, animal husbandry, animal health, and rural agriculture practices. "
        f"If the question is not related to agriculture, reply politely in Kannada: "
        f"'ಕ್ಷಮಿಸಿ, ನಾನು ಕೃಷಿ ಮತ್ತು ಪಶುಪಾಲನೆಗೆ ಸಂಬಂಧಿಸಿದ ಪ್ರಶ್ನೆಗಳಿಗೆ ಮಾತ್ರ ಉತ್ತರ ನೀಡುತ್ತೇನೆ.'\n\n"
        f"User asked: {prompt}\n\n"
        f"Answer in **Kannada only**, clear, natural, and grammatically correct. "
        f"Keep the answer short (max 3 sentences)."
    )
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception:
        return "ಕ್ಷಮಿಸಿ, ನಾನು ಪ್ರತಿಕ್ರಿಯೆ ನೀಡಲಾಗುವುದಿಲ್ಲ."

def get_gemini_response_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return get_gemini_response(prompt)
        except Exception as e:
            if "quota" in str(e).lower() or "429" in str(e):
                wait_time = (attempt + 1) * 10
                time.sleep(wait_time)
            else:
                raise e
    return "ಕ್ಷಮಿಸಿ, ನಾನು ಪ್ರಸ್ತುತ ಪ್ರತಿಕ್ರಿಯೆ ನೀಡಲು ಸಾಧ್ಯವಿಲ್ಲ."

@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_text = request.json.get("text")
    lang = request.json.get("lang", "en")  # Default to English
    
    greetings_kn = ["ಹಾಯ್", "ನಮಸ್ತೆ", "ನಮಸ್ಕಾರ"]
    
    if "bye" in user_text.lower() or "ವಿದಾಯ" in user_text:
        bot_response_kn = "ವಿದಾಯ! 👋"
    elif user_text in greetings_kn:
        bot_response_kn = "ನಮಸ್ತೆ! ನಿಮಗೆ ಸಹಾಯ ಬೇಕೇ?"
    else:
        # If input is in Kannada, translate to English for Gemini
        if lang == "kn":
            user_text_en = translate_to_english(user_text)
        else:
            user_text_en = user_text
            
        # Get response from Gemini
        bot_response_kn = get_gemini_response_with_retry(user_text_en)

    return {"reply": bot_response_kn}

def translate_to_english(text, retries=3):
    for attempt in range(retries):
        try:
            return translator.translate(text, src="kn", dest="en").text
        except Exception as e:
            time.sleep(1)
    return text






"""
@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_text = request.json.get("text")
    lang = request.json.get("lang")  # "en", "hi", "kn"

    # Force Gemini to reply in English (to keep responses stable)
    prompt = f""""""
    #You are a farm assistant chatbot. The farmer said: {user_text}.
    #Answer clearly in English (short, simple sentences).

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    reply = response.text

    # 🔹 Translate Gemini's English reply to farmer's language
    if lang != "en":
        translated = translator.translate(reply, dest=lang)
        reply = translated.text

    return {"reply": reply}
"""






import os
from werkzeug.utils import secure_filename

# Folder to store vet photos
UPLOAD_FOLDER = "static/uploads/vets"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/vet/register", methods=["GET", "POST"])
def vet_register():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        name = f"{first_name} {last_name}"

        email = request.form["email"]
        phone = request.form["phone"]
        clinic = request.form.get("clinic", "")
        password = request.form["password"]

        # Handle photo upload
        photo_file = request.files.get("photo")
        photo_path = None
        if photo_file and photo_file.filename != "":
            filename = secure_filename(photo_file.filename)
            save_path = os.path.join(app.config["VET_UPLOAD_FOLDER"], filename)
            photo_file.save(save_path)
            photo_path = filename   # ✅ only save filename in DB

        conn = get_db()
        cursor = conn.cursor()
        try:
            # Create table if not exists
            cursor.execute("""CREATE TABLE IF NOT EXISTS veterinarians (
                                vet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL,
                                email TEXT UNIQUE NOT NULL,
                                phone TEXT UNIQUE NOT NULL,
                                clinic TEXT,
                                password TEXT NOT NULL,
                                photo TEXT,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                              )""")

            # Insert vet data including photo
            cursor.execute("""INSERT INTO veterinarians 
                              (name, email, phone, clinic, password, photo)
                              VALUES (?, ?, ?, ?, ?, ?)""",
                           (name, email, phone, clinic, password, photo_path))
            conn.commit()

            flash("Veterinarian registered successfully! Please login.", "success")
            return redirect(url_for("vet_login"))
        except sqlite3.IntegrityError:
            flash("Email or Phone already registered!", "danger")
        finally:
            conn.close()

    return render_template("vet_register.html")



@app.route("/vet/login", methods=["GET", "POST"])
def vet_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM veterinarians WHERE email=? AND password=?", (email, password))
        vet = cursor.fetchone()
        conn.close()

        if vet:
            session["vet_id"] = vet["vet_id"]
            session["vet_name"] = vet["name"]
            flash("Login successful!", "success")
            return redirect(url_for("vet_dashboard"))
        else:
            flash("Invalid credentials!", "danger")

    return render_template("vet_login.html")

@app.route("/vet/dashboard")
def vet_dashboard():
    if "vet_id" not in session:
        flash("Please login first!", "danger")
        return redirect(url_for("vet_login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM veterinarians WHERE vet_id=?", (session["vet_id"],))
    vet = cursor.fetchone()
    conn.close()

    return render_template("vet_dashboard.html", vet=vet)



@app.route("/vet/edit", methods=["GET", "POST"])
def vet_edit_profile():
    if "vet_id" not in session:
        flash("Please login first!", "danger")
        return redirect(url_for("vet_login"))

    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        clinic = request.form.get("clinic", "")

        # handle new photo upload
        photo_file = request.files.get("photo")
        if photo_file and photo_file.filename != "":
            filename = secure_filename(photo_file.filename)
            save_path = os.path.join(app.config["VET_UPLOAD_FOLDER"], filename)
            photo_file.save(save_path)
            photo_path = filename   # ✅ only save filename in DB

            cursor.execute("UPDATE veterinarians SET name=?, phone=?, clinic=?, photo=? WHERE vet_id=?",
                        (name, phone, clinic, photo_path, session["vet_id"]))

        else:
            cursor.execute("UPDATE veterinarians SET name=?, phone=?, clinic=? WHERE vet_id=?",
                           (name, phone, clinic, session["vet_id"]))

        conn.commit()
        conn.close()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("vet_profile"))

    cursor.execute("SELECT * FROM veterinarians WHERE vet_id=?", (session["vet_id"],))
    vet = cursor.fetchone()
    conn.close()

    return render_template("vet_edit.html", vet=vet)



@app.route("/vet/profile")
def vet_profile():
    if "vet_id" not in session:
        return redirect(url_for("vet_login"))

    conn = get_db()
    vet = conn.execute("SELECT * FROM veterinarians WHERE vet_id = ?", (session["vet_id"],)).fetchone()
    conn.close()

    return render_template("vet_profile.html", vet=vet)






@app.route('/book_appointment')
def book_appointment():
    conn = sqlite3.connect("kamadhenu.db")
    conn.row_factory = sqlite3.Row  # <--- enables dictionary access
    cursor = conn.cursor()
    cursor.execute("SELECT vet_id, name, email, phone, clinic, photo FROM veterinarians")
    vets = cursor.fetchall()
    conn.close()
    return render_template("book_appointment.html", vets=vets)

@app.route("/delete_appointment/<int:appointment_id>", methods=["POST"])
def delete_appointment(appointment_id):
    if "vet_id" not in session:
        flash("Please login first!", "danger")
        return redirect(url_for("vet_login"))

    conn = sqlite3.connect("kamadhenu.db")
    cursor = conn.cursor()

    # Ensure the appointment belongs to this vet
    cursor.execute("SELECT * FROM appointments WHERE id=? AND vet_id=?", (appointment_id, session["vet_id"]))
    appointment = cursor.fetchone()

    if not appointment:
        conn.close()
        flash("Appointment not found or unauthorized.", "danger")
        return redirect(url_for("vet_appointments"))

    cursor.execute("DELETE FROM appointments WHERE id=? AND vet_id=?", (appointment_id, session["vet_id"]))
    conn.commit()
    conn.close()

    flash("Appointment deleted successfully!", "success")
    return redirect(url_for("vet_appointments"))


from datetime import date as dt_date  # rename import to avoid conflict


@app.route('/confirm_appointment/<int:vet_id>', methods=['GET', 'POST'])
def confirm_appointment(vet_id):
    # Ensure farmer is logged in
    farmer_id = session.get("farmer_id")
    if not farmer_id:
        return redirect(url_for('farmer_login'))  # redirect to login if not logged in

    if request.method == 'POST':
        appointment_date = request.form['date']
        appointment_time = request.form['time']

        # Save appointment
        conn = sqlite3.connect("kamadhenu.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO appointments (farmer_id, vet_id, date, time) VALUES (?, ?, ?, ?)",
            (farmer_id, vet_id, appointment_date, appointment_time)
        )
        conn.commit()
        conn.close()
        flash('✅ Appointment booked successfully!', 'success')
        return redirect(url_for('book_appointment'))

    # Fetch vet details
    conn = sqlite3.connect("kamadhenu.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, clinic FROM veterinarians WHERE vet_id=?",
        (vet_id,)
    )
    vet = cursor.fetchone()
    conn.close()

    # Minimum date for date picker
    today = dt_date.today().isoformat()

    return render_template("confirm_appointment.html", vet=vet, vet_id=vet_id, today=today)






@app.route('/vet_appointments')
def vet_appointments():
    vet_id = session.get('vet_id')  # Vet must be logged in
    if not vet_id:
        flash("Please login first!", "danger")
        return redirect(url_for("vet_login"))

    conn = sqlite3.connect('kamadhenu.db')
    conn.row_factory = sqlite3.Row  # so we can access by column names
    cursor = conn.cursor()
    
    # Fetch appointments for this vet with farmer details
    cursor.execute("""
        SELECT a.id, f.name, f.phone, a.date, a.time
        FROM appointments a
        JOIN farmers f ON a.farmer_id = f.farmer_id
        WHERE a.vet_id = ?
        ORDER BY a.date, a.time
    """, (vet_id,))

    appointments = cursor.fetchall()
    conn.close()
    
    return render_template('vet_appointments.html', appointments=appointments)







# ---------------- Logout ----------------
@app.route("/farmer/logout")
def farmer_logout():
    session.clear()
    return redirect(url_for("home"))   # sends farmer back to main.html (your index page)


@app.route("/vet/logout")
def vet_logout():
    session.clear()
    return redirect(url_for("veterinarian"))

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

# ---------------- Run ----------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
