from datetime import date
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker, get_current_user
from app.core.database import get_db
from app.models import Appointment, AppointmentStatus, Doctor, Patient, User, UserRole, Invoice
from app.schemas import AppointmentCreate, AppointmentResponse, AppointmentUpdate

router = APIRouter(prefix="/appointments", tags=["Appointments"])

allow_staff = RoleChecker([UserRole.ADMIN, UserRole.DOCTOR, UserRole.RECEPTIONIST])


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def book_appointment(
    appt_in: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """Book a new appointment with slot overlap conflict prevention."""
    # Validate patient exists
    p_res = await db.execute(select(Patient).where(Patient.id == appt_in.patient_id))
    patient = p_res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Validate doctor exists
    d_res = await db.execute(select(Doctor).where(Doctor.id == appt_in.doctor_id))
    doctor = d_res.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    # Verify time interval validity
    if appt_in.start_time >= appt_in.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be earlier than end_time"
        )

    # Overlap detection query for the same doctor and date
    conflict_stmt = select(Appointment).where(
        and_(
            Appointment.doctor_id == appt_in.doctor_id,
            Appointment.appointment_date == appt_in.appointment_date,
            Appointment.status.notin_([AppointmentStatus.CANCELLED]),
            or_(
                and_(Appointment.start_time <= appt_in.start_time, Appointment.end_time > appt_in.start_time),
                and_(Appointment.start_time < appt_in.end_time, Appointment.end_time >= appt_in.end_time),
                and_(Appointment.start_time >= appt_in.start_time, Appointment.end_time <= appt_in.end_time)
            )
        )
    )
    conflict_res = await db.execute(conflict_stmt)
    if conflict_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor already has an appointment booked during this time interval."
        )

    appointment = Appointment(**appt_in.model_dump())
    db.add(appointment)
    await db.flush()

    # Automatically generate an initial pending invoice based on doctor's consultation fee
    invoice = Invoice(
        appointment_id=appointment.id,
        total_amount=doctor.consultation_fee,
        paid_amount=0.0,
        notes=f"Initial consultation fee for Dr. {doctor.id}"
    )
    db.add(invoice)

    await db.commit()
    
    # Reload with patient and doctor
    q = (
        select(Appointment)
        .options(
            selectinload(Appointment.patient),
            selectinload(Appointment.doctor).selectinload(Doctor.user)
        )
        .where(Appointment.id == appointment.id)
    )
    res = await db.execute(q)
    return res.scalar_one()


@router.get("/", response_model=List[AppointmentResponse])
async def list_appointments(
    doctor_id: Optional[str] = Query(None),
    patient_id: Optional[str] = Query(None),
    status: Optional[AppointmentStatus] = Query(None),
    date_filter: Optional[date] = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """List appointments with optional doctor, patient, status, or date filters."""
    query = select(Appointment).options(
        selectinload(Appointment.patient),
        selectinload(Appointment.doctor).selectinload(Doctor.user)
    )

    if doctor_id:
        query = query.where(Appointment.doctor_id == doctor_id)
    if patient_id:
        query = query.where(Appointment.patient_id == patient_id)
    if status:
        query = query.where(Appointment.status == status)
    if date_filter:
        query = query.where(Appointment.appointment_date == date_filter)

    res = await db.execute(query)
    return res.scalars().all()


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user)
) -> Any:
    """Get appointment by ID."""
    query = (
        select(Appointment)
        .options(
            selectinload(Appointment.patient),
            selectinload(Appointment.doctor).selectinload(Doctor.user)
        )
        .where(Appointment.id == appointment_id)
    )
    res = await db.execute(query)
    appt = res.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appt


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: str,
    appt_update: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    _staff = Depends(allow_staff)
) -> Any:
    """Update appointment details or status."""
    stmt = select(Appointment).where(Appointment.id == appointment_id)
    res = await db.execute(stmt)
    appt = res.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    update_data = appt_update.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(appt, field, val)

    await db.commit()
    
    # Reload with relationships
    q = (
        select(Appointment)
        .options(
            selectinload(Appointment.patient),
            selectinload(Appointment.doctor).selectinload(Doctor.user)
        )
        .where(Appointment.id == appointment_id)
    )
    res = await db.execute(q)
    return res.scalar_one()
