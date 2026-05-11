from pydantic import BaseModel
from typing import Optional
from datetime import time

class ShiftDefinitionBase(BaseModel):
    shift_code: str
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    ot_start_time: Optional[time] = None
    is_night_shift: bool = False

    break_hours: float = 0.0
    work_hours: float = 0.0
    leave_hours_p: float = 0.0
    leave_hours_r: float = 0.0
    leave_hours_o: float = 0.0
    leave_hours_t: float = 0.0
    leave_hours_c: float = 0.0
    leave_hours_k: float = 0.0

    standard_hours: float = 8.0
    workday_base: float = 8.0
    description: Optional[str] = None
    # 'NORMAL' | 'HOLIDAY' | 'ROTATION'
    shift_category: Optional[str] = "NORMAL"

class ShiftDefinitionCreate(ShiftDefinitionBase):
    pass

class ShiftDefinitionUpdate(BaseModel):
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    ot_start_time: Optional[time] = None
    is_night_shift: Optional[bool] = None

    break_hours: Optional[float] = None
    work_hours: Optional[float] = None
    leave_hours_p: Optional[float] = None
    leave_hours_r: Optional[float] = None
    leave_hours_o: Optional[float] = None
    leave_hours_t: Optional[float] = None
    leave_hours_c: Optional[float] = None
    leave_hours_k: Optional[float] = None
    standard_hours: Optional[float] = None
    workday_base: Optional[float] = None
    description: Optional[str] = None
    shift_category: Optional[str] = None

class ShiftDefinitionSchema(ShiftDefinitionBase):
    class Config:
        from_attributes = True
