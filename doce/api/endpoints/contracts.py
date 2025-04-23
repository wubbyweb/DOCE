from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import os
import shutil
from datetime import datetime

from doce.api.auth import get_current_active_user, check_manager_role
from doce.config import settings
from doce.database import get_db
from doce.database.models import Contract as ContractModel, User as UserModel
from doce.models import Contract, ContractCreate, ContractUpdate

router = APIRouter()


@router.post("/", response_model=Contract, status_code=status.HTTP_201_CREATED)
async def create_contract(
    vendor_name: str = Form(...),
    start_date: Optional[datetime] = Form(None),
    end_date: Optional[datetime] = Form(None),
    contract_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Create a new contract with file upload.
    """
    # Ensure contract storage directory exists
    os.makedirs(settings.file_storage.contract_path, exist_ok=True)
    
    # Create a unique filename
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_vendor_name = "".join(c if c.isalnum() else "_" for c in vendor_name)
    filename = f"{safe_vendor_name}_{timestamp}_{contract_file.filename}"
    file_path = os.path.join(settings.file_storage.contract_path, filename)
    
    # Save the uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(contract_file.file, buffer)
    
    # Create contract record in database
    db_contract = ContractModel(
        vendor_name=vendor_name,
        file_path=file_path,
        start_date=start_date,
        end_date=end_date
    )
    
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)
    return db_contract


@router.get("/", response_model=List[Contract])
def read_contracts(
    skip: int = 0,
    limit: int = 100,
    vendor_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get all contracts with optional vendor name filter.
    """
    query = db.query(ContractModel)
    
    if vendor_name:
        query = query.filter(ContractModel.vendor_name.ilike(f"%{vendor_name}%"))
    
    contracts = query.offset(skip).limit(limit).all()
    return contracts


@router.get("/{contract_id}", response_model=Contract)
def read_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get a specific contract by ID.
    """
    db_contract = db.query(ContractModel).filter(ContractModel.id == contract_id).first()
    if db_contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    return db_contract


@router.put("/{contract_id}", response_model=Contract)
def update_contract(
    contract_id: int,
    contract: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(check_manager_role)
):
    """
    Update a contract (manager or admin only).
    """
    db_contract = db.query(ContractModel).filter(ContractModel.id == contract_id).first()
    if db_contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    
    update_data = contract.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_contract, key, value)
    
    db.commit()
    db.refresh(db_contract)
    return db_contract


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(check_manager_role)
):
    """
    Delete a contract (manager or admin only).
    """
    db_contract = db.query(ContractModel).filter(ContractModel.id == contract_id).first()
    if db_contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    
    # Delete the contract file if it exists
    if os.path.exists(db_contract.file_path):
        os.remove(db_contract.file_path)
    
    db.delete(db_contract)
    db.commit()
    return None