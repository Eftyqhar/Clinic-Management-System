from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker, get_current_user
from app.core.database import get_db
from app.models import Doctor, User, UserRole
from app.schemas import DoctorCreate, DoctorResponse, DoctorUpdate

router = APIRouter(prefix="/doctors", tags=["Doctors"])

admin_only = RoleChecker([UserRole.ADMIN])


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor_profile(
    doctor_in: DoctorCreate,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(admin_only)
) -> Any:
    """Create a doctor profile for an existing user account (Admin only)."""
    # Verify user exists and has DOCTOR role
    user_res = await db.execute(select(User).where(User.id == doctor_in.user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found")
    
    # Check if doctor profile already exists
    doc_res = await db.execute(select(Doctor).where(Doctor.user_id == doctor_in.user_id))
    if doc_res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor profile already exists for this user")

    # Assign doctor role only if user is patient
    if user.role == UserRole.PATIENT:
        user.role = UserRole.DOCTOR

    doctor = Doctor(**doctor_in.model_dump())
    db.add(doctor)
    await db.commit()
    
    # Reload with user relationship
    result = await db.execute(select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor.id))
    return result.scalar_one()


@router.get("/", response_model=List[DoctorResponse])
async def list_doctors(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user)
) -> Any:
    """List all doctors and their specializations."""
    query = select(Doctor).options(selectinload(Doctor.user))
    res = await db.execute(query)
    return res.scalars().all()


@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(
    doctor_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user)
) -> Any:
    """Get doctor profile by ID."""
    query = select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor_id)
    res = await db.execute(query)
    doctor = res.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return doctor


@router.put("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(
    doctor_id: str,
    doctor_in: DoctorUpdate,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(admin_only)
) -> Any:
    """Update doctor profile details."""
    query = select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor_id)
    res = await db.execute(query)
    doctor = res.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    update_data = doctor_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(doctor, field, val)

    await db.commit()
    await db.refresh(doctor)
    return doctor
