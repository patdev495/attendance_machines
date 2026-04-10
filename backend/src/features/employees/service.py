from sqlalchemy.orm import Session
from database import EmployeeLocalRegistry, EmployeeMetadata, AttendanceLog, SessionLocal
from config import config
from utils.encoding import sanitize_machine_name
from features.logs.service import get_machine_list
from sync_service import get_users_from_machine, delete_user_from_machine, update_user_name_on_machine
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
import logging

logger = logging.getLogger(__name__)

def update_registry(db: Session):
    """
    Update EmployeeLocalRegistry from 3 sources:
    1. Excel (EmployeeMetadata)
    2. Machines (get_users_from_machine)
    3. Logs (AttendanceLogs)
    """
    try:
        # 1. Update from Excel
        excel_users = db.query(EmployeeMetadata).all()
        for emp in excel_users:
            registry_entry = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id == emp.employee_id).first()
            if not registry_entry:
                registry_entry = EmployeeLocalRegistry(employee_id=emp.employee_id)
                db.add(registry_entry)
            
            registry_entry.emp_name = emp.emp_name
            registry_entry.department = emp.department
            registry_entry.group_name = emp.group
            registry_entry.start_date = emp.start_date
            registry_entry.shift = emp.shift
            registry_entry.source_status = 'excel_synced'
        db.commit()

        # 2. Update from Machines
        ips = get_machine_list()
        for ip in ips:
            users, status = get_users_from_machine(ip)
            if status == "Success":
                for u in users:
                    emp_id = str(u.get('user_id'))
                    registry_entry = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id == emp_id).first()
                    if not registry_entry:
                        registry_entry = EmployeeLocalRegistry(
                            employee_id=emp_id,
                            machine_name=u.get('name'),
                            source_status='machine_only'
                        )
                        db.add(registry_entry)
                    else:
                        # Existing user, maybe update machine_name but don't overwrite excel_synced status
                        if registry_entry.source_status != 'excel_synced':
                            if registry_entry.source_status == 'log_only':
                                registry_entry.source_status = 'machine_only'
                            registry_entry.machine_name = u.get('name')
                        else:
                            registry_entry.machine_name = u.get('name')
        db.commit()

        # 3. Update from Logs
        log_users = db.query(AttendanceLog.employee_id).distinct().all()
        for (emp_id,) in log_users:
            registry_entry = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id == emp_id).first()
            if not registry_entry:
                registry_entry = EmployeeLocalRegistry(
                    employee_id=emp_id,
                    source_status='log_only'
                )
                db.add(registry_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Error updating registry: {e}")
        db.rollback()
        raise

def delete_user_from_hardware(employee_id: str):
    """
    Deletes user ONLY from hardware, does not delete from DB.
    Uses ThreadPoolExecutor for parallel processing.
    """
    ips = get_machine_list()
    results = {}
    
    with ThreadPoolExecutor(max_workers=max(1, len(ips))) as executor:
        future_to_ip = {executor.submit(delete_user_from_machine, ip, employee_id): ip for ip in ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                result = future.result()
                results[ip] = result
            except Exception as e:
                results[ip] = f"Error: {str(e)}"
    return results

def update_employee_info(employee_id: str, db_name: str, db: Session):
    """
    Updates user info in EmployeeLocalRegistry, EmployeeMetadata, and propagates
    the updated name to all connected machines.
    """
    # 1. Update EmployeeLocalRegistry
    registry_entry = db.query(EmployeeLocalRegistry).filter(EmployeeLocalRegistry.employee_id == employee_id).first()
    if registry_entry:
        registry_entry.emp_name = db_name
        
    # 2. Update EmployeeMetadata
    meta_entry = db.query(EmployeeMetadata).filter(EmployeeMetadata.employee_id == employee_id).first()
    if meta_entry:
        meta_entry.emp_name = db_name
        
    db.commit()
    
    return {"status": "success", "message": "Updated in DB"}
