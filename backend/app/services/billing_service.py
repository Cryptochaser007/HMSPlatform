"""Billing service: invoice generation, itemized charges, payment processing."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import Bill, BillItem, Payment, PaymentStatus
from app.schemas.billing import BillCreate, PaymentCreate
from app.utils.helpers import generate_bill_number, generate_receipt_number


class BillingService:
    """Business logic for OPD/IPD billing, payment collections, receipts, and summaries."""

    async def create_bill(self, db: AsyncSession, data: BillCreate, created_by: str) -> Bill:
        bill_no = generate_bill_number()

        subtotal = Decimal("0.00")
        tax_total = Decimal("0.00")

        bill_items = []
        for item_data in data.items:
            unit_price = Decimal(str(item_data.unit_price))
            qty = Decimal(str(item_data.quantity))
            disc_pct = Decimal(str(item_data.discount_percent))
            tax_pct = Decimal(str(item_data.tax_percent))

            gross = unit_price * qty
            disc_val = gross * (disc_pct / Decimal("100.00"))
            after_disc = gross - disc_val
            tax_val = after_disc * (tax_pct / Decimal("100.00"))
            line_total = after_disc + tax_val

            subtotal += gross
            tax_total += tax_val

            bill_item = BillItem(
                item_type=item_data.item_type,
                description=item_data.description,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                discount_percent=item_data.discount_percent,
                tax_percent=item_data.tax_percent,
                total=line_total,
                reference_id=item_data.reference_id,
            )
            bill_items.append(bill_item)

        discount_amount = Decimal(str(data.discount_amount))
        total_amount = (subtotal - discount_amount) + tax_total

        bill = Bill(
            bill_number=bill_no,
            encounter_id=data.encounter_id,
            patient_id=data.patient_id,
            bill_type=data.bill_type,
            subtotal=subtotal,
            discount_amount=discount_amount,
            tax_amount=tax_total,
            total_amount=total_amount,
            payment_status=PaymentStatus.PENDING,
            notes=data.notes,
            created_by=created_by,
        )
        bill.items = bill_items
        db.add(bill)
        await db.flush()
        await db.refresh(bill)
        return bill

    async def get_bill(self, db: AsyncSession, bill_id: str) -> Bill:
        result = await db.execute(
            select(Bill)
            .options(selectinload(Bill.items), selectinload(Bill.payments))
            .where(Bill.id == bill_id, Bill.is_deleted == False)  # noqa: E712
        )
        bill = result.scalar_one_or_none()
        if bill is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
        return bill

    async def list_bills(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        patient_id: Optional[str] = None,
        payment_status: Optional[str] = None,
    ) -> dict:
        query = select(Bill).options(selectinload(Bill.items)).where(Bill.is_deleted == False)  # noqa: E712
        if patient_id:
            query = query.where(Bill.patient_id == patient_id)
        if payment_status:
            query = query.where(Bill.payment_status == payment_status)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_q)).scalar() or 0

        query = query.order_by(Bill.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = list((await db.execute(query)).scalars().all())
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    async def record_payment(
        self, db: AsyncSession, data: PaymentCreate, received_by: str
    ) -> Payment:
        bill = await self.get_bill(db, data.bill_id)
        if bill.payment_status == PaymentStatus.PAID:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bill is already fully paid")
        if bill.payment_status == PaymentStatus.CANCELLED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot pay against cancelled bill")

        rcp_no = generate_receipt_number()
        payment = Payment(
            bill_id=data.bill_id,
            amount=data.amount,
            payment_method=data.payment_method,
            transaction_reference=data.transaction_reference,
            payment_date=datetime.now(timezone.utc),
            received_by=received_by,
            receipt_number=rcp_no,
            notes=data.notes,
        )
        db.add(payment)

        # Calculate total paid so far
        total_paid = sum(Decimal(str(p.amount)) for p in bill.payments) + Decimal(str(data.amount))
        if total_paid >= Decimal(str(bill.total_amount)):
            bill.payment_status = PaymentStatus.PAID
        elif total_paid > Decimal("0.00"):
            bill.payment_status = PaymentStatus.PARTIAL

        await db.flush()
        await db.refresh(payment)
        return payment

    async def cancel_bill(self, db: AsyncSession, bill_id: str) -> Bill:
        bill = await self.get_bill(db, bill_id)
        if bill.payments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel bill with existing payments. Process refund first.",
            )
        bill.payment_status = PaymentStatus.CANCELLED
        await db.flush()
        return bill

    async def get_billing_summary(self, db: AsyncSession, period: str = "today") -> dict:
        query = select(Bill).where(Bill.is_deleted == False)  # noqa: E712
        bills = list((await db.execute(query)).scalars().all())

        total_bills = len(bills)
        total_amount = sum(Decimal(str(b.total_amount)) for b in bills)
        paid_amount = sum(
            Decimal(str(b.total_amount)) for b in bills if b.payment_status == PaymentStatus.PAID
        )
        pending_amount = sum(
            Decimal(str(b.total_amount))
            for b in bills
            if b.payment_status in (PaymentStatus.PENDING, PaymentStatus.PARTIAL)
        )
        cancelled_amount = sum(
            Decimal(str(b.total_amount)) for b in bills if b.payment_status == PaymentStatus.CANCELLED
        )

        return {
            "total_bills": total_bills,
            "total_amount": total_amount,
            "total_collected": paid_amount,
            "total_pending": pending_amount,
            "total_cancelled": cancelled_amount,
            "period": period,
        }


billing_service = BillingService()

