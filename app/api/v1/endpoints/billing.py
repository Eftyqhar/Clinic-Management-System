from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker, get_current_user
from app.core.database import get_db
from app.models import Appointment, Invoice, InvoiceStatus, User, UserRole
from app.schemas import InvoiceCreate, InvoiceResponse, InvoiceUpdate

router = APIRouter(prefix="/billing", tags=["Billing & Invoices"])

billing_staff = RoleChecker([UserRole.ADMIN, UserRole.RECEPTIONIST])


@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_in: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    _staff = Depends(billing_staff)
) -> Any:
    """Manually create or override an invoice for an appointment."""
    # Check appointment
    appt_res = await db.execute(select(Appointment).where(Appointment.id == invoice_in.appointment_id))
    appt = appt_res.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    invoice = Invoice(**invoice_in.model_dump())
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.get("/", response_model=List[InvoiceResponse])
async def list_invoices(
    status: Optional[InvoiceStatus] = Query(None),
    db: AsyncSession = Depends(get_db),
    _staff = Depends(billing_staff)
) -> Any:
    """List all clinic invoices with optional status filter."""
    query = select(Invoice)
    if status:
        query = query.where(Invoice.status == status)
    res = await db.execute(query)
    return res.scalars().all()


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user)
) -> Any:
    """Get invoice details by invoice ID."""
    res = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = res.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.get("/by-appointment/{appointment_id}", response_model=InvoiceResponse)
async def get_invoice_by_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user)
) -> Any:
    """Get invoice generated for a specific appointment."""
    res = await db.execute(select(Invoice).where(Invoice.appointment_id == appointment_id))
    invoice = res.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found for this appointment")
    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    inv_update: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    _staff = Depends(billing_staff)
) -> Any:
    """Update invoice, record payments, and mark as paid."""
    res = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = res.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    update_data = inv_update.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(invoice, field, val)

    # Auto-adjust status if full amount paid
    if invoice.paid_amount >= invoice.total_amount and invoice.status != InvoiceStatus.CANCELLED:
        invoice.status = InvoiceStatus.PAID

    await db.commit()
    await db.refresh(invoice)
    return invoice
