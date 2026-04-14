from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db, ShiftDefinition
from .schema import ShiftDefinitionSchema, ShiftDefinitionCreate, ShiftDefinitionUpdate

router = APIRouter(prefix="/api/shifts", tags=["Shifts"])

@router.get("/", response_model=List[ShiftDefinitionSchema])
def get_shifts(db: Session = Depends(get_db)):
    return db.query(ShiftDefinition).all()

@router.post("/", response_model=ShiftDefinitionSchema)
def create_shift(shift: ShiftDefinitionCreate, db: Session = Depends(get_db)):
    db_shift = db.query(ShiftDefinition).filter(ShiftDefinition.shift_code == shift.shift_code).first()
    if db_shift:
        raise HTTPException(status_code=400, detail="Shift code already exists")
    
    new_shift = ShiftDefinition(**shift.model_dump())
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)
    return new_shift

@router.put("/{shift_code}", response_model=ShiftDefinitionSchema)
def update_shift(shift_code: str, shift: ShiftDefinitionUpdate, db: Session = Depends(get_db)):
    db_shift = db.query(ShiftDefinition).filter(ShiftDefinition.shift_code == shift_code).first()
    if not db_shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    update_data = shift.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_shift, key, value)
    
    db.commit()
    db.refresh(db_shift)
    return db_shift

@router.delete("/{shift_code}")
def delete_shift(shift_code: str, db: Session = Depends(get_db)):
    db_shift = db.query(ShiftDefinition).filter(ShiftDefinition.shift_code == shift_code).first()
    if not db_shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    db.delete(db_shift)
    db.commit()
    return {"message": "Shift deleted successfully"}
