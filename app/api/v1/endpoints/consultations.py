from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker, get_current_user
from app.core.database import get_db
from app.models import Appointment, AppointmentStatus, Consultation, Prescription, User, UserRole
from app.schemas import ConsultationCreate, ConsultationResponse, ConsultationUpdate

router = APIRouter(prefix="/consultations", tags=["Consultations & Prescriptions"])

clinical_staff = RoleChecker([UserRole.ADMIN, UserRole.DOCTOR])


@router.post("/", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
async def create_consultation(
    cons_in: ConsultationCreate,
    db: AsyncSession = Depends(get_db),
    _doctor = Depends(clinical_staff)
) -> Any:
    """Record clinical consultation and prescribe medications (Doctor/Admin only)."""
    # Verify appointment exists
    appt_res = await db.execute(select(Appointment).where(Appointment.id == cons_in.appointment_id))
    appt = appt_res.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    # Check if consultation already exists for this appointment
    exist_res = await db.execute(select(Consultation).where(Consultation.appointment_id == cons_in.appointment_id))
    if exist_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Consultation already recorded for this appointment")

    # Create consultation
    consultation = Consultation(
        appointment_id=cons_in.appointment_id,
        symptoms=cons_in.symptoms,
        diagnosis=cons_in.diagnosis,
        treatment_plan=cons_in.treatment_plan,
        vitals=cons_in.vitals,
        clinical_notes=cons_in.clinical_notes,
    )
    db.add(consultation)
    await db.flush()

    # Add prescriptions if provided
    if cons_in.prescriptions:
        for rx in cons_in.prescriptions:
            prescription = Prescription(
                consultation_id=consultation.id,
                medication_name=rx.medication_name,
                dosage=rx.dosage,
                frequency=rx.frequency,
                duration=rx.duration,
                instructions=rx.instructions,
            )
            db.add(prescription)

    # Mark appointment as completed
    appt.status = AppointmentStatus.COMPLETED

    await db.commit()

    # Return with prescriptions
    q = select(Consultation).options(selectinload(Consultation.prescriptions)).where(Consultation.id == consultation.id)
    res = await db.execute(q)
    return res.scalar_one()


@router.get("/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(
    consultation_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user)
) -> Any:
    """Get consultation records including prescriptions."""
    q = select(Consultation).options(selectinload(Consultation.prescriptions)).where(Consultation.id == consultation_id)
    res = await db.execute(q)
    cons = res.scalar_one_or_none()
    if not cons:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation record not found")
    return cons


@router.get("/by-appointment/{appointment_id}", response_model=ConsultationResponse)
async def get_consultation_by_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user)
) -> Any:
    """Get consultation for a given appointment ID."""
    q = select(Consultation).options(selectinload(Consultation.prescriptions)).where(Consultation.appointment_id == appointment_id)
    res = await db.execute(q)
    cons = res.scalar_one_or_none()
    if not cons:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found for this appointment")
    return cons


@router.put("/{consultation_id}", response_model=ConsultationResponse)
async def update_consultation(
    consultation_id: str,
    cons_update: ConsultationUpdate,
    db: AsyncSession = Depends(get_db),
    _doctor = Depends(clinical_staff)
) -> Any:
    """Update consultation notes and diagnosis."""
    stmt = select(Consultation).where(Consultation.id == consultation_id)
    res = await db.execute(stmt)
    cons = res.scalar_one_or_none()
    if not cons:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")

    update_data = cons_update.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(cons, field, val)

    await db.commit()

    q = select(Consultation).options(selectinload(Consultation.prescriptions)).where(Consultation.id == consultation_id)
    res = await db.execute(q)
    return res.scalar_one()
