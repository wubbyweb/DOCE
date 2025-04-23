from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from doce.api.auth import get_current_active_user, check_manager_role
from doce.database import get_db
from doce.database.models import WorkflowRule as WorkflowRuleModel, User as UserModel
from doce.models import WorkflowRule, WorkflowRuleCreate, WorkflowRuleUpdate

router = APIRouter()


@router.post("/", response_model=WorkflowRule, status_code=status.HTTP_201_CREATED)
def create_workflow_rule(
    rule: WorkflowRuleCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(check_manager_role)
):
    """
    Create a new workflow rule (manager or admin only).
    """
    db_rule = WorkflowRuleModel(**rule.dict())
    
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


@router.get("/", response_model=List[WorkflowRule])
def read_workflow_rules(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get all workflow rules.
    """
    rules = db.query(WorkflowRuleModel).order_by(
        WorkflowRuleModel.priority.desc()
    ).offset(skip).limit(limit).all()
    return rules


@router.get("/{rule_id}", response_model=WorkflowRule)
def read_workflow_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get a specific workflow rule by ID.
    """
    db_rule = db.query(WorkflowRuleModel).filter(WorkflowRuleModel.id == rule_id).first()
    if db_rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow rule not found"
        )
    return db_rule


@router.put("/{rule_id}", response_model=WorkflowRule)
def update_workflow_rule(
    rule_id: int,
    rule: WorkflowRuleUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(check_manager_role)
):
    """
    Update a workflow rule (manager or admin only).
    """
    db_rule = db.query(WorkflowRuleModel).filter(WorkflowRuleModel.id == rule_id).first()
    if db_rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow rule not found"
        )
    
    update_data = rule.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_rule, key, value)
    
    db.commit()
    db.refresh(db_rule)
    return db_rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(check_manager_role)
):
    """
    Delete a workflow rule (manager or admin only).
    """
    db_rule = db.query(WorkflowRuleModel).filter(WorkflowRuleModel.id == rule_id).first()
    if db_rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow rule not found"
        )
    
    db.delete(db_rule)
    db.commit()
    return None