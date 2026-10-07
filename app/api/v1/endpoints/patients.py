from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker, get_current_user
from app.core.database import get_db
from app.models import Patient, UserRole
from app.schemas import PatientCreate, PatientResponse, PatientUpdate

router = APIRouter(prefix="/patients", tags=["Patients"])

allow_staff = RoleChecker([UserRole.ADMIN, UserRole.DOCTOR, UserRole.RECEPTIONIST])


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_in: PatientCreate,
    db: AsyncSession = Depends(get_db),
    _staff = Depends(allow_staff)
) -> Any:
    """Register a new patient into the clinic system."""
    patient = Patient(**patient_in.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.get("/", response_model=List[PatientResponse])
async def list_patients(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = Query(None, description="Search by name, phone, or email"),
    db: AsyncSession = Depends(get_db),
    _staff = Depends(allow_staff)
) -> Any:
    """List patients with optional search filtering."""
    query = select(Patient)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Patient.first_name.ilike(search_filter),
                Patient.last_name.ilike(search_filter),
                Patient.phone.ilike(search_filter),
                Patient.email.ilike(search_filter)
            )
        )
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _staff = Depends(allow_staff)
) -> Any:
    """Retrieve details of a specific patient."""
    stmt = select(Patient).where(Patient.id == patient_id)
    res = await db.execute(stmt)
    patient = res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    patient_update: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    _staff = Depends(allow_staff)
) -> Any:
    """Update patient details."""
    stmt = select(Patient).where(Patient.id == patient_id)
    res = await db.execute(stmt)
    patient = res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    update_data = patient_update.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(patient, field, val)

    await db.commit()
    await db.refresh(patient)
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(RoleChecker([UserRole.ADMIN]))
) -> None:
    """Delete patient record (Admin only)."""
    stmt = select(Patient).where(Patient.id == patient_id)
    res = await db.execute(stmt)
    patient = res.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    await db.delete(patient)
    await db.commit()
