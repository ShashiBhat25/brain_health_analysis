from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import mysql.connector
import random
import os
import json
import hashlib
import base64
from datetime import datetime
from werkzeug.utils import secure_filename
import joblib
import pandas as pd
import io
import pyotp
import qrcode
from io import BytesIO

# Load environment variables (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use environment variables or defaults

app = Flask(__name__)

# Configuration from environment variables with fallbacks
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_secret_key_here_change_in_production')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 33554432))  # 32MB default
app.config['UPLOAD_FOLDER'] = 'static/uploads/prescriptions'

# Production vs Development settings
IS_PRODUCTION = os.getenv('FLASK_ENV', 'development') == 'production'

if not IS_PRODUCTION:
    # Development settings
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.jinja_env.auto_reload = True
    app.jinja_env.cache = {}
else:
    # Production settings
    app.config['TEMPLATES_AUTO_RELOAD'] = False
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year

# Load ML model
clf = joblib.load('Doctors_prescription_patient_1/Best_Model.pkl')

# -------------------- CONFIG -------------------- #

db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'root')
}

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# -------------------- HELPERS -------------------- #

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_file_hash(file_path):
    """Generate SHA-256 hash for a given file path."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def get_db_connection():
    config = db_config.copy()
    config['database'] = 'healthcare_system'
    return mysql.connector.connect(**config)

# -------------------- TOTP HELPERS -------------------- #

def generate_totp_secret():
    """Generate a new TOTP secret for a user."""
    return pyotp.random_base32()

def generate_qr_code(secret, user_email, issuer_name="Healthcare App"):
    """Generate QR code for TOTP setup."""
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=user_email,
        issuer_name=issuer_name
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 for display in HTML
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return qr_code_base64

def verify_totp_code(secret, user_code):
    """Verify TOTP code entered by user."""
    if not secret or not user_code:
        return False
    
    totp = pyotp.TOTP(secret)
    # Allow for 1 time step tolerance (30 seconds before/after)
    return totp.verify(user_code, valid_window=1)

def generate_backup_codes():
    """Generate backup codes for account recovery."""
    codes = []
    for _ in range(10):
        code = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        codes.append(code)
    return codes

def verify_backup_code(stored_codes, entered_code):
    """Verify and consume a backup code."""
    if not stored_codes or not entered_code:
        return False, stored_codes
    
    try:
        codes_list = json.loads(stored_codes) if isinstance(stored_codes, str) else stored_codes
        if entered_code in codes_list:
            codes_list.remove(entered_code)  # Use code only once
            return True, json.dumps(codes_list)
        return False, stored_codes
    except (json.JSONDecodeError, TypeError):
        return False, stored_codes


import requests



# -------------------- DB SETUP & ALTER -------------------- #

def setup_database():
    """Create database & tables if they don't exist (safe to run)."""
    conn = None
    cursor = None
    try:
        # Create database if not exists
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS healthcare_system")
        cursor.close()
        conn.close()

        # Connect to DB and create tables (will not drop existing data)
        config = db_config.copy()
        config['database'] = 'healthcare_system'
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # patients
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INT AUTO_INCREMENT PRIMARY KEY,
                aadhar_id VARCHAR(16) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL,
                password VARCHAR(100) NOT NULL,
                phone VARCHAR(15),
                date_of_birth DATE,
                address TEXT,
                blood_group VARCHAR(5),
                emergency_contact VARCHAR(15),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # doctors
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS doctors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                doctor_id VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL,
                password VARCHAR(100) NOT NULL,
                specialization VARCHAR(100),
                license_number VARCHAR(50),
                phone VARCHAR(15),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # caretaker
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS caretaker (
                id INT AUTO_INCREMENT PRIMARY KEY,
                caretaker_id VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                phone VARCHAR(15),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # caretaker_patients (relationship table)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS caretaker_patients (
                id INT AUTO_INCREMENT PRIMARY KEY,
                caretaker_id VARCHAR(20) NOT NULL,
                patient_aadhar VARCHAR(16) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (caretaker_id) REFERENCES caretaker(caretaker_id),
                FOREIGN KEY (patient_aadhar) REFERENCES patients(aadhar_id),
                UNIQUE KEY unique_caretaker_patient (caretaker_id, patient_aadhar)
            )
        ''')

        # patient_doctors
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patient_doctors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_aadhar VARCHAR(16) NOT NULL,
                doctor_id VARCHAR(20) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_aadhar) REFERENCES patients(aadhar_id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id),
                UNIQUE KEY unique_patient_doctor (patient_aadhar, doctor_id)
            )
        ''')

        # prescriptions (include digital_signature column here; alter function will also add if missing)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prescriptions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                prescription_id VARCHAR(50) UNIQUE NOT NULL,
                patient_aadhar VARCHAR(16) NOT NULL,
                doctor_id VARCHAR(20) NOT NULL,
                diagnosis TEXT,
                file_name VARCHAR(255),
                file_path VARCHAR(500),
                file_type VARCHAR(50),
                file_size INT,
                digital_signature VARCHAR(64),
                instructions TEXT,
                prescription_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_aadhar) REFERENCES patients(aadhar_id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
            )
        ''')

        # patient_otp
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patient_otp (
                id INT AUTO_INCREMENT PRIMARY KEY,
                aadhar_id VARCHAR(16) NOT NULL,
                otp VARCHAR(6) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_used BOOLEAN DEFAULT FALSE
            )
        ''')

        # brain_reports
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS brain_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                aadhar_id VARCHAR(16) NOT NULL,
                doctor_email VARCHAR(100) NOT NULL,
                result VARCHAR(50),
                features TEXT,
                graph_image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (aadhar_id) REFERENCES patients(aadhar_id)
            )
        ''')

        conn.commit()
        print("All tables created (if they didn't already exist).")
    except mysql.connector.Error as e:
        print(f"Database error during setup: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    # Add TOTP columns
    alter_tables_for_totp()

def alter_tables_for_digital_signature():
    """Add digital_signature column to prescriptions table if missing."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'healthcare_system' 
            AND TABLE_NAME = 'prescriptions' 
            AND COLUMN_NAME = 'digital_signature'
        """)
        column_exists = cursor.fetchone()[0]
        if column_exists == 0:
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN digital_signature VARCHAR(64) AFTER file_size")
            conn.commit()
            print("Added 'digital_signature' column to prescriptions table.")
        else:
            print("'digital_signature' column already exists.")
    except mysql.connector.Error as e:
        print(f"Error altering prescriptions table: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def alter_tables_for_totp():
    """Add TOTP columns to user tables if missing."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add TOTP columns to patients table
        tables_columns = [
            ('patients', 'totp_secret', 'VARCHAR(32)'),
            ('patients', 'totp_enabled', 'BOOLEAN DEFAULT FALSE'),
            ('patients', 'backup_codes', 'TEXT'),
            ('doctors', 'totp_secret', 'VARCHAR(32)'),
            ('doctors', 'totp_enabled', 'BOOLEAN DEFAULT FALSE'),
            ('doctors', 'backup_codes', 'TEXT'),
            ('caretaker', 'totp_secret', 'VARCHAR(32)'),
            ('caretaker', 'totp_enabled', 'BOOLEAN DEFAULT FALSE'),
            ('caretaker', 'backup_codes', 'TEXT')
        ]
        
        for table, column, column_type in tables_columns:
            cursor.execute(f"""
                SELECT COUNT(*) FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = 'healthcare_system' 
                AND TABLE_NAME = '{table}' 
                AND COLUMN_NAME = '{column}'
            """)
            column_exists = cursor.fetchone()[0]
            if column_exists == 0:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
                print(f"Added '{column}' column to {table} table.")
        
        conn.commit()
        print("TOTP columns added successfully.")
    except mysql.connector.Error as e:
        print(f"Error adding TOTP columns: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def alter_tables():
    """Older alter logic preserved (safe, checks for columns before altering)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Example: ensure patients.aadhar_id length
        try:
            cursor.execute("ALTER TABLE patients MODIFY aadhar_id VARCHAR(16)")
        except mysql.connector.Error:
            pass

        # Add password column to patients if missing
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = 'healthcare_system' 
            AND TABLE_NAME = 'patients' 
            AND COLUMN_NAME = 'password'
        """)
        if cursor.fetchone()[0] == 0:
            try:
                cursor.execute("ALTER TABLE patients ADD COLUMN password VARCHAR(100) NOT NULL AFTER email")
            except mysql.connector.Error:
                pass

        # Prescriptions alterations handled by alter_tables_for_digital_signature()

        # patient_otp aadhar length
        try:
            cursor.execute("ALTER TABLE patient_otp MODIFY aadhar_id VARCHAR(16)")
        except mysql.connector.Error:
            pass

        conn.commit()
    except mysql.connector.Error as e:
        print(f"Error in alter_tables: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()



# -------------------- TEMPLATE FILTER -------------------- #

@app.template_filter('fromjson')
def fromjson_filter(value):
    try:
        if isinstance(value, str):
            return json.loads(value)
        return value
    except (json.JSONDecodeError, TypeError):
        return value

# -------------------- ROUTES -------------------- #

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test-design')
def test_design():
    return render_template('test_design.html')

@app.route('/test-css')
def test_css():
    return send_file('static/test.html')

# -------------------- PATIENT ROUTES -------------------- #

@app.route('/patient/signup', methods=['GET', 'POST'])
def patient_signup():
    if request.method == 'POST':
        aadhar_id = request.form['aadhar_id']
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']  # plaintext per your request
        phone = request.form['phone']
        date_of_birth = request.form['date_of_birth']
        address = request.form['address']
        blood_group = request.form['blood_group']
        emergency_contact = request.form['emergency_contact']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO patients (aadhar_id, name, email, password, phone, date_of_birth, address, blood_group, emergency_contact)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (aadhar_id, name, email, password, phone, date_of_birth, address, blood_group, emergency_contact))
            conn.commit()
            flash('Patient registered successfully! Please login.', 'success')
            return redirect(url_for('patient_login'))
        except mysql.connector.Error as e:
            flash('Error during registration. Patient might already exist.', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('patient_signup.html')

@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        aadhar_id = request.form['aadhar_id']
        password = request.form['password']
        totp_code = request.form.get('totp_code', '')
        backup_code = request.form.get('backup_code', '')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM patients WHERE aadhar_id = %s", (aadhar_id,))
            patient = cursor.fetchone()
            
            if not patient:
                flash("User not found! Please sign up first.", "error")
                return render_template("patient_login.html")
            
            dbpass = patient["password"]
            
            if dbpass != password:
                flash("Incorrect password!", "error")
                return render_template("patient_login.html")
            
            # Check if TOTP is enabled
            if patient.get('totp_enabled', False):
                totp_secret = patient.get('totp_secret')
                
                # Try TOTP code first
                if totp_code and verify_totp_code(totp_secret, totp_code):
                    # TOTP verified successfully
                    pass
                elif backup_code:
                    # Try backup code
                    is_valid, updated_codes = verify_backup_code(patient.get('backup_codes'), backup_code)
                    if is_valid:
                        # Update backup codes in database
                        cursor.execute("UPDATE patients SET backup_codes = %s WHERE aadhar_id = %s", 
                                     (updated_codes, aadhar_id))
                        conn.commit()
                        flash("Backup code used successfully. Please consider regenerating backup codes.", "warning")
                    else:
                        flash("Invalid backup code!", "error")
                        return render_template("patient_login.html", show_totp=True)
                else:
                    flash("Please enter TOTP code or backup code!", "error")
                    return render_template("patient_login.html", show_totp=True)
            
            # Login successful
            session["user_type"] = "patient"
            session["patient_aadhar"] = aadhar_id
            flash("Login successful!", "success")
            return redirect(url_for("patient_dashboard"))

        finally:
            cursor.close()
            conn.close()

    return render_template("patient_login.html")

@app.route("/doctor/view_reports/<aadhar_id>")
def view_reports(aadhar_id):
    if 'user_type' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('doctor_login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        

        cursor.execute("SELECT email FROM doctors WHERE doctor_id = %s", (session['doctor_id'],))
        result = cursor.fetchone()

        doc_email= result['email']
        cursor.execute("""
            SELECT * FROM brain_reports 
            WHERE aadhar_id = %s AND doctor_email = %s
            ORDER BY created_at DESC
        """, (aadhar_id, doc_email))

        reports = cursor.fetchall()

    except mysql.connector.Error as e:
        flash("Error loading reports", "error")
        reports = []
    finally:
        cursor.close()
        conn.close()

    return render_template("view_reports.html", 
                           reports=reports,
                           aadhar_id=aadhar_id)






@app.route('/patient/dashboard')
def patient_dashboard():
    if 'user_type' not in session or session['user_type'] != 'patient':
        return redirect(url_for('patient_login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get patient's selected doctors
        cursor.execute('''
            SELECT d.*, pd.created_at as connected_date 
            FROM patient_doctors pd 
            JOIN doctors d ON pd.doctor_id = d.doctor_id 
            WHERE pd.patient_aadhar = %s AND pd.is_active = TRUE
        ''', (session['patient_aadhar'],))
        selected_doctors = cursor.fetchall()

        # Get all available doctors
        cursor.execute('SELECT * FROM doctors')
        all_doctors = cursor.fetchall()

        # Get patient's prescriptions
        cursor.execute('''
            SELECT p.*, d.name as doctor_name, d.specialization
            FROM prescriptions p
            JOIN doctors d ON p.doctor_id = d.doctor_id
            WHERE p.patient_aadhar = %s
            ORDER BY p.prescription_date DESC
        ''', (session['patient_aadhar'],))
        prescriptions = cursor.fetchall()

    except mysql.connector.Error as e:
        flash('Database error occurred', 'error')
        selected_doctors = []
        all_doctors = []
        prescriptions = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('patient_dashboard.html',
                           patient_aadhar=session['patient_aadhar'],
                           selected_doctors=selected_doctors,
                           all_doctors=all_doctors,
                           prescriptions=prescriptions)

@app.route('/patient/select-doctor', methods=['POST'])
def select_doctor():
    if 'user_type' not in session or session['user_type'] != 'patient':
        return redirect(url_for('patient_login'))

    doctor_id = request.form['doctor_id']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM patient_doctors 
            WHERE patient_aadhar = %s AND doctor_id = %s
        ''', (session['patient_aadhar'], doctor_id))
        existing = cursor.fetchone()

        if not existing:
            cursor.execute('''
                INSERT INTO patient_doctors (patient_aadhar, doctor_id)
                VALUES (%s, %s)
            ''', (session['patient_aadhar'], doctor_id))
            conn.commit()
            flash('Doctor added successfully!', 'success')
        else:
            flash('Doctor is already in your list!', 'warning')
    except mysql.connector.Error as e:
        print(f"Select doctor error: {e}")
        flash('Error selecting doctor', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for('patient_dashboard'))

@app.route('/patient/remove-doctor/<doctor_id>')
def remove_doctor(doctor_id):
    if 'user_type' not in session or session['user_type'] != 'patient':
        return redirect(url_for('patient_login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM patient_doctors 
            WHERE patient_aadhar = %s AND doctor_id = %s
        ''', (session['patient_aadhar'], doctor_id))
        conn.commit()
        flash('Doctor removed successfully!', 'success')
    except mysql.connector.Error as e:
        print(f"Remove doctor error: {e}")
        flash('Error removing doctor', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for('patient_dashboard'))

@app.route('/patient/setup-totp', methods=['GET', 'POST'])
def patient_setup_totp():
    if 'user_type' not in session or session['user_type'] != 'patient':
        return redirect(url_for('patient_login'))
    
    if request.method == 'POST':
        totp_code = request.form.get('totp_code')
        
        if 'temp_totp_secret' not in session:
            flash('TOTP setup session expired. Please try again.', 'error')
            return redirect(url_for('patient_setup_totp'))
        
        secret = session['temp_totp_secret']
        
        if verify_totp_code(secret, totp_code):
            # Generate backup codes
            backup_codes = generate_backup_codes()
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE patients 
                    SET totp_secret = %s, totp_enabled = TRUE, backup_codes = %s 
                    WHERE aadhar_id = %s
                ''', (secret, json.dumps(backup_codes), session['patient_aadhar']))
                conn.commit()
                
                # Clear temp secret
                session.pop('temp_totp_secret', None)
                
                flash('TOTP enabled successfully!', 'success')
                return render_template('totp_backup_codes.html', 
                                     backup_codes=backup_codes, 
                                     user_type='patient')
                
            except mysql.connector.Error as e:
                flash('Error enabling TOTP. Please try again.', 'error')
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
        else:
            flash('Invalid TOTP code. Please try again.', 'error')
    
    # Generate new secret and QR code
    secret = generate_totp_secret()
    session['temp_totp_secret'] = secret
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT email FROM patients WHERE aadhar_id = %s", (session['patient_aadhar'],))
        patient = cursor.fetchone()
        user_email = patient['email'] if patient else session['patient_aadhar']
    except:
        user_email = session['patient_aadhar']
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    qr_code = generate_qr_code(secret, user_email)
    
    return render_template('setup_totp.html', 
                         qr_code=qr_code, 
                         secret=secret,
                         user_type='patient')

@app.route('/patient/disable-totp', methods=['POST'])
def patient_disable_totp():
    if 'user_type' not in session or session['user_type'] != 'patient':
        return redirect(url_for('patient_login'))
    
    password = request.form.get('password')
    totp_code = request.form.get('totp_code')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM patients WHERE aadhar_id = %s", (session['patient_aadhar'],))
        patient = cursor.fetchone()
        
        if not patient or patient['password'] != password:
            flash('Incorrect password!', 'error')
            return redirect(url_for('patient_profile'))
        
        if patient.get('totp_enabled') and not verify_totp_code(patient.get('totp_secret'), totp_code):
            flash('Invalid TOTP code!', 'error')
            return redirect(url_for('patient_profile'))
        
        cursor.execute('''
            UPDATE patients 
            SET totp_secret = NULL, totp_enabled = FALSE, backup_codes = NULL 
            WHERE aadhar_id = %s
        ''', (session['patient_aadhar'],))
        conn.commit()
        
        flash('TOTP disabled successfully!', 'success')
        
    except mysql.connector.Error as e:
        flash('Error disabling TOTP. Please try again.', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('patient_profile'))

@app.route('/patient/regenerate-backup-codes', methods=['POST'])
def patient_regenerate_backup_codes():
    if 'user_type' not in session or session['user_type'] != 'patient':
        return redirect(url_for('patient_login'))
    
    password = request.form.get('password')
    totp_code = request.form.get('totp_code')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM patients WHERE aadhar_id = %s", (session['patient_aadhar'],))
        patient = cursor.fetchone()
        
        if not patient or patient['password'] != password:
            flash('Incorrect password!', 'error')
            return redirect(url_for('patient_profile'))
        
        if not patient.get('totp_enabled'):
            flash('TOTP is not enabled!', 'error')
            return redirect(url_for('patient_profile'))
        
        if not verify_totp_code(patient.get('totp_secret'), totp_code):
            flash('Invalid TOTP code!', 'error')
            return redirect(url_for('patient_profile'))
        
        # Generate new backup codes
        backup_codes = generate_backup_codes()
        
        cursor.execute('''
            UPDATE patients SET backup_codes = %s WHERE aadhar_id = %s
        ''', (json.dumps(backup_codes), session['patient_aadhar']))
        conn.commit()
        
        flash('Backup codes regenerated successfully!', 'success')
        return render_template('totp_backup_codes.html', 
                             backup_codes=backup_codes, 
                             user_type='patient')
        
    except mysql.connector.Error as e:
        flash('Error regenerating backup codes. Please try again.', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('patient_profile'))

# -------------------- DOCTOR ROUTES -------------------- #

@app.route('/doctor/signup', methods=['GET', 'POST'])
def doctor_signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        specialization = request.form['specialization']
        license_number = request.form['license_number']
        phone = request.form['phone']
        
        # Auto-generate doctor_id
        doctor_id = f"DR{random.randint(100000, 999999)}"

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO doctors (doctor_id, name, email, password, specialization, license_number, phone)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (doctor_id, name, email, password, specialization, license_number, phone))
            conn.commit()
            flash('Doctor registered successfully!', 'success')
            return redirect(url_for('doctor_login'))
        except mysql.connector.Error as e:
            flash('Error during registration. Email might already exist.', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('doctor_signup.html')

@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        totp_code = request.form.get('totp_code', '')
        backup_code = request.form.get('backup_code', '')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM doctors WHERE email = %s', (email,))
            doctor = cursor.fetchone()
            
            if not doctor:
                flash('User not found! Please sign up first.', 'error')
                return render_template('doctor_login.html')
            
            if doctor['password'] != password:
                flash('Incorrect password!', 'error')
                return render_template('doctor_login.html')
            
            # Check if TOTP is enabled
            if doctor.get('totp_enabled', False):
                # If TOTP is enabled but no code provided, show TOTP form
                if not totp_code and not backup_code:
                    return render_template("doctor_login.html", show_totp=True, email=email)
                
                totp_secret = doctor.get('totp_secret')
                
                # Try TOTP code first
                if totp_code and verify_totp_code(totp_secret, totp_code):
                    # TOTP verified successfully
                    pass
                elif backup_code:
                    # Try backup code
                    is_valid, updated_codes = verify_backup_code(doctor.get('backup_codes'), backup_code)
                    if is_valid:
                        # Update backup codes in database
                        cursor.execute("UPDATE doctors SET backup_codes = %s WHERE doctor_id = %s", 
                                     (updated_codes, doctor['doctor_id']))
                        conn.commit()
                        flash("Backup code used successfully. Please consider regenerating backup codes.", "warning")
                    else:
                        flash("Invalid backup code!", "error")
                        return render_template("doctor_login.html", show_totp=True, email=email)
                else:
                    flash("Please enter TOTP code or backup code!", "error")
                    return render_template("doctor_login.html", show_totp=True, email=email)
            
            # Login successful
            session['doctor_id'] = doctor['doctor_id']
            session['doctor_name'] = doctor['name']
            session['user_type'] = 'doctor'
            flash('Login successful!', 'success')
            return redirect(url_for('doctor_dashboard'))
                
        except mysql.connector.Error as e:
            print(f"Doctor login error: {e}")
            flash('Database error occurred', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    return render_template('doctor_login.html')

@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'user_type' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('doctor_login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get patients who have selected this doctor
        cursor.execute('''
            SELECT p.*, pd.created_at as connected_date 
            FROM patient_doctors pd 
            JOIN patients p ON pd.patient_aadhar = p.aadhar_id 
            WHERE pd.doctor_id = %s AND pd.is_active = TRUE
        ''', (session['doctor_id'],))
        my_patients = cursor.fetchall()
    except mysql.connector.Error as e:
        print(f"Doctor dashboard error: {e}")
        flash('Database error occurred', 'error')
        my_patients = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('doctor_dashboard.html', my_patients=my_patients)

@app.route('/doctor/setup-totp', methods=['GET', 'POST'])
def doctor_setup_totp():
    if 'user_type' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('doctor_login'))
    
    if request.method == 'POST':
        totp_code = request.form.get('totp_code')
        
        if 'temp_totp_secret' not in session:
            flash('TOTP setup session expired. Please try again.', 'error')
            return redirect(url_for('doctor_setup_totp'))
        
        secret = session['temp_totp_secret']
        
        if verify_totp_code(secret, totp_code):
            # Generate backup codes
            backup_codes = generate_backup_codes()
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE doctors 
                    SET totp_secret = %s, totp_enabled = TRUE, backup_codes = %s 
                    WHERE doctor_id = %s
                ''', (secret, json.dumps(backup_codes), session['doctor_id']))
                conn.commit()
                
                # Clear temp secret
                session.pop('temp_totp_secret', None)
                
                flash('TOTP enabled successfully!', 'success')
                return render_template('totp_backup_codes.html', 
                                     backup_codes=backup_codes, 
                                     user_type='doctor')
                
            except mysql.connector.Error as e:
                flash('Error enabling TOTP. Please try again.', 'error')
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
        else:
            flash('Invalid TOTP code. Please try again.', 'error')
    
    # Generate new secret and QR code
    secret = generate_totp_secret()
    session['temp_totp_secret'] = secret
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT email FROM doctors WHERE doctor_id = %s", (session['doctor_id'],))
        doctor = cursor.fetchone()
        user_email = doctor['email'] if doctor else session['doctor_id']
    except:
        user_email = session['doctor_id']
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    qr_code = generate_qr_code(secret, user_email)
    
    return render_template('setup_totp.html', 
                         qr_code=qr_code, 
                         secret=secret,
                         user_type='doctor')

@app.route('/doctor/disable-totp', methods=['POST'])
def doctor_disable_totp():
    if 'user_type' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('doctor_login'))
    
    password = request.form.get('password')
    totp_code = request.form.get('totp_code')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM doctors WHERE doctor_id = %s", (session['doctor_id'],))
        doctor = cursor.fetchone()
        
        if not doctor or doctor['password'] != password:
            flash('Incorrect password!', 'error')
            return redirect(url_for('doctor_profile'))
        
        if doctor.get('totp_enabled') and not verify_totp_code(doctor.get('totp_secret'), totp_code):
            flash('Invalid TOTP code!', 'error')
            return redirect(url_for('doctor_profile'))
        
        cursor.execute('''
            UPDATE doctors 
            SET totp_secret = NULL, totp_enabled = FALSE, backup_codes = NULL 
            WHERE doctor_id = %s
        ''', (session['doctor_id'],))
        conn.commit()
        
        flash('TOTP disabled successfully!', 'success')
        
    except mysql.connector.Error as e:
        flash('Error disabling TOTP. Please try again.', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('doctor_profile'))

@app.route('/doctor/regenerate-backup-codes', methods=['POST'])
def doctor_regenerate_backup_codes():
    if 'user_type' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('doctor_login'))
    
    password = request.form.get('password')
    totp_code = request.form.get('totp_code')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM doctors WHERE doctor_id = %s", (session['doctor_id'],))
        doctor = cursor.fetchone()
        
        if not doctor or doctor['password'] != password:
            flash('Incorrect password!', 'error')
            return redirect(url_for('doctor_profile'))
        
        if not doctor.get('totp_enabled'):
            flash('TOTP is not enabled!', 'error')
            return redirect(url_for('doctor_profile'))
        
        if not verify_totp_code(doctor.get('totp_secret'), totp_code):
            flash('Invalid TOTP code!', 'error')
            return redirect(url_for('doctor_profile'))
        
        # Generate new backup codes
        backup_codes = generate_backup_codes()
        
        cursor.execute('''
            UPDATE doctors SET backup_codes = %s WHERE doctor_id = %s
        ''', (json.dumps(backup_codes), session['doctor_id']))
        conn.commit()
        
        flash('Backup codes regenerated successfully!', 'success')
        return render_template('totp_backup_codes.html', 
                             backup_codes=backup_codes, 
                             user_type='doctor')
        
    except mysql.connector.Error as e:
        flash('Error regenerating backup codes. Please try again.', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('doctor_profile'))

@app.route('/caretaker/setup-totp', methods=['GET', 'POST'])
def caretaker_setup_totp():
    if 'user_type' not in session or session['user_type'] != 'caretaker':
        return redirect(url_for('caretaker_login'))
    
    if request.method == 'POST':
        totp_code = request.form.get('totp_code')
        
        if 'temp_totp_secret' not in session:
            flash('TOTP setup session expired. Please try again.', 'error')
            return redirect(url_for('caretaker_setup_totp'))
        
        secret = session['temp_totp_secret']
        
        if verify_totp_code(secret, totp_code):
            # Generate backup codes
            backup_codes = generate_backup_codes()
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE caretaker 
                    SET totp_secret = %s, totp_enabled = TRUE, backup_codes = %s 
                    WHERE caretaker_id = %s
                ''', (secret, json.dumps(backup_codes), session['caretaker_id']))
                conn.commit()
                
                # Clear temp secret
                session.pop('temp_totp_secret', None)
                
                flash('TOTP enabled successfully!', 'success')
                return render_template('totp_backup_codes.html', 
                                     backup_codes=backup_codes, 
                                     user_type='caretaker')
                
            except mysql.connector.Error as e:
                flash('Error enabling TOTP. Please try again.', 'error')
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
        else:
            flash('Invalid TOTP code. Please try again.', 'error')
    
    # Generate new secret and QR code
    secret = generate_totp_secret()
    session['temp_totp_secret'] = secret
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT email FROM caretaker WHERE caretaker_id = %s", (session['caretaker_id'],))
        caretaker = cursor.fetchone()
        user_email = caretaker['email'] if caretaker else session['caretaker_id']
    except:
        user_email = session['caretaker_id']
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    qr_code = generate_qr_code(secret, user_email)
    
    return render_template('setup_totp.html', 
                         qr_code=qr_code, 
                         secret=secret,
                         user_type='caretaker')

@app.route('/caretaker/disable-totp', methods=['POST'])
def caretaker_disable_totp():
    if 'user_type' not in session or session['user_type'] != 'caretaker':
        return redirect(url_for('caretaker_login'))
    
    password = request.form.get('password')
    totp_code = request.form.get('totp_code')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM caretaker WHERE caretaker_id = %s", (session['caretaker_id'],))
        caretaker = cursor.fetchone()
        
        if not caretaker or caretaker['password'] != password:
            flash('Incorrect password!', 'error')
            return redirect(url_for('caretaker_profile'))
        
        if caretaker.get('totp_enabled') and not verify_totp_code(caretaker.get('totp_secret'), totp_code):
            flash('Invalid TOTP code!', 'error')
            return redirect(url_for('caretaker_profile'))
        
        cursor.execute('''
            UPDATE caretaker 
            SET totp_secret = NULL, totp_enabled = FALSE, backup_codes = NULL 
            WHERE caretaker_id = %s
        ''', (session['caretaker_id'],))
        conn.commit()
        
        flash('TOTP disabled successfully!', 'success')
        
    except mysql.connector.Error as e:
        flash('Error disabling TOTP. Please try again.', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('caretaker_profile'))

@app.route('/caretaker/regenerate-backup-codes', methods=['POST'])
def caretaker_regenerate_backup_codes():
    if 'user_type' not in session or session['user_type'] != 'caretaker':
        return redirect(url_for('caretaker_login'))
    
    password = request.form.get('password')
    totp_code = request.form.get('totp_code')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM caretaker WHERE caretaker_id = %s", (session['caretaker_id'],))
        caretaker = cursor.fetchone()
        
        if not caretaker or caretaker['password'] != password:
            flash('Incorrect password!', 'error')
            return redirect(url_for('caretaker_profile'))
        
        if not caretaker.get('totp_enabled'):
            flash('TOTP is not enabled!', 'error')
            return redirect(url_for('caretaker_profile'))
        
        if not verify_totp_code(caretaker.get('totp_secret'), totp_code):
            flash('Invalid TOTP code!', 'error')
            return redirect(url_for('caretaker_profile'))
        
        # Generate new backup codes
        backup_codes = generate_backup_codes()
        
        cursor.execute('''
            UPDATE caretaker SET backup_codes = %s WHERE caretaker_id = %s
        ''', (json.dumps(backup_codes), session['caretaker_id']))
        conn.commit()
        
        flash('Backup codes regenerated successfully!', 'success')
        return render_template('totp_backup_codes.html', 
                             backup_codes=backup_codes, 
                             user_type='caretaker')
        
    except mysql.connector.Error as e:
        flash('Error regenerating backup codes. Please try again.', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('caretaker_profile'))

@app.route('/doctor/search-patient', methods=['GET', 'POST'])
def search_patient():
    if 'user_type' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('doctor_login'))

    if request.method == 'POST':
        aadhar_id = request.form['aadhar_id']
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT p.*, 
                       CASE WHEN pd.doctor_id IS NOT NULL THEN TRUE ELSE FALSE END as is_my_patient
                FROM patients p 
                LEFT JOIN patient_doctors pd ON p.aadhar_id = pd.patient_aadhar AND pd.doctor_id = %s
                WHERE p.aadhar_id = %s
            ''', (session['doctor_id'], aadhar_id))
            patient = cursor.fetchone()
            if patient:
                if patient['is_my_patient']:
                    
                    session['verified_aadhar'] = aadhar_id
                    flash('OTP verified successfully!', 'success')
                    return redirect(url_for('patient_details'))
                else:
                    flash('This patient has not selected you as their doctor!', 'error')
            else:
                
                
                flash('Patient not found. Signup invitation sent!', 'warning')
        except mysql.connector.Error as e:
            print(f"Search patient error: {e}")
            flash('Database error occurred', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('patient_search.html')

@app.route('/doctor/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'user_type' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('doctor_login'))

    if 'search_aadhar' not in session:
        return redirect(url_for('search_patient'))

    if request.method == 'POST':
        otp = request.form['otp']
        aadhar_id = session['search_aadhar']
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM patient_otp 
                WHERE aadhar_id = %s AND otp = %s AND expires_at > NOW() AND is_used = FALSE
            ''', (aadhar_id, otp))
            result = cursor.fetchone()
            if result:
                cursor.execute('UPDATE patient_otp SET is_used = TRUE WHERE id = %s', (result[0],))
                conn.commit()
                session['verified_aadhar'] = aadhar_id
                flash('OTP verified successfully!', 'success')
                return redirect(url_for('patient_details'))
            else:
                flash('Invalid or expired OTP!', 'error')
        except mysql.connector.Error as e:
            print(f"Verify OTP error: {e}")
            flash('Database error occurred', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('verify_otp.html')

@app.route('/doctor/patient-details')
def patient_details():
    if 'user_type' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('doctor_login'))

    if 'verified_aadhar' not in session:
        return redirect(url_for('search_patient'))

    aadhar_id = session['verified_aadhar']
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM patients WHERE aadhar_id = %s', (aadhar_id,))
        patient = cursor.fetchone()

        # Get patient prescriptions (only from this doctor)
        cursor.execute('''
            SELECT p.*, d.name as doctor_name 
            FROM prescriptions p 
            JOIN doctors d ON p.doctor_id = d.doctor_id 
            WHERE p.patient_aadhar = %s AND p.doctor_id = %s
            ORDER BY p.prescription_date DESC
        ''', (aadhar_id, session['doctor_id']))
        prescriptions = cursor.fetchall()
    except mysql.connector.Error as e:
        print(f"Patient details error: {e}")
        flash('Database error occurred', 'error')
        patient = None
        prescriptions = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('patient_details.html', patient=patient, prescriptions=prescriptions)

@app.route('/doctor/create-prescription', methods=['GET', 'POST'])
def create_prescription():
    if 'user_type' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('doctor_login'))

    if 'verified_aadhar' not in session:
        return redirect(url_for('search_patient'))

    if request.method == 'POST':
        diagnosis = request.form.get('diagnosis')
        instructions = request.form.get('instructions')
        patient_aadhar = session['verified_aadhar']
        doctor_id = session['doctor_id']
        camera_photo = request.form.get('camera_photo')  # base64 data url if present

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            prescription_id = f"RX{random.randint(100000, 999999)}"

            filename = None
            file_path = None
            file_type = None
            file_size = 0
            digital_signature = None

            # File upload (optional)
            if 'prescription_file' in request.files and request.files['prescription_file'].filename:
                file = request.files['prescription_file']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{prescription_id}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file_path = file_path.replace("\\", "/")
                    file.save(file_path)
                    file_size = os.path.getsize(file_path)
                    file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown'
                    digital_signature = generate_file_hash(file_path)
                else:
                    flash('Invalid file type. Allowed types: PNG, JPG, JPEG, GIF, PDF, DOC, DOCX', 'error')
                    return redirect(request.url)

            # Camera photo (optional)
            elif camera_photo:
                try:
                    if camera_photo.startswith('data:image/'):
                        header, base64_data = camera_photo.split(',', 1)
                        if 'jpeg' in header or 'jpg' in header:
                            file_type = 'jpg'
                            filename = f"{prescription_id}_camera_photo.jpg"
                        elif 'png' in header:
                            file_type = 'png'
                            filename = f"{prescription_id}_camera_photo.png"
                        else:
                            file_type = 'jpg'
                            filename = f"{prescription_id}_camera_photo.jpg"

                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file_path = file_path.replace("\\", "/")

                        image_data = base64.b64decode(base64_data)
                        with open(file_path, 'wb') as f:
                            f.write(image_data)

                        file_size = os.path.getsize(file_path)
                        digital_signature = generate_file_hash(file_path)
                    else:
                        flash('Invalid camera photo data', 'error')
                        return redirect(request.url)
                except Exception as e:
                    flash(f'Error processing camera photo: {str(e)}', 'error')
                    return redirect(request.url)

            # Insert prescription record including digital_signature
            cursor.execute('''
                INSERT INTO prescriptions (prescription_id, patient_aadhar, doctor_id, 
                diagnosis, file_name, file_path, file_type, file_size, digital_signature, instructions, prescription_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (prescription_id, patient_aadhar, doctor_id, diagnosis, filename,
                  file_path, file_type, file_size, digital_signature, instructions, datetime.now().date()))
            conn.commit()

            

            flash(f'Prescription uploaded successfully! ID: {prescription_id}', 'success')
            return redirect(url_for('patient_details'))

        except mysql.connector.Error as e:
            print(f"Create prescription DB error: {e}")
            flash('Error creating prescription', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('create_prescription.html')

# -------------------- caretaker ROUTES -------------------- #

@app.route('/caretaker/signup', methods=['GET', 'POST'])
def caretaker_signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        patient_aadhar = request.form['patient_aadhar']
        phone = request.form['phone']
        
        # Auto-generate caretaker_id
        caretaker_id = f"CT{random.randint(100000, 999999)}"

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Check if patient exists
            cursor.execute('SELECT * FROM patients WHERE aadhar_id = %s', (patient_aadhar,))
            patient = cursor.fetchone()
            
            if not patient:
                flash('Patient with this Aadhar ID not found! Patient must sign up first.', 'error')
                return render_template('caretaker_signup.html')
            
            # Insert caretaker
            cursor.execute('''
                INSERT INTO caretaker (caretaker_id, name, email, password, phone)
                VALUES (%s, %s, %s, %s, %s)
            ''', (caretaker_id, name, email, password, phone))
            
            # Link caretaker to patient
            cursor.execute('''
                INSERT INTO caretaker_patients (caretaker_id, patient_aadhar)
                VALUES (%s, %s)
            ''', (caretaker_id, patient_aadhar))
            
            conn.commit()
            flash('Caretaker registered successfully!', 'success')
            return redirect(url_for('caretaker_login'))
        except mysql.connector.Error as e:
            flash('Error during registration. Email might already exist.', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('caretaker_signup.html')

@app.route('/caretaker/login', methods=['GET', 'POST'])
def caretaker_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        totp_code = request.form.get('totp_code', '')
        backup_code = request.form.get('backup_code', '')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM caretaker WHERE email = %s', (email,))
            caretaker = cursor.fetchone()
            
            if not caretaker:
                flash('User not found! Please sign up first.', 'error')
                return render_template('caretaker_login.html')
            
            if caretaker['password'] != password:
                flash('Incorrect password!', 'error')
                return render_template('caretaker_login.html')
            
            # Check if TOTP is enabled
            if caretaker.get('totp_enabled', False):
                # If TOTP is enabled but no code provided, show TOTP form
                if not totp_code and not backup_code:
                    return render_template("caretaker_login.html", show_totp=True, email=email)
                
                totp_secret = caretaker.get('totp_secret')
                
                # Try TOTP code first
                if totp_code and verify_totp_code(totp_secret, totp_code):
                    # TOTP verified successfully
                    pass
                elif backup_code:
                    # Try backup code
                    is_valid, updated_codes = verify_backup_code(caretaker.get('backup_codes'), backup_code)
                    if is_valid:
                        # Update backup codes in database
                        cursor.execute("UPDATE caretaker SET backup_codes = %s WHERE caretaker_id = %s", 
                                     (updated_codes, caretaker['caretaker_id']))
                        conn.commit()
                        flash("Backup code used successfully. Please consider regenerating backup codes.", "warning")
                    else:
                        flash("Invalid backup code!", "error")
                        return render_template("caretaker_login.html", show_totp=True, email=email)
                else:
                    flash("Please enter TOTP code or backup code!", "error")
                    return render_template("caretaker_login.html", show_totp=True, email=email)
            
            # Login successful
            session['caretaker_id'] = caretaker['caretaker_id']
            session['caretaker_name'] = caretaker['name']
            session['user_type'] = 'caretaker'
            flash('Login successful!', 'success')
            return redirect(url_for('caretaker_dashboard'))
                
        except mysql.connector.Error as e:
            print(f"Caretaker login error: {e}")
            flash('Database error occurred', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    return render_template('caretaker_login.html')

@app.route('/caretaker/dashboard')
def caretaker_dashboard():
    if 'user_type' not in session or session['user_type'] != 'caretaker':
        return redirect(url_for('caretaker_login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get caretaker's patients
        cursor.execute('''
            SELECT p.*, cp.created_at as connected_date 
            FROM caretaker_patients cp 
            JOIN patients p ON cp.patient_aadhar = p.aadhar_id 
            WHERE cp.caretaker_id = %s AND cp.is_active = TRUE
        ''', (session['caretaker_id'],))
        my_patients = cursor.fetchall()
    except mysql.connector.Error as e:
        flash('Database error occurred', 'error')
        my_patients = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('caretaker_dashboard.html', my_patients=my_patients)

@app.route('/caretaker/profile', methods=['GET', 'POST'])
def caretaker_profile():
    if 'user_type' not in session or session['user_type'] != 'caretaker':
        return redirect(url_for('caretaker_login'))
    
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            
            if new_password:
                cursor.execute('SELECT password FROM caretaker WHERE caretaker_id = %s', (session['caretaker_id'],))
                result = cursor.fetchone()
                if result and result[0] == current_password:
                    cursor.execute('''
                        UPDATE caretaker SET name=%s, email=%s, phone=%s, password=%s 
                        WHERE caretaker_id=%s
                    ''', (name, email, phone, new_password, session['caretaker_id']))
                else:
                    flash('Current password is incorrect!', 'error')
                    return redirect(url_for('caretaker_profile'))
            else:
                cursor.execute('''
                    UPDATE caretaker SET name=%s, email=%s, phone=%s 
                    WHERE caretaker_id=%s
                ''', (name, email, phone, session['caretaker_id']))
            
            conn.commit()
            flash('Profile updated successfully!', 'success')
            
        except mysql.connector.Error as e:
            flash('Error updating profile', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
        return redirect(url_for('caretaker_profile'))
    
    # GET request
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM caretaker WHERE caretaker_id = %s', (session['caretaker_id'],))
        caretaker = cursor.fetchone()
    except mysql.connector.Error as e:
        caretaker = None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('caretaker_profile.html', caretaker=caretaker)

@app.route('/caretaker/add-patient', methods=['POST'])
def caretaker_add_patient():
    if 'user_type' not in session or session['user_type'] != 'caretaker':
        return redirect(url_for('caretaker_login'))
    
    patient_aadhar = request.form['patient_aadhar']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if patient exists
        cursor.execute('SELECT * FROM patients WHERE aadhar_id = %s', (patient_aadhar,))
        patient = cursor.fetchone()
        
        if not patient:
            flash('Patient with this Aadhar ID not found!', 'error')
            return redirect(url_for('caretaker_dashboard'))
        
        # Check if already added
        cursor.execute('''
            SELECT id FROM caretaker_patients 
            WHERE caretaker_id = %s AND patient_aadhar = %s
        ''', (session['caretaker_id'], patient_aadhar))
        existing = cursor.fetchone()
        
        if existing:
            flash('Patient is already in your list!', 'warning')
        else:
            cursor.execute('''
                INSERT INTO caretaker_patients (caretaker_id, patient_aadhar)
                VALUES (%s, %s)
            ''', (session['caretaker_id'], patient_aadhar))
            conn.commit()
            flash('Patient added successfully!', 'success')
            
    except mysql.connector.Error as e:
        flash('Error adding patient', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('caretaker_dashboard'))

@app.route('/caretaker/remove-patient/<patient_aadhar>')
def caretaker_remove_patient(patient_aadhar):
    if 'user_type' not in session or session['user_type'] != 'caretaker':
        return redirect(url_for('caretaker_login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM caretaker_patients 
            WHERE caretaker_id = %s AND patient_aadhar = %s
        ''', (session['caretaker_id'], patient_aadhar))
        conn.commit()
        flash('Patient removed successfully!', 'success')
    except mysql.connector.Error as e:
        flash('Error removing patient', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('caretaker_dashboard'))

@app.route('/caretaker/patient-prescriptions/<patient_aadhar>')
def caretaker_patient_prescriptions(patient_aadhar):
    if 'user_type' not in session or session['user_type'] != 'caretaker':
        return redirect(url_for('caretaker_login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify caretaker has access to this patient
        cursor.execute("""
            SELECT cp.*, p.name as patient_name 
            FROM caretaker_patients cp
            JOIN patients p ON cp.patient_aadhar = p.aadhar_id
            WHERE cp.caretaker_id = %s AND cp.patient_aadhar = %s AND cp.is_active = TRUE
        """, (session['caretaker_id'], patient_aadhar))
        access = cursor.fetchone()

        if not access:
            flash("You don't have access to this patient's records.", "error")
            return redirect(url_for('caretaker_dashboard'))

        # Get patient details
        cursor.execute("SELECT * FROM patients WHERE aadhar_id = %s", (patient_aadhar,))
        patient = cursor.fetchone()

        # Get prescriptions
        cursor.execute("""
            SELECT p.*, d.name AS doctor_name, d.specialization
            FROM prescriptions p
            JOIN doctors d ON p.doctor_id = d.doctor_id
            WHERE p.patient_aadhar = %s
            ORDER BY p.prescription_date DESC
        """, (patient_aadhar,))
        prescriptions = cursor.fetchall()

    except mysql.connector.Error as e:
        flash("Database error", "error")
        return redirect(url_for('caretaker_dashboard'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("caretaker_prescriptions.html", prescriptions=prescriptions, patient=patient)

@app.route('/caretaker/search-prescriptions', methods=['GET', 'POST'])
def search_prescriptions():
    if 'user_type' not in session or session['user_type'] != 'caretaker':
        return redirect(url_for('caretaker_login'))

    if request.method == 'POST':
        aadhar_id = request.form['aadhar_id']
        return redirect(url_for('caretaker_patient_prescriptions', patient_aadhar=aadhar_id))

    return render_template("search_prescriptions.html", prescriptions=[], patient=None)


@app.route('/caretaker/verify-otp', methods=['GET', 'POST'])
def caretaker_verify_otp():
    if 'user_type' not in session or session['user_type'] != 'caretaker':
        return redirect(url_for('caretaker_login'))

    if 'caretaker_aadhar' not in session:
        return redirect(url_for('search_prescriptions'))

    aadhar_id = session['caretaker_aadhar']

    if request.method == 'POST':
        otp = request.form['otp']

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT id FROM patient_otp 
                WHERE aadhar_id = %s AND otp = %s 
                AND expires_at > NOW() AND is_used = FALSE
            """, (aadhar_id, otp))

            result = cursor.fetchone()

            if result:
                # Mark OTP as used
                cursor.execute("UPDATE patient_otp SET is_used = TRUE WHERE id = %s", (result["id"],))
                conn.commit()

                # OTP verified → allow showing prescriptions
                return redirect(url_for("caretaker_view_prescriptions"))

            else:
                flash("Invalid or expired OTP!", "error")

        except mysql.connector.Error as e:
            print("Verify OTP error:", e)
            flash("Database error", "error")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("caretaker_verify_otp.html")

@app.route('/caretaker/view-prescriptions')
def caretaker_view_prescriptions():
    if 'user_type' not in session or session['user_type'] != 'caretaker':
        return redirect(url_for('caretaker_login'))

    if 'caretaker_aadhar' not in session:
        return redirect(url_for('search_prescriptions'))

    aadhar_id = session['caretaker_aadhar']

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify caretaker has access to this patient
        cursor.execute("""
            SELECT id FROM caretaker_patients 
            WHERE caretaker_id = %s AND patient_aadhar = %s AND is_active = TRUE
        """, (session['caretaker_id'], aadhar_id))
        access = cursor.fetchone()

        if not access:
            flash("You don't have access to this patient's records.", "error")
            return redirect(url_for('caretaker_dashboard'))

        cursor.execute("SELECT * FROM patients WHERE aadhar_id = %s", (aadhar_id,))
        patient = cursor.fetchone()

        cursor.execute("""
            SELECT p.*, d.name AS doctor_name, d.specialization
            FROM prescriptions p
            JOIN doctors d ON p.doctor_id = d.doctor_id
            WHERE p.patient_aadhar = %s
            ORDER BY p.prescription_date DESC
        """, (aadhar_id,))
        prescriptions = cursor.fetchall()

    except mysql.connector.Error as e:
        flash("Database error", "error")
        return redirect(url_for('caretaker_dashboard'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("search_prescriptions.html", prescriptions=prescriptions, patient=patient)


# -------------------- VERIFY SIGNATURE ROUTE -------------------- #

@app.route('/verify-signature/<int:prescription_id>')
def verify_signature(prescription_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT file_path, digital_signature FROM prescriptions WHERE id = %s", (prescription_id,))
        record = cursor.fetchone()
    except mysql.connector.Error as e:
        print(f"Verify signature DB error: {e}")
        record = None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    if not record or not record.get('file_path') or not os.path.exists(record['file_path']):
        return jsonify({"status": "error", "message": "File not found"})

    current_hash = generate_file_hash(record['file_path'])
    if current_hash == record.get('digital_signature'):
        return jsonify({"status": "verified", "message": "File integrity verified"})
    else:
        return jsonify({"status": "tampered", "message": "File integrity check failed"})
def analyze_brain_signal(features):
    global clf
    
    # Ensure features is a list of 85 numeric values
    if isinstance(features, str):
        # If string, try to parse as comma-separated values
        try:
            features = [float(x.strip()) for x in features.split(',')]
        except:
            return "Error: Invalid input format"
    
    # Convert to list if needed
    if not isinstance(features, list):
        features = list(features)
    
    # Validate feature count
    if len(features) != 85:
        return f"Error: Expected 85 features, got {len(features)}"
    
    # Ensure all values are numeric
    try:
        features = [float(f) for f in features]
    except:
        return "Error: All features must be numeric"
    
    # Make prediction
    try:
        Class = clf.predict([features])
        
        if Class[0] == 0:
            result = "Normal"
        elif Class[0] == 1:
            result = "Pre-seizure"
        elif Class[0] == 2:
            result = "Seizure"
        elif Class[0] == 3:
            result = "Post-seizure"
        else:
            result = f"Unknown class: {Class[0]}"
        
        return result
    except Exception as e:
        return f"Error during prediction: {str(e)}"
@app.route("/brain_signal_ai/<aadhar_id>", methods=["GET", "POST"])
def brain_signal_ai(aadhar_id):
    if request.method == "POST":
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get patient's selected doctors
        cursor.execute('''
            SELECT d.*, pd.created_at as connected_date 
            FROM patient_doctors pd 
            JOIN doctors d ON pd.doctor_id = d.doctor_id 
            WHERE pd.patient_aadhar = %s AND pd.is_active = TRUE
        ''', (session['patient_aadhar'],))
        selected_doctors = cursor.fetchall()
        # ------------------------------
        # MANUAL F1–F85 ENTRIES
        # ------------------------------
        manual_features = {}
        for i in range(1, 86):   # F1 to F85
            value = request.form.get(f"F{i}")
            if value and value.strip() != "":
                manual_features[f"F{i}"] = float(value.strip())

        # If manual fields exist → process them
        if manual_features:
            result = analyze_brain_signal(list(manual_features.values()))
            return render_template(
                "brain_result.html",
                result=result,
                manual_features=manual_features,   # <-- PASS TO TEMPLATE
                csv_preview=None,
                features=list(manual_features.values()),
                doctors=selected_doctors,
                aadhar_id=aadhar_id
            )

        # ------------------------------
        # TEXT-BASED INPUT
        # ------------------------------
        text = request.form.get("signal_text")
        if text and text.strip() != "":
            # Parse comma-separated values
            try:
                features = [float(x.strip()) for x in text.split(',')]
                result = analyze_brain_signal(features)
                return render_template(
                    "brain_result.html",
                    result=result,
                    manual_features=None,
                    csv_preview=None,
                    features=features,
                    doctors=selected_doctors,
                    aadhar_id=aadhar_id
                )
            except Exception as e:
                return f"Text input error: {str(e)}. Please provide 85 comma-separated numeric values."

        # ------------------------------
        # FILE UPLOAD (CSV)
        # ------------------------------
        file = request.files.get("signal_file")
        if file and file.filename != "":
            filename = file.filename.lower()

            if filename.endswith(".csv"):
                try:
                    # Read file content
                    file_content = file.read().decode("utf-8")
                    
                    # Parse CSV
                    df = pd.read_csv(io.StringIO(file_content))
                    
                    # Extract first row
                    row = df.iloc[0].to_dict()
                    features = []
                    for i in range(1, 86):
                        key = f"F{i}"
                        if key in row:
                            features.append(float(row[key]))
                        else:
                            features.append(0.0)

                    result = analyze_brain_signal(features)

                    return render_template(
                        "brain_result.html",
                        result=result,
                        csv_preview=df.to_html(
                            classes="table table-bordered table-striped"
                        ),
                        features=features,       # <-- SEND ORDERED FEATURE VECTOR
                        manual_features=None,
                        doctors=selected_doctors,
                        aadhar_id=aadhar_id
                    )

                except Exception as e:
                    return f"CSV parse error: {str(e)}"

        return "No data provided"

    return render_template("brain_signal_ai.html", aadhar_id=aadhar_id)

@app.route("/send_brain_report/<aadhar_id>", methods=["POST"])
def send_brain_report(aadhar_id):
    try:
        doctor_email = request.form.get("doctor_email")
        result = request.form.get("result")
        features = request.form.get("features")
        graph_image = request.form.get("graph_image")  # Base64 encoded graph image

        if not doctor_email:
            flash("Please select a doctor to send the report.", "error")
            return redirect(request.referrer or url_for('patient_dashboard'))

        # Store report in database with graph image
        query = """
            INSERT INTO brain_reports (aadhar_id, doctor_email, result, features, graph_image)
            VALUES (%s, %s, %s, %s, %s)
        """
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        values = (aadhar_id, doctor_email, result, features, graph_image)
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        # OPTIONAL: Email to doctor
        # send_email(doctor_email, "Brain Signal Report", f"Result:\n{result}")

        flash("Brain signal report with EEG graph successfully sent to the doctor!", "success")
        return render_template(
            "success.html",
            message="Brain signal report with EEG graph successfully sent to the doctor!"
        )
    except Exception as e:
        flash(f"Error sending report: {str(e)}", "error")
        return redirect(request.referrer or url_for('patient_dashboard'))


# -------------------- PROFILE MANAGEMENT ROUTES -------------------- #

@app.route('/patient/profile', methods=['GET', 'POST'])
def patient_profile():
    if 'user_type' not in session or session['user_type'] != 'patient':
        return redirect(url_for('patient_login'))
    
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get form data
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            address = request.form.get('address')
            emergency_contact = request.form.get('emergency_contact')
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            
            # Verify current password if changing password
            if new_password:
                cursor.execute('SELECT password FROM patients WHERE aadhar_id = %s', (session['patient_aadhar'],))
                result = cursor.fetchone()
                if result and result[0] == current_password:
                    cursor.execute('''
                        UPDATE patients SET name=%s, email=%s, phone=%s, address=%s, 
                        emergency_contact=%s, password=%s WHERE aadhar_id=%s
                    ''', (name, email, phone, address, emergency_contact, new_password, session['patient_aadhar']))
                else:
                    flash('Current password is incorrect!', 'error')
                    return redirect(url_for('patient_profile'))
            else:
                cursor.execute('''
                    UPDATE patients SET name=%s, email=%s, phone=%s, address=%s, 
                    emergency_contact=%s WHERE aadhar_id=%s
                ''', (name, email, phone, address, emergency_contact, session['patient_aadhar']))
            
            conn.commit()
            flash('Profile updated successfully!', 'success')
            
        except mysql.connector.Error as e:
            print(f"Profile update error: {e}")
            flash('Error updating profile', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
        return redirect(url_for('patient_profile'))
    
    # GET request - show profile
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM patients WHERE aadhar_id = %s', (session['patient_aadhar'],))
        patient = cursor.fetchone()
    except mysql.connector.Error as e:
        print(f"Profile fetch error: {e}")
        patient = None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('patient_profile.html', patient=patient)

@app.route('/doctor/profile', methods=['GET', 'POST'])
def doctor_profile():
    if 'user_type' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('doctor_login'))
    
    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get form data
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            specialization = request.form.get('specialization')
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            
            # Verify current password if changing password
            if new_password:
                cursor.execute('SELECT password FROM doctors WHERE doctor_id = %s', (session['doctor_id'],))
                result = cursor.fetchone()
                if result and result[0] == current_password:
                    cursor.execute('''
                        UPDATE doctors SET name=%s, email=%s, phone=%s, specialization=%s, 
                        password=%s WHERE doctor_id=%s
                    ''', (name, email, phone, specialization, new_password, session['doctor_id']))
                else:
                    flash('Current password is incorrect!', 'error')
                    return redirect(url_for('doctor_profile'))
            else:
                cursor.execute('''
                    UPDATE doctors SET name=%s, email=%s, phone=%s, specialization=%s 
                    WHERE doctor_id=%s
                ''', (name, email, phone, specialization, session['doctor_id']))
            
            conn.commit()
            flash('Profile updated successfully!', 'success')
            
        except mysql.connector.Error as e:
            print(f"Profile update error: {e}")
            flash('Error updating profile', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        
        return redirect(url_for('doctor_profile'))
    
    # GET request - show profile
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM doctors WHERE doctor_id = %s', (session['doctor_id'],))
        doctor = cursor.fetchone()
    except mysql.connector.Error as e:
        print(f"Profile fetch error: {e}")
        doctor = None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return render_template('doctor_profile.html', doctor=doctor)

# -------------------- DELETE ROUTES -------------------- #

@app.route('/patient/delete-prescription/<int:prescription_id>', methods=['POST'])
def delete_prescription(prescription_id):
    if 'user_type' not in session or session['user_type'] != 'patient':
        return redirect(url_for('patient_login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get prescription details to delete file
        cursor.execute('SELECT file_path, patient_aadhar FROM prescriptions WHERE id = %s', (prescription_id,))
        prescription = cursor.fetchone()
        
        if prescription and prescription['patient_aadhar'] == session['patient_aadhar']:
            # Delete file if exists
            if prescription['file_path'] and os.path.exists(prescription['file_path']):
                try:
                    os.remove(prescription['file_path'])
                except:
                    pass
            
            # Delete from database
            cursor.execute('DELETE FROM prescriptions WHERE id = %s', (prescription_id,))
            conn.commit()
            flash('Prescription deleted successfully!', 'success')
        else:
            flash('Unauthorized to delete this prescription!', 'error')
            
    except mysql.connector.Error as e:
        print(f"Delete prescription error: {e}")
        flash('Error deleting prescription', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(url_for('patient_dashboard'))

@app.route('/doctor/delete-report/<int:report_id>', methods=['POST'])
def delete_report(report_id):
    if 'user_type' not in session or session['user_type'] != 'doctor':
        return redirect(url_for('doctor_login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get doctor's email
        cursor.execute('SELECT email FROM doctors WHERE doctor_id = %s', (session['doctor_id'],))
        doctor = cursor.fetchone()
        
        if doctor:
            # Delete report only if it belongs to this doctor
            cursor.execute('DELETE FROM brain_reports WHERE id = %s AND doctor_email = %s', 
                         (report_id, doctor['email']))
            conn.commit()
            
            if cursor.rowcount > 0:
                flash('Report deleted successfully!', 'success')
            else:
                flash('Report not found or unauthorized!', 'error')
        else:
            flash('Doctor not found!', 'error')
            
    except mysql.connector.Error as e:
        print(f"Delete report error: {e}")
        flash('Error deleting report', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    return redirect(request.referrer or url_for('doctor_dashboard'))

# -------------------- LOGOUT -------------------- #

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

# -------------------- RUN APP -------------------- #

if __name__ == '__main__':
    # Ensure DB exists (safe) and then alter prescriptions table if needed
    setup_database()
    alter_tables()  # preserve previous alterations (safe)
    alter_tables_for_digital_signature()  # ensure digital_signature column exists
    
    # Get configuration from environment
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = not IS_PRODUCTION
    
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    setup_database()
    alter_tables()
    alter_tables_for_digital_signature()
    alter_tables_for_totp()
    app.run(debug=True, host='0.0.0.0', port=5000)