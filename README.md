# Clinic Management System (FastAPI)

A modern, asynchronous RESTful API for managing a clinic, built with **FastAPI**, **SQLAlchemy 2.0 (async)**, **Pydantic v2**, and **JWT Authentication with Role-Based Access Control (RBAC)**.

---

## 🚀 Features

- **Authentication & RBAC**:
  - Roles: `admin`, `doctor`, `receptionist`, `pharmacist`, `patient`.
  - Secure password hashing with `bcrypt`.
  - OAuth2 Password Bearer flow with JWT access tokens.
- **Patient Management**:
  - Register, update, and search patients by name, phone, or email.
  - Comprehensive clinical records (blood group, allergies, emergency contacts).
- **Doctor Profiles & Scheduling**:
  - Doctor profiles with specializations and consultation fees.
  - Appointment scheduling with **double-booking collision detection**.
- **Clinical Workflow (EMR)**:
  - Clinical consultation notes, recorded symptoms, diagnosis, and vitals.
  - Digital prescriptions with medication dosage, frequency, and duration.
- **Billing & Invoices**:
  - Automatic invoice generation upon appointment booking.
  - Payment tracking (Cash, Card, Insurance) and status updates.

---

## 📁 Project Structure

```text
.
├── app/
│   ├── api/
│   │   ├── deps.py                     # Auth & RBAC role checker dependencies
│   │   └── v1/
│   │       ├── api_router.py           # Consolidated v1 router
│   │       └── endpoints/
│   │           ├── auth.py             # Login, register, me profile
│   │           ├── patients.py         # Patient CRUD & search
│   │           ├── doctors.py          # Doctor profiles & directory
│   │           ├── appointments.py     # Appointment booking & conflict prevention
│   │           ├── consultations.py    # Clinical notes & prescriptions
│   │           └── billing.py          # Invoice management & payments
│   ├── core/
│   │   ├── config.py                   # Pydantic BaseSettings
│   │   ├── database.py                 # Async SQLAlchemy engine & sessionmaker
│   │   └── security.py                 # Password hashing & JWT helpers
│   ├── models/
│   │   └── __init__.py                 # SQLAlchemy ORM models & relationships
│   ├── schemas/
│   │   └── __init__.py                 # Pydantic v2 request/response schemas
│   └── main.py                         # FastAPI application entrypoint & startup seed
├── tests/
│   └── test_clinic_flow.py             # End-to-end integration tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🛠️ Quickstart

### 1. Set Up Environment

```bash
# Clone the repository and navigate into it
cd "Clinic Management System"

# Activate your virtual environment
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Run the Development Server

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running:
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 4. Default Admin Credentials

Upon initial launch, the system automatically provisions the default administrator account:
- **Username / Email**: `admin@clinic.com`
- **Password**: `admin123`

---

## 🧪 Running Tests

To run the automated test suite:

```bash
pytest -v
```
