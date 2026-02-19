import os, json, uuid, secrets, random, string, math
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from werkzeug.utils import secure_filename

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = 'bloodbridge_secret_2024'

# Cookie settings — work on localhost AND ngrok/HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Keep False — ngrok proxies HTTP internally

CORS(app, supports_credentials=True, origins='*')

# ── Config ─────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

UPLOAD_FOLDERS = {
    'blood_donors':   os.path.join(UPLOAD_DIR, 'blood_donors'),
    'hospital_staff': os.path.join(UPLOAD_DIR, 'hospital_staff'),
    'emergency':      os.path.join(UPLOAD_DIR, 'emergency'),
}

DATA_FILES = {
    'blood_donors':       os.path.join(DATA_DIR, 'blood_donors.json'),
    'hospital_staff':     os.path.join(DATA_DIR, 'hospital_staff.json'),
    'emergency_requests': os.path.join(DATA_DIR, 'emergency_requests.json'),
}

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'gif', 'webp'}

ADMIN_USERNAME = 'ADMIN1223'
ADMIN_PASSWORD = 'admin123'

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Gmail SMTP config
SMTP_EMAIL    = 'bloodbridge2025@gmail.com'
SMTP_PASSWORD = 'xrhskuxeelbhzxql'   # Gmail App Password (no spaces)
SMTP_HOST     = 'smtp.gmail.com'
SMTP_PORT     = 587

# ── Public base URL (ngrok or production) ──────────────────────────────────
BASE_URL = 'https://noumenal-renay-absurdly.ngrok-free.dev'

# ── Init folders & files ───────────────────────────────────────────────────
for folder in [DATA_DIR, *UPLOAD_FOLDERS.values()]:
    os.makedirs(folder, exist_ok=True)

for path in DATA_FILES.values():
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump([], f)

# ── Helpers ────────────────────────────────────────────────────────────────
def load_db(key):
    try:
        with open(DATA_FILES[key], 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_db(key, data):
    with open(DATA_FILES[key], 'w') as f:
        json.dump(data, f, indent=2, default=str)

def gen_id():
    return str(uuid.uuid4())[:8]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file, folder_key):
    """Save uploaded file to the correct folder, return saved filename or None."""
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{gen_id()}_{secure_filename(file.filename)}"
    save_path = os.path.join(UPLOAD_FOLDERS[folder_key], unique_name)
    file.save(save_path)
    return unique_name

def ts():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def require_admin():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    return None


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great-circle distance in km between two points."""
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def send_donor_alert_email(donor, hospital_name, blood_type, distance_km, location_link):
    """Send hospital-staff emergency alert to donor (no login needed)."""
    try:
        speed_kmh = 40
        time_min = round((distance_km / speed_kmh) * 60)
        dist_str = f"{distance_km:.1f} km"

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'\U0001f6a8 Urgent Blood Request \u2014 {blood_type} Needed Nearby'
        msg['From']    = f'BloodBridge <{SMTP_EMAIL}>'
        msg['To']      = donor['email']

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;background:#0f172a;color:#e2e8f0;border-radius:16px;padding:32px;">
          <h2 style="color:#f87171;margin:0 0 4px">\U0001fa78 BloodBridge Emergency Alert</h2>
          <p style="color:#94a3b8;margin:0 0 24px;font-size:14px">A hospital near you urgently needs blood</p>
          <div style="background:#1e293b;border-radius:12px;padding:24px;margin-bottom:20px;">
            <table width="100%">
              <tr><td style="color:#94a3b8;font-size:13px;padding:6px 0;">Blood Type</td><td style="text-align:right;"><span style="background:#ef4444;color:#fff;padding:4px 12px;border-radius:6px;font-weight:700;">{blood_type}</span></td></tr>
              <tr><td style="color:#94a3b8;font-size:13px;padding:6px 0;">Hospital</td><td style="text-align:right;color:#f8fafc;font-weight:600;">{hospital_name}</td></tr>
              <tr><td style="color:#94a3b8;font-size:13px;padding:6px 0;">Distance</td><td style="text-align:right;color:#22c55e;font-weight:700;">{dist_str} away</td></tr>
              <tr><td style="color:#94a3b8;font-size:13px;padding:6px 0;">Est. Time</td><td style="text-align:right;color:#3b82f6;font-weight:700;">~{time_min} mins</td></tr>
            </table>
          </div>
          <a href="{location_link}" style="display:block;text-align:center;background:#dc2626;color:#fff;padding:14px;border-radius:10px;text-decoration:none;font-weight:700;font-size:15px;margin-bottom:20px;">\U0001f4cd Get Directions</a>
          <p style="color:#64748b;font-size:12px;text-align:center;">You are a registered BloodBridge donor within 30km of this request.</p>
        </div>"""

        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, donor['email'], msg.as_string())
        print(f"[ALERT] \u2705 Email sent to {donor['email']} ({dist_str})")
        return True
    except Exception as e:
        print(f"[ALERT ERROR] {e}")
        return False


def send_public_donor_alert_email(donor, req, distance_km):
    """Send public emergency alert to donor. Links to donor login page."""
    try:
        speed_kmh = 40
        time_min = round((distance_km / speed_kmh) * 60)
        dist_str = f"{distance_km:.1f} km"
        blood_type = req.get('bloodType', '')
        hospital_name = req.get('hospitalName', 'a hospital')
        req_id = req.get('id', '')
        location_link = req.get('location', '#')

        # Link goes to donor login page (they login then see the request)
        login_url = f'{BASE_URL}/donor_login.html'

        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'\U0001f6a8 URGENT: {blood_type} Blood Needed \u2014 15 Min to Respond'
        msg['From']    = f'BloodBridge <{SMTP_EMAIL}>'
        msg['To']      = donor['email']

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:540px;margin:auto;background:#0f172a;color:#e2e8f0;border-radius:16px;padding:32px;">
          <h2 style="color:#f87171;margin:0 0 4px">\U0001fa78 Emergency Blood Request</h2>
          <p style="color:#94a3b8;margin:0 0 24px;font-size:14px">This request was approved by BloodBridge Admin</p>

          <div style="background:#7f1d1d;border-radius:12px;padding:14px 20px;margin-bottom:20px;text-align:center;">
            <p style="color:#fca5a5;font-weight:700;font-size:16px;margin:0;">\u23f0 You have 15 minutes to Accept or Decline</p>
          </div>

          <div style="background:#1e293b;border-radius:12px;padding:24px;margin-bottom:20px;">
            <table width="100%">
              <tr><td style="color:#94a3b8;font-size:13px;padding:6px 0;">Blood Type</td><td style="text-align:right;"><span style="background:#ef4444;color:#fff;padding:4px 14px;border-radius:6px;font-weight:700;font-size:17px;">{blood_type}</span></td></tr>
              <tr><td style="color:#94a3b8;font-size:13px;padding:6px 0;">Hospital</td><td style="text-align:right;color:#f8fafc;font-weight:600;">{hospital_name}</td></tr>
              <tr><td style="color:#94a3b8;font-size:13px;padding:6px 0;">Distance</td><td style="text-align:right;color:#22c55e;font-weight:700;">{dist_str} away</td></tr>
              <tr><td style="color:#94a3b8;font-size:13px;padding:6px 0;">Est. Travel</td><td style="text-align:right;color:#3b82f6;font-weight:700;">~{time_min} mins</td></tr>
            </table>
          </div>

          <a href="{login_url}" style="display:block;text-align:center;background:#dc2626;color:#fff;padding:16px;border-radius:10px;text-decoration:none;font-weight:700;font-size:16px;margin-bottom:12px;">\U0001fa78 Login to Accept / Decline</a>
          <a href="{location_link}" style="display:block;text-align:center;background:#1e293b;color:#94a3b8;padding:12px;border-radius:10px;text-decoration:none;font-size:14px;margin-bottom:20px;">\U0001f4cd View Hospital Location</a>

          <p style="color:#64748b;font-size:12px;text-align:center;">If you do not respond within 15 minutes, this request will be automatically declined for you.</p>
        </div>"""

        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, donor['email'], msg.as_string())
        print(f"[PUBLIC ALERT] \u2705 Sent to {donor['email']} ({dist_str})")
        return True
    except Exception as e:
        print(f"[PUBLIC ALERT ERROR] {e}")
        return False

# ── Serve frontend pages ───────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'login.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/uploads/<folder>/<filename>')
def serve_upload(folder, filename):
    folder_path = os.path.join(UPLOAD_DIR, folder)
    return send_from_directory(folder_path, filename)

# ══════════════════════════════════════════════════════════════════════════
# PUBLIC FORM ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════

# ── Blood Donor Registration ───────────────────────────────────────────────
@app.route('/api/blood-donor', methods=['POST'])
def add_blood_donor():
    try:
        name        = request.form.get('name', '').strip()
        contact     = request.form.get('contact', '').strip()
        email       = request.form.get('email', '').strip()
        blood_group = request.form.get('bloodGroup', '').strip()
        location    = request.form.get('location', '').strip()
        age_confirm = request.form.get('ageConfirm', 'false')

        if not all([name, contact, email, blood_group, location]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Handle ID image upload
        id_file = request.files.get('validId')
        saved_filename = save_upload(id_file, 'blood_donors')

        record = {
            'id':           gen_id(),
            'name':         name,
            'contact':      contact,
            'email':        email,
            'bloodGroup':   blood_group,
            'location':     location,
            'lat':          float(request.form.get('lat', 0) or 0),
            'lng':          float(request.form.get('lng', 0) or 0),
            'ageConfirmed': age_confirm == 'true',
            'idImage':      saved_filename,
            'idImageUrl':   f'/uploads/blood_donors/{saved_filename}' if saved_filename else None,
            'status':       'Pending',
            'createdAt':    ts(),
        }

        donors = load_db('blood_donors')
        donors.append(record)
        save_db('blood_donors', donors)

        return jsonify({'success': True, 'message': 'Registration submitted!', 'id': record['id']}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Hospital Staff Registration ────────────────────────────────────────────
@app.route('/api/hospital-staff', methods=['POST'])
def add_hospital_staff():
    try:
        hospital_name    = request.form.get('hospitalName', '').strip()
        hospital_contact = request.form.get('contact', '').strip()
        staff_name       = request.form.get('staffName', '').strip()
        staff_contact    = request.form.get('staffContact', '').strip()
        staff_email      = request.form.get('staffEmail', '').strip()
        location         = request.form.get('location', '').strip()

        if not all([hospital_name, hospital_contact, staff_name, staff_contact, staff_email]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Handle staff ID upload
        id_file = request.files.get('staffIdUpload')
        saved_filename = save_upload(id_file, 'hospital_staff')

        record = {
            'id':              gen_id(),
            'hospitalName':    hospital_name,
            'hospitalContact': hospital_contact,
            'staffName':       staff_name,
            'staffContact':    staff_contact,
            'staffEmail':      staff_email,
            'location':        location,
            'staffIdFile':     saved_filename,
            'staffIdUrl':      f'/uploads/hospital_staff/{saved_filename}' if saved_filename else None,
            'status':          'Pending',
            'createdAt':       ts(),
        }

        staff = load_db('hospital_staff')
        staff.append(record)
        save_db('hospital_staff', staff)

        return jsonify({'success': True, 'message': 'Staff registration submitted!', 'id': record['id']}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════
# OTP ENDPOINTS  —  Twilio Programmable SMS (works for ANY number)
# ══════════════════════════════════════════════════════════════════════════

# In-memory OTP store: { phone: { code, expires } }
_otp_store = {}

def _store_otp(phone):
    """Generate & store a 4-digit OTP valid for 10 minutes."""
    code = str(random.randint(1000, 9999))
    _otp_store[phone] = {
        'code': code,
        'expires': datetime.utcnow() + timedelta(minutes=10)
    }
    return code

def _verify_local_otp(phone, code):
    """Check the stored OTP. Returns True if valid & not expired."""
    entry = _otp_store.get(phone)
    if not entry:
        return False
    if datetime.utcnow() > entry['expires']:
        _otp_store.pop(phone, None)
        return False
    if entry['code'] == code:
        _otp_store.pop(phone, None)
        return True
    return False


def _send_otp_email(to_email, code):
    """Send OTP via Gmail SMTP. Returns True on success."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'BloodBridge OTP: {code}'
        msg['From']    = f'BloodBridge <{SMTP_EMAIL}>'
        msg['To']      = to_email

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;background:#0f172a;color:#e2e8f0;border-radius:16px;padding:32px;">
          <h2 style="color:#f87171;margin:0 0 8px">🩸 BloodBridge</h2>
          <p style="color:#94a3b8;margin:0 0 24px">Hospital Staff Verification</p>
          <div style="background:#1e293b;border-radius:12px;padding:24px;text-align:center;">
            <p style="margin:0 0 8px;color:#94a3b8;font-size:14px">Your verification code is</p>
            <div style="font-size:40px;font-weight:700;letter-spacing:12px;color:#f87171;">{code}</div>
            <p style="margin:16px 0 0;color:#64748b;font-size:12px">Valid for 10 minutes. Do not share this code.</p>
          </div>
        </div>"""

        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f'[SMTP ERROR] {e}')
        return False


@app.route('/api/otp/send', methods=['POST'])
def otp_send():
    data  = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'error': 'Email required'}), 400

    # Generate 4-digit OTP and store it
    code = _store_otp(email)
    print(f"\n{'='*50}\n[OTP] Email: {email}  Code: {code}\n{'='*50}\n")

    if _send_otp_email(email, code):
        print(f"[OTP] ✅ Email sent to {email}")
        return jsonify({'success': True, 'email': email, 'via': 'email'})
    else:
        # Fallback: show OTP on screen
        print(f"[OTP] Email failed — returning OTP for on-screen display")
        return jsonify({'success': True, 'email': email, 'via': 'screen', 'devOtp': code})


@app.route('/api/otp/verify', methods=['POST'])
def otp_verify():
    data  = request.get_json() or {}
    email = data.get('email', '').strip()
    code  = data.get('code', '').strip()

    if not email or not code:
        return jsonify({'error': 'Email and code required'}), 400

    if _verify_local_otp(email, code):
        print(f"[OTP] ✅ Verified for {email}")
        return jsonify({'success': True, 'verified': True})

    print(f"[OTP] ❌ Invalid/expired OTP for {email}")
    return jsonify({'success': False, 'verified': False, 'error': 'Invalid or expired OTP'}), 400


# ── LOGIN ENDPOINTS (Email OTP) ─────────────────────────────────────────────
@app.route('/api/login/send-otp', methods=['POST'])
def login_send_otp():
    data  = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'error': 'Email required'}), 400

    # 1. Check if email exists in hospital_staff
    staff_db = load_db('hospital_staff')
    user = next((u for u in staff_db if u.get('staffEmail') == email), None)
    
    if not user:
        return jsonify({'error': 'Email not registered. Please register first.'}), 404

    # 2. Check status (optional - maybe only allow Approved users?)
    # if user.get('status') != 'Approved':
    #     return jsonify({'error': 'Account not approved yet'}), 403

    # 3. Generate & Send OTP using existing logic
    code = _store_otp(email)
    print(f"\n{'='*50}\n[LOGIN OTP] Email: {email}  Code: {code}\n{'='*50}\n")

    if _send_otp_email(email, code):
        return jsonify({'success': True, 'email': email, 'via': 'email'})
    else:
        # Fallback to screen for dev/trial
        return jsonify({'success': True, 'email': email, 'via': 'screen', 'devOtp': code})


@app.route('/api/login/verify-otp', methods=['POST'])
def login_verify_otp():
    data  = request.get_json() or {}
    email = data.get('email', '').strip()
    code  = data.get('code', '').strip()

    if not email or not code:
        return jsonify({'error': 'Email and code required'}), 400

    if _verify_local_otp(email, code):
        # Login success
        session['user_email'] = email
        session['logged_in'] = True
        return jsonify({'success': True, 'verified': True})

    return jsonify({'success': False, 'verified': False, 'error': 'Invalid or expired OTP'}), 400



    return jsonify({'success': False, 'verified': False, 'error': 'Invalid or expired OTP'}), 400


# ── DONOR LOGIN & DASHBOARD ────────────────────────────────────────────────
@app.route('/api/donor/login/send-otp', methods=['POST'])
def donor_login_send_otp():
    data  = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email: return jsonify({'error': 'Email required'}), 400

    donors = load_db('blood_donors')
    user = next((d for d in donors if d.get('email') == email), None)
    
    if not user:
        return jsonify({'error': 'Email not registered.'}), 404

    code = _store_otp(email)
    print(f"\n[DONOR OTP] Email: {email}  Code: {code}\n")

    if _send_otp_email(email, code):
        return jsonify({'success': True, 'email': email, 'via': 'email'})
    else:
        return jsonify({'success': True, 'email': email, 'via': 'screen', 'devOtp': code})


@app.route('/api/donor/login/verify-otp', methods=['POST'])
def donor_login_verify_otp():
    data  = request.get_json() or {}
    email = data.get('email', '').strip()
    code  = data.get('code', '').strip()

    if not email or not code: return jsonify({'error': 'Email and code required'}), 400

    if _verify_local_otp(email, code):
        session['donor_email'] = email
        return jsonify({'success': True, 'verified': True})

    return jsonify({'success': False, 'error': 'Invalid OTP'}), 400


@app.route('/api/donor/logout', methods=['POST'])
def donor_logout():
    session.pop('donor_email', None)
    return jsonify({'success': True})


@app.route('/api/donor/dashboard', methods=['GET'])
def donor_dashboard():
    email = session.get('donor_email')
    if not email: return jsonify({'error': 'Unauthorized'}), 401

    donors = load_db('blood_donors')
    user = next((d for d in donors if d.get('email') == email), None)
    if not user: return jsonify({'error': 'User not found'}), 404

    # Auto-expire: any Active public request notified >15 mins ago with no response
    all_reqs = load_db('emergency_requests')
    changed = False
    now = datetime.now()
    for r in all_reqs:
        if r.get('status') == 'Active' and r.get('notifiedAt'):
            notified_at = datetime.strptime(r['notifiedAt'], '%Y-%m-%d %H:%M:%S')
            if (now - notified_at).total_seconds() > 900:  # 15 minutes
                donor_responses = r.get('donorResponses', {})
                if email not in donor_responses:
                    r.setdefault('donorResponses', {})[email] = {'status': 'Expired', 'at': ts()}
                    changed = True
    if changed:
        save_db('emergency_requests', all_reqs)

    # Filter requests: Active, matching blood group
    relevant_emergencies = [
        e for e in all_reqs
        if e.get('status') == 'Active'
        and (e.get('bloodType') == user.get('bloodGroup') or e.get('bloodType') == 'Any')
    ]

    # Attach donor's own response to each request
    for e in relevant_emergencies:
        responses = e.get('donorResponses', {})
        e['myResponse'] = responses.get(email, {}).get('status', 'Pending')
        if e.get('notifiedAt'):
            notified_at = datetime.strptime(e['notifiedAt'], '%Y-%m-%d %H:%M:%S')
            elapsed = (now - notified_at).total_seconds()
            e['secondsLeft'] = max(0, 900 - int(elapsed))
        else:
            e['secondsLeft'] = 0

    return jsonify({
        'profile': user,
        'stats': {
            'totalDonations': user.get('totalDonations', 0),
            'livesSaved':     user.get('totalDonations', 0),  # 1 donation = 1 life saved
            'lastDonation':   user.get('lastDonation', 'Never'),
            'cooldownUntil':  user.get('cooldownUntil', None),
        },
        'emergencies': relevant_emergencies
    })




@app.route('/api/hospital/dashboard', methods=['GET'])
def hospital_dashboard():
    email = session.get('user_email')
    if not email: return jsonify({'error': 'Unauthorized'}), 401

    staff_db = load_db('hospital_staff')
    user = next((u for u in staff_db if u.get('staffEmail') == email), None)
    
    if not user: return jsonify({'error': 'User not found'}), 404

    # Get requests for this hospital
    hospital_name = user.get('hospitalName')
    all_requests = load_db('emergency_requests')
    
    # Filter requests where hospital matches (case insensitive to be safe)
    my_requests = [
        r for r in all_requests 
        if r.get('hospitalName', '').lower() == hospital_name.lower()
    ]

    return jsonify({
        'staff': user,
        'requests': my_requests
    })


# ── Emergency Request ──────────────────────────────────────────────────────
@app.route('/api/emergency', methods=['POST'])
def add_emergency():
    """Hospital staff emergency request (login required, Approved only)."""
    try:
        email = session.get('user_email')
        if not email: return jsonify({'error': 'Unauthorized'}), 401

        staff_db = load_db('hospital_staff')
        user = next((u for u in staff_db if u.get('staffEmail') == email), None)
        if not user: return jsonify({'error': 'User not found'}), 404
        if user.get('status') != 'Approved':
            return jsonify({'error': 'Account not approved. Cannot raise requests.'}), 403

        hospital_name = request.form.get('hospitalName', user.get('hospitalName', '')).strip()
        patient_name  = request.form.get('patientName', '').strip()
        blood_type    = request.form.get('bloodType', '').strip()
        units_needed  = request.form.get('unitsNeeded', '').strip()
        contact       = request.form.get('contact', '').strip()
        location      = request.form.get('location', '').strip()
        condition     = request.form.get('condition', '').strip()
        required_time = request.form.get('requiredTime', '').strip()
        hosp_lat      = float(request.form.get('lat', 0) or 0)
        hosp_lng      = float(request.form.get('lng', 0) or 0)

        if not all([patient_name, blood_type, contact]):
            return jsonify({'error': 'Missing required fields'}), 400

        record = {
            'id':           gen_id(),
            'source':       'hospital_staff',
            'hospitalName': hospital_name,
            'patientName':  patient_name,
            'bloodType':    blood_type,
            'unitsNeeded':  units_needed,
            'condition':    condition,
            'requiredTime': required_time,
            'contact':      contact,
            'location':     location,
            'lat':          hosp_lat,
            'lng':          hosp_lng,
            'status':       'Active',
            'notifiedAt':   ts(),
            'donorResponses': {},
            'createdAt':    ts(),
        }

        reqs = load_db('emergency_requests')
        reqs.append(record)
        save_db('emergency_requests', reqs)

        # Smart 30KM Radius Notification
        notified_count = 0
        if hosp_lat and hosp_lng:
            donors = load_db('blood_donors')
            today = datetime.now().date()
            for donor in [d for d in donors if d.get('status') == 'Approved']:
                # Skip donors on cooldown
                cooldown_until = donor.get('cooldownUntil')
                if cooldown_until:
                    try:
                        if datetime.strptime(cooldown_until, '%Y-%m-%d').date() >= today:
                            print(f"[SKIP] {donor.get('email')} is on cooldown until {cooldown_until}")
                            continue
                    except ValueError:
                        pass
                donor_lat = donor.get('lat', 0)
                donor_lng = donor.get('lng', 0)
                if not donor_lat or not donor_lng: continue
                if blood_type != 'Any' and donor.get('bloodGroup') != blood_type: continue
                distance = haversine_distance(hosp_lat, hosp_lng, donor_lat, donor_lng)
                if distance <= 30:
                    if send_donor_alert_email(donor, hospital_name, blood_type, distance, location):
                        notified_count += 1

        print(f"[EMERGENCY] Staff request saved. {notified_count} donors notified.")
        return jsonify({'success': True, 'message': 'Emergency request raised!', 'id': record['id'], 'notified_count': notified_count}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/public-emergency', methods=['POST'])
def add_public_emergency():
    """Public emergency request — no login needed. Starts as Pending_Admin."""
    try:
        hospital_name = request.form.get('hospitalName', '').strip()
        patient_name  = request.form.get('patientName', '').strip()
        blood_type    = request.form.get('bloodType', '').strip()
        units_needed  = request.form.get('unitsNeeded', '').strip()
        contact       = request.form.get('contact', '').strip()
        location      = request.form.get('location', '').strip()
        hosp_lat      = float(request.form.get('lat', 0) or 0)
        hosp_lng      = float(request.form.get('lng', 0) or 0)

        if not all([hospital_name, patient_name, blood_type, contact]):
            return jsonify({'error': 'Missing required fields'}), 400

        record = {
            'id':             gen_id(),
            'source':         'public',
            'hospitalName':   hospital_name,
            'patientName':    patient_name,
            'bloodType':      blood_type,
            'unitsNeeded':    units_needed,
            'contact':        contact,
            'location':       location,
            'lat':            hosp_lat,
            'lng':            hosp_lng,
            'status':         'Pending_Admin',
            'donorResponses': {},
            'createdAt':      ts(),
        }

        reqs = load_db('emergency_requests')
        reqs.append(record)
        save_db('emergency_requests', reqs)

        print(f"[PUBLIC] Request from public saved. Awaiting admin approval.")
        return jsonify({'success': True, 'message': 'Request submitted! Awaiting admin review.', 'id': record['id']}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/donor/respond', methods=['POST'])
def donor_respond():
    """Donor accepts or declines an emergency request."""
    email = session.get('donor_email')
    if not email: return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json() or {}
    req_id   = data.get('requestId')
    response = data.get('response')  # 'Accepted' or 'Declined'

    if not req_id or response not in ['Accepted', 'Declined']:
        return jsonify({'error': 'Invalid data'}), 400

    reqs = load_db('emergency_requests')
    for r in reqs:
        if r['id'] == req_id:
            # Check 15-min window
            if r.get('notifiedAt'):
                notified_at = datetime.strptime(r['notifiedAt'], '%Y-%m-%d %H:%M:%S')
                if (datetime.now() - notified_at).total_seconds() > 900:
                    return jsonify({'error': 'Response window expired (15 minutes passed)'}), 410

            r.setdefault('donorResponses', {})[email] = {'status': response, 'at': ts()}
            save_db('emergency_requests', reqs)
            print(f"[DONOR RESPOND] {email} -> {response} on {req_id}")
            return jsonify({'success': True, 'response': response})

    return jsonify({'error': 'Request not found'}), 404


# ══════════════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        session['admin_user'] = username
        return jsonify({'success': True, 'message': 'Login successful'})
    return jsonify({'error': 'Invalid credentials'}), 401


@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    err = require_admin()
    if err: return err

    donors = load_db('blood_donors')
    staff  = load_db('hospital_staff')
    emerg  = load_db('emergency_requests')

    return jsonify({
        'bloodDonors': {
            'total':    len(donors),
            'pending':  sum(1 for d in donors if d['status'] == 'Pending'),
            'approved': sum(1 for d in donors if d['status'] == 'Approved'),
            'rejected': sum(1 for d in donors if d['status'] == 'Rejected'),
        },
        'hospitalStaff': {
            'total':    len(staff),
            'pending':  sum(1 for s in staff if s['status'] == 'Pending'),
            'approved': sum(1 for s in staff if s['status'] == 'Approved'),
            'rejected': sum(1 for s in staff if s['status'] == 'Rejected'),
        },
        'emergencyRequests': {
            'total':         len(emerg),
            'pending_admin': sum(1 for e in emerg if e.get('status') == 'Pending_Admin'),
            'active':        sum(1 for e in emerg if e.get('status') == 'Active'),
            'resolved':      sum(1 for e in emerg if e.get('status') == 'Resolved'),
        }
    })


# ── Blood Donors CRUD ──────────────────────────────────────────────────────
@app.route('/api/admin/blood-donors', methods=['GET'])
def get_blood_donors():
    err = require_admin()
    if err: return err
    return jsonify(load_db('blood_donors'))

@app.route('/api/admin/blood-donors/<record_id>/status', methods=['PATCH'])
def update_donor_status(record_id):
    err = require_admin()
    if err: return err
    data = request.get_json() or {}
    status = data.get('status')
    if status not in ['Approved', 'Rejected', 'Pending']:
        return jsonify({'error': 'Invalid status'}), 400
    donors = load_db('blood_donors')
    for d in donors:
        if d['id'] == record_id:
            d['status'] = status
            save_db('blood_donors', donors)
            return jsonify({'success': True})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/admin/blood-donors/<record_id>', methods=['DELETE'])
def delete_donor(record_id):
    err = require_admin()
    if err: return err
    donors = load_db('blood_donors')
    donors = [d for d in donors if d['id'] != record_id]
    save_db('blood_donors', donors)
    return jsonify({'success': True})


# ── Hospital Staff CRUD ────────────────────────────────────────────────────
@app.route('/api/admin/hospital-staff', methods=['GET'])
def get_hospital_staff():
    err = require_admin()
    if err: return err
    return jsonify(load_db('hospital_staff'))

@app.route('/api/admin/hospital-staff/<record_id>/status', methods=['PATCH'])
def update_staff_status(record_id):
    err = require_admin()
    if err: return err
    data = request.get_json() or {}
    status = data.get('status')
    if status not in ['Approved', 'Rejected', 'Pending']:
        return jsonify({'error': 'Invalid status'}), 400
    staff = load_db('hospital_staff')
    for s in staff:
        if s['id'] == record_id:
            s['status'] = status
            save_db('hospital_staff', staff)
            return jsonify({'success': True})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/admin/hospital-staff/<record_id>', methods=['DELETE'])
def delete_staff(record_id):
    err = require_admin()
    if err: return err
    staff = load_db('hospital_staff')
    staff = [s for s in staff if s['id'] != record_id]
    save_db('hospital_staff', staff)
    return jsonify({'success': True})


# ── Emergency Requests CRUD ────────────────────────────────────────────────
@app.route('/api/admin/emergency-requests', methods=['GET'])
def get_emergency_requests():
    err = require_admin()
    if err: return err
    return jsonify(load_db('emergency_requests'))


@app.route('/api/emergency/<req_id>/responses', methods=['GET'])
def get_emergency_responses(req_id):
    """Get accepted/declined donor details for a specific emergency request."""
    reqs = load_db('emergency_requests')
    req = next((r for r in reqs if r['id'] == req_id), None)
    if not req:
        return jsonify({'error': 'Request not found'}), 404

    donor_responses = req.get('donorResponses', {})
    donors_db = load_db('blood_donors')

    # Build lookup: email -> donor record
    donor_lookup = {d.get('email', '').lower(): d for d in donors_db}

    accepted = []
    declined = []

    for email, resp in donor_responses.items():
        donor = donor_lookup.get(email.lower(), {})
        entry = {
            'email':          email,
            'name':           donor.get('name', email),
            'bloodGroup':     donor.get('bloodGroup', '?'),
            'contact':        donor.get('contact', 'N/A'),
            'respondedAt':    resp.get('at', ''),
            'donationStatus': resp.get('status') if resp.get('status') in ('Donated', 'Failed') else None,
        }
        if resp.get('status') in ('Accepted', 'Donated', 'Failed'):
            accepted.append(entry)
        elif resp.get('status') == 'Declined':
            declined.append(entry)

    return jsonify({
        'request':        req,
        'acceptedDonors': accepted,
        'declinedDonors': declined,
    })


@app.route('/api/emergency/<req_id>/confirm-donation', methods=['POST'])
def confirm_donation(req_id):
    """Requestor confirms whether a donor's donation was successful."""
    data = request.get_json() or {}
    donor_email = data.get('donorEmail', '').strip().lower()
    success = data.get('success', False)  # True = Donated, False = Failed

    if not donor_email:
        return jsonify({'error': 'donorEmail required'}), 400

    # ── Update emergency request ──
    reqs = load_db('emergency_requests')
    req = next((r for r in reqs if r['id'] == req_id), None)
    if not req:
        return jsonify({'error': 'Request not found'}), 404

    # Find the donor response key (case-insensitive)
    matched_key = next((k for k in req.get('donorResponses', {}) if k.lower() == donor_email), None)
    if not matched_key:
        return jsonify({'error': 'Donor response not found'}), 404

    req['donorResponses'][matched_key]['status'] = 'Donated' if success else 'Failed'
    req['donorResponses'][matched_key]['confirmedAt'] = ts()

    if success:
        req['status'] = 'Resolved'

    save_db('emergency_requests', reqs)

    # ── Update donor record (only on success) ──
    if success:
        donors = load_db('blood_donors')
        donor = next((d for d in donors if d.get('email', '').lower() == donor_email), None)
        if donor:
            today = datetime.now()
            donor['totalDonations'] = donor.get('totalDonations', 0) + 1
            donor['livesSaved']     = donor.get('livesSaved', 0) + 1
            donor['lastDonation']   = today.strftime('%d %b %Y')
            donor['cooldownUntil']  = (today + timedelta(days=90)).strftime('%Y-%m-%d')
            save_db('blood_donors', donors)
            print(f"[DONATION] {donor.get('name')} confirmed donation. Cooldown until {donor['cooldownUntil']}")

    return jsonify({'success': True, 'resolution': 'Donated' if success else 'Failed'})

@app.route('/api/admin/emergency-requests/<record_id>/status', methods=['PATCH'])
def update_emergency_status(record_id):
    err = require_admin()
    if err: return err
    data = request.get_json() or {}
    status = data.get('status')
    if status not in ['Active', 'Resolved', 'Pending_Admin']:
        return jsonify({'error': 'Invalid status'}), 400
    reqs = load_db('emergency_requests')
    for r in reqs:
        if r['id'] == record_id:
            old_status = r.get('status')
            r['status'] = status

            # When admin approves a public request, trigger donor notifications
            if old_status == 'Pending_Admin' and status == 'Active':
                r['notifiedAt'] = ts()
                save_db('emergency_requests', reqs)

                hosp_lat = r.get('lat', 0)
                hosp_lng = r.get('lng', 0)
                blood_type = r.get('bloodType', '')
                notified_count = 0

                if hosp_lat and hosp_lng:
                    donors = load_db('blood_donors')
                    today = datetime.now().date()
                    for donor in [d for d in donors if d.get('status') == 'Approved']:
                        # Skip donors on cooldown
                        cooldown_until = donor.get('cooldownUntil')
                        if cooldown_until:
                            try:
                                if datetime.strptime(cooldown_until, '%Y-%m-%d').date() >= today:
                                    print(f"[SKIP] {donor.get('email')} is on cooldown until {cooldown_until}")
                                    continue
                            except ValueError:
                                pass
                        donor_lat = donor.get('lat', 0)
                        donor_lng = donor.get('lng', 0)
                        if not donor_lat or not donor_lng: continue
                        if blood_type != 'Any' and donor.get('bloodGroup') != blood_type: continue
                        distance = haversine_distance(hosp_lat, hosp_lng, donor_lat, donor_lng)
                        if distance <= 30:
                            if send_public_donor_alert_email(donor, r, distance):
                                notified_count += 1

                print(f"[ADMIN APPROVE] {notified_count} donors notified for request {record_id}")
                return jsonify({'success': True, 'notified_count': notified_count})

            save_db('emergency_requests', reqs)
            return jsonify({'success': True})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/admin/emergency-requests/<record_id>', methods=['DELETE'])
def delete_emergency(record_id):
    err = require_admin()
    if err: return err
    reqs = load_db('emergency_requests')
    reqs = [r for r in reqs if r['id'] != record_id]
    save_db('emergency_requests', reqs)
    return jsonify({'success': True})


# ── Export all data ────────────────────────────────────────────────────────
@app.route('/api/admin/export', methods=['GET'])
def export_data():
    err = require_admin()
    if err: return err
    export = {
        'exportedAt':       ts(),
        'bloodDonors':      load_db('blood_donors'),
        'hospitalStaff':    load_db('hospital_staff'),
        'emergencyRequests':load_db('emergency_requests'),
    }
    return jsonify(export)


if __name__ == '__main__':
    print("=" * 50)
    print("  BloodBridge Backend Server")
    print("  http://localhost:5000")
    print("  Admin: ADMIN1223 / admin123")
    print("=" * 50)
    app.run(debug=True, port=5000)
