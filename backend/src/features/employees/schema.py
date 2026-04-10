from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import date, datetime

class EmployeeBase(BaseModel):
    employee_id: str
    emp_name: Optional[str] = None

class EmployeeOut(EmployeeBase):
    department: Optional[str] = None
    group_name: Optional[str] = None
    start_date: Optional[date] = None
    shift: Optional[str] = None
    source_status: str
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class EmployeeListOut(BaseModel):
    items: List[EmployeeOut]
    total_count: int
    page: int
    page_size: int
    total_pages: int

class EmployeeUpdate(BaseModel):
    emp_name: Optional[str] = None
    department: Optional[str] = None
    group_name: Optional[str] = None
    shift: Optional[str] = None

class UpdateStatusOut(BaseModel):
    is_running: bool
    status: str
    progress: Optional[int] = 0

class DeleteHardwareOut(BaseModel):
    results: Dict[str, str]

class UpdateHardwareOut(BaseModel):
    results: Dict[str, str]

class BiometricCoverageOut(BaseModel):
    ip: str
    status: str
    has_user: bool
    has_finger: bool
    error: Optional[str] = None
