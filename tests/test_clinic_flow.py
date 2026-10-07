import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models import User, UserRole
from app.core.security import get_password_hash

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_auth_and_full_clinic_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Register an Admin user
    admin_reg = await client.post("/api/v1/auth/register", json={
        "email": "dr.admin@clinic.com",
        "password": "Password123!",
        "full_name": "Dr. Sarah Admin",
        "role": "admin"
    })
    assert admin_reg.status_code == 201
    admin_id = admin_reg.json()["id"]

    # 2. Login to get JWT
    login_res = await client.post("/api/v1/auth/login", data={
        "username": "dr.admin@clinic.com",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create Doctor Profile
    doc_res = await client.post("/api/v1/doctors/", headers=headers, json={
        "user_id": admin_id,
        "specialization": "Cardiology",
        "consultation_fee": 100.0,
        "phone": "+1-555-0199",
        "bio": "Experienced cardiologist"
    })
    assert doc_res.status_code == 201
    doctor_id = doc_res.json()["id"]

    # 4. Create Patient
    patient_res = await client.post("/api/v1/patients/", headers=headers, json={
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+1-555-0100",
        "email": "john.doe@example.com",
        "blood_group": "O+",
        "gender": "Male"
    })
    assert patient_res.status_code == 201
    patient_id = patient_res.json()["id"]

    # 5. Book Appointment
    appt_res = await client.post("/api/v1/appointments/", headers=headers, json={
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_date": "2026-10-10",
        "start_time": "10:00:00",
        "end_time": "10:30:00",
        "reason": "Routine heart checkup"
    })
    assert appt_res.status_code == 201
    appointment_id = appt_res.json()["id"]

    # 6. Verify Overlap Conflict Prevention (Attempt double booking)
    conflict_res = await client.post("/api/v1/appointments/", headers=headers, json={
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_date": "2026-10-10",
        "start_time": "10:15:00",
        "end_time": "10:45:00",
        "reason": "Double book test"
    })
    assert conflict_res.status_code == 409

    # 7. Record Consultation and Prescribe Medicine
    cons_res = await client.post("/api/v1/consultations/", headers=headers, json={
        "appointment_id": appointment_id,
        "symptoms": "Mild chest tightness upon exertion",
        "diagnosis": "Mild Angina",
        "treatment_plan": "Exercise, reduce salt, follow-up in 2 weeks",
        "vitals": "BP: 120/80, HR: 72 bpm, Weight: 75kg",
        "prescriptions": [
            {
                "medication_name": "Aspirin",
                "dosage": "75mg",
                "frequency": "Once daily",
                "duration": "30 days",
                "instructions": "Take after breakfast"
            }
        ]
    })
    assert cons_res.status_code == 201
    consultation_id = cons_res.json()["id"]
    assert len(cons_res.json()["prescriptions"]) == 1

    # 8. Check and Pay Invoice
    inv_fetch = await client.get(f"/api/v1/billing/by-appointment/{appointment_id}", headers=headers)
    assert inv_fetch.status_code == 200
    invoice_id = inv_fetch.json()["id"]
    assert inv_fetch.json()["total_amount"] == 100.0

    # Pay the invoice
    pay_res = await client.put(f"/api/v1/billing/{invoice_id}", headers=headers, json={
        "paid_amount": 100.0,
        "payment_method": "Credit Card"
    })
    assert pay_res.status_code == 200
    assert pay_res.json()["status"] == "paid"
