# 🩸 BloodBridge

> A real-time emergency blood request and donor notification system — connecting patients in need with nearby blood donors instantly.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [System Flow](#system-flow)
- [Pages & Routes](#pages--routes)
- [API Endpoints](#api-endpoints)
- [Running the Project](#running-the-project)
- [Project Structure](#project-structure)

---

## Overview

BloodBridge is a web-based emergency blood management platform with three types of users:

| Role | Description |
|---|---|
| **Public** | Anyone can raise an emergency blood request (requires admin approval) |
| **Hospital Staff** | Verified hospital staff raise requests directly (no approval needed) |
| **Blood Donors** | Registered donors receive real-time alerts via email and can accept/decline |
| **Admin** | Reviews pending requests, manages all users, approves donors and staff |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python (Flask) |
| Database | JSON files (`/data/*.json`) |
| Email | Gmail SMTP (App Password) |
| Frontend | HTML5, CSS3, Vanilla JS |
| Fonts | Google Fonts (Inter) |
| File Storage | Local (`/uploads/`) |
| Public URL | ngrok |

---

## Features

### 🏥 Hospital Staff
- Login via OTP (email-based)
- Raise emergency blood requests with patient details, blood type, units needed, and GPS location
- Requests go **Active** immediately — no admin approval needed
- All nearby donors (≤ 30 km) matching the blood type are emailed instantly
- View request status and donor responses on the status page

### 🌐 Public Emergency Requests
- Anyone can raise a request without login via `emergency.html`
- Request starts as `Pending_Admin` — admin must approve first
- After admin approval → nearby matching donors are emailed
- Requester is redirected to a **live status page** (`request_status.html?id=...`)
- Status page auto-refreshes every 10 seconds
- Shows real-time progress: Submitted → Admin Review → Donors Notified → Donor Responds

### 🩸 Blood Donors
- Register with name, contact, blood group, GPS location, and ID proof
- Login via email OTP
- Dashboard shows:
  - Matching active emergency requests (by blood group)
  - 15-minute countdown timer per request
  - Accept / Decline buttons
  - Total donations, lives saved, last donation date
- **90-day Cooldown** after each confirmed donation
  - Dashboard shows: *"You're on cooldown until DD/MM/YYYY"*
  - No email alerts sent during cooldown period
- Digital donor ID card on the dashboard

### 👤 Admin
- Login at `/admin_login.html` (username: `ADMIN1223`, password: `admin123`)
- Dashboard shows live stats: donors, staff, emergencies
- **Blood Donors tab** — Approve / Reject / Delete donor registrations
- **Hospital Staff tab** — Approve / Reject / Delete staff registrations
- **Emergency Requests tab** — split into two sections:
  - 🌐 **Public Requests** (need approval) — green `Approve` button triggers donor notifications. Pending badge is amber.
  - 🏥 **Hospital Staff Requests** (already active) — only Resolve / Delete
- Export all data as JSON

### 📧 Email Notifications
- Donors receive a branded HTML email alert with:
  - Blood type needed (highlighted)
  - Hospital name
  - Distance from their location
  - Estimated travel time
  - "Login to Accept / Decline" button (links to ngrok/public URL)
  - Hospital location map link
  - 15-minute response deadline warning
- Donors on **cooldown are skipped** — no email sent

### ✅ Donation Confirmation
- After a donor accepts and meets the patient, the requester sees each accepted donor's card on `request_status.html`
- Under each donor card, two buttons:
  - **✅ Donation Successful** → donor's `totalDonations + 1`, 90-day cooldown starts, request marked **Resolved**
  - **❌ Not Successful** → marked as Failed, request remains Active
- Donor dashboard reflects updated stats on next load

---

## System Flow

### Hospital Staff Request Flow
```
Hospital Staff Login (OTP)
        ↓
hospital_emergency_request.html → Submit Form
        ↓
POST /api/emergency  (status = Active, notifiedAt = now)
        ↓
All Approved donors within 30km + matching blood group
        ↓ (email sent)
Donor receives alert → logs in → Accept / Decline (15 min window)
        ↓
request_status.html?id=... → Requestor sees accepted donors
        ↓
Requestor clicks "Donation Successful"
        ↓
  • Donor: totalDonations++, cooldownUntil = today + 90 days
  • Request: status = Resolved
```

### Public Emergency Request Flow
```
Anyone visits emergency.html → Submit Form
        ↓
POST /api/public-emergency  (status = Pending_Admin)
        ↓
Redirect → request_status.html?id=...
  Shows: Submitted ✓ → Admin Review ⏳ → Donors Notified → Donor Responds
        ↓
Admin logs in → Emergency tab → Public Requests section
        ↓
Admin clicks "✓ Approve"
        ↓
PATCH /api/admin/emergency-requests/:id/status  { status: "Active" }
  • Donors within 30km + matching blood group notified via email
  • Cooldown donors are SKIPPED
        ↓
Same flow as hospital staff from here →
Donor responds → Requestor confirms → Donation recorded
```

### Donor Cooldown Flow
```
After "Donation Successful" confirmed:
  donor.totalDonations += 1
  donor.lastDonation = today (DD Mon YYYY)
  donor.cooldownUntil = today + 90 days (YYYY-MM-DD)
        ↓
On next emergency:
  if cooldownUntil >= today → donor SKIPPED (no email)
        ↓
Donor dashboard shows:
  ❄️ "You're on cooldown until DD/MM/YYYY"
  Emergency list replaced with cooldown message
        ↓
After cooldown date passes → donor is eligible again automatically
```

---

## Pages & Routes

| Page | URL | Who Uses It |
|---|---|---|
| Home / Login | `/login.html` | Everyone |
| Role Selection | `/role_selection.html` | New users |
| Donor Registration | `/blood_donor_form.html` | New donors |
| Donor Login | `/donor_login.html` | Donors |
| Donor Dashboard | `/donor_dashboard.html` | Donors |
| Public Emergency Form | `/emergency.html` | Public users |
| Hospital Staff Login | `/hospital_staff_login.html` | Staff |
| Hospital Staff OTP | `/hospital_otp_verify.html` | Staff |
| Hospital Dashboard | `/hospital_dashboard.html` | Staff |
| Hospital Emergency Form | `/hospital_emergency_request.html` | Staff |
| Request Status | `/request_status.html?id=<ID>` | Requester (live tracking) |
| Admin Login | `/admin_login.html` | Admin |
| Admin Dashboard | `/admin_dashboard.html` | Admin |

---

## API Endpoints

### Public / Donor
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/public-emergency` | Raise a public emergency request |
| GET | `/api/emergency/<id>/responses` | Get donor responses for a request |
| POST | `/api/emergency/<id>/confirm-donation` | Confirm donation success/failure |
| POST | `/api/donor/register` | Register as a blood donor |
| POST | `/api/donor/send-otp` | Send login OTP to donor email |
| POST | `/api/donor/verify-otp` | Verify OTP and login donor |
| GET | `/api/donor/dashboard` | Get donor dashboard data |
| POST | `/api/donor/respond` | Accept or Decline an emergency request |
| POST | `/api/donor/logout` | Logout donor |

### Hospital Staff
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/emergency` | Raise emergency request (staff only) |
| POST | `/api/hospital-staff/register` | Register as hospital staff |
| POST | `/api/hospital-staff/send-otp` | Send OTP to staff email |
| POST | `/api/hospital-staff/verify-otp` | Verify OTP and login staff |

### Admin
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/admin/login` | Admin login |
| POST | `/api/admin/logout` | Admin logout |
| GET | `/api/admin/stats` | Dashboard statistics |
| GET | `/api/admin/blood-donors` | List all donors |
| PATCH | `/api/admin/blood-donors/<id>/status` | Approve / Reject donor |
| DELETE | `/api/admin/blood-donors/<id>` | Delete donor |
| GET | `/api/admin/hospital-staff` | List all staff |
| PATCH | `/api/admin/hospital-staff/<id>/status` | Approve / Reject staff |
| DELETE | `/api/admin/hospital-staff/<id>` | Delete staff |
| GET | `/api/admin/emergency-requests` | List all emergency requests |
| PATCH | `/api/admin/emergency-requests/<id>/status` | Approve / Resolve request |
| DELETE | `/api/admin/emergency-requests/<id>` | Delete request |
| GET | `/api/admin/export` | Export all data as JSON |

---

## Running the Project

### Prerequisites
- Python 3.8+
- pip

### Install Dependencies
```bash
pip install flask flask-cors
```

### Start the Server
```bash
python app.py
```

Server runs at: [http://localhost:5000](http://localhost:5000)

### For Public Access (ngrok)
```bash
ngrok http 5000
```
Then update `BASE_URL` in `app.py`:
```python
BASE_URL = 'https://your-ngrok-url.ngrok-free.dev'
```

### Admin Credentials
```
Username: ADMIN1223
Password: admin123
```

---

## Project Structure

```
BloodBridge/
├── app.py                          # Flask backend (all API routes)
├── login.html                      # Home / entry page
├── login.js                        # Login page JS
├── login.css                       # Shared styles
├── role_selection.html             # Role picker
├── emergency.html                  # Public emergency request form
├── request_status.html             # Live request status tracker
├── blood_donor_form.html           # Donor registration
├── donor_login.html                # Donor OTP login
├── donor_dashboard.html            # Donor dashboard + emergency list
├── hospital_staff_login.html       # Staff login
├── hospital_otp_verify.html        # Staff OTP verify
├── hospital_dashboard.html         # Staff dashboard
├── hospital_emergency_request.html # Staff emergency form
├── admin_login.html                # Admin login
├── admin_dashboard.html            # Admin control panel
├── data/
│   ├── blood_donors.json           # Donor records
│   ├── hospital_staff.json         # Staff records
│   └── emergency_requests.json     # Emergency request records
└── uploads/
    ├── blood_donors/               # Donor ID proofs
    ├── hospital_staff/             # Staff ID proofs
    └── emergency/                  # Emergency related files
```

---

## Key Design Decisions

| Decision | Reason |
|---|---|
| JSON files as DB | No external DB dependency — simple, portable |
| Email OTP login | No password storage needed — more secure |
| 30km radius notifications | Ensures donors are realistically reachable |
| 15-minute response window | Urgency — expired responses auto-marked |
| 90-day cooldown | Medically safe gap between whole-blood donations |
| Public requests need approval | Prevents spam/fake emergency requests |
| ngrok for public access | Easy sharing without server deployment |

---

*Built for BloodBridge — saving lives, one donation at a time.* 🩸
