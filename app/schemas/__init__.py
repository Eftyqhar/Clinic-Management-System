from datetime import datetime, date, time
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from app.models import UserRole, AppointmentStatus, InvoiceStatus


# ------------------- TOKEN SCHEMAS -------------------
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[str] = None


# ------------------- USER SCHEMAS -------------------
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.PATIENT
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ------------------- DOCTOR SCHEMAS -------------------
class DoctorBase(BaseModel):
    specialization: str
    consultation_fee: float = 50.0
    phone: Optional[str] = None
    bio: Optional[str] = None


class DoctorCreate(DoctorBase):
    user_id: str


class DoctorUpdate(BaseModel):
    specialization: Optional[str] = None
    consultation_fee: Optional[float] = None
    phone: Optional[str] = None
    bio: Optional[str] = None


class DoctorResponse(DoctorBase):
    id: str
    user_id: str
    user: Optional[UserResponse] = None
    model_config = ConfigDict(from_attributes=True)


# ------------------- PATIENT SCHEMAS -------------------
class PatientBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    allergies: Optional[str] = None


class PatientCreate(PatientBase):
    user_id: Optional[str] = None


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    allergies: Optional[str] = None


class PatientResponse(PatientBase):
    id: str
    user_id: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ------------------- APPOINTMENT SCHEMAS -------------------
class AppointmentBase(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_date: date
    start_time: time
    end_time: time
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    reason: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[AppointmentStatus] = None
    reason: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    id: str
    created_at: datetime
    patient: Optional[PatientResponse] = None
    doctor: Optional[DoctorResponse] = None
    model_config = ConfigDict(from_attributes=True)


# ------------------- PRESCRIPTION & CONSULTATION -------------------
class PrescriptionBase(BaseModel):
    medication_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: Optional[str] = None


class PrescriptionCreate(PrescriptionBase):
    pass


class PrescriptionResponse(PrescriptionBase):
    id: str
    consultation_id: str
    model_config = ConfigDict(from_attributes=True)


class ConsultationBase(BaseModel):
    symptoms: Optional[str] = None
    diagnosis: str
    treatment_plan: Optional[str] = None
    vitals: Optional[str] = None
    clinical_notes: Optional[str] = None


class ConsultationCreate(ConsultationBase):
    appointment_id: str
    prescriptions: Optional[List[PrescriptionCreate]] = []


class ConsultationUpdate(BaseModel):
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    vitals: Optional[str] = None
    clinical_notes: Optional[str] = None


class ConsultationResponse(ConsultationBase):
    id: str
    appointment_id: str
    created_at: datetime
    prescriptions: List[PrescriptionResponse] = []
    model_config = ConfigDict(from_attributes=True)


# ------------------- INVOICE SCHEMAS -------------------
class InvoiceBase(BaseModel):
    appointment_id: str
    total_amount: float
    paid_amount: float = 0.0
    status: InvoiceStatus = InvoiceStatus.PENDING
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    total_amount: Optional[float] = None
    paid_amount: Optional[float] = None
    status: Optional[InvoiceStatus] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


class InvoiceResponse(InvoiceBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
