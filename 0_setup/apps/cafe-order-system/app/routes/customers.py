from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Order
from app.schemas import CustomerCreate, CustomerResponse

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("/", response_model=list[CustomerResponse])
def list_customers(
    department: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Customer)
    if department:
        query = query.filter(Customer.department == department)
    return query.all()


@router.get("/{employee_id}", response_model=CustomerResponse)
def get_customer(employee_id: str, db: Session = Depends(get_db)):
    customer = (
        db.query(Customer).filter(Customer.employee_id == employee_id).first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("/", response_model=CustomerResponse, status_code=201)
def register_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(Customer)
        .filter(Customer.employee_id == customer.employee_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Employee already registered")
    db_customer = Customer(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.get("/{employee_id}/orders")
def get_customer_orders(employee_id: str, db: Session = Depends(get_db)):
    customer = (
        db.query(Customer).filter(Customer.employee_id == employee_id).first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    orders = (
        db.query(Order)
        .filter(Order.customer_id == customer.id)
        .order_by(Order.created_at.desc())
        .limit(20)
        .all()
    )
    return orders
