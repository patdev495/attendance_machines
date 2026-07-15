from config import DEMO_MODE

from database import SessionLocal, AttendanceLog
from config import config
import logging
import datetime
import threading
from shared.hardware import get_all_machine_configs, get_machine_list

from features.hanvon.client import HanvonClient, iter_dates

logger = logging.getLogger(__name__)

# Progress Tracking State for Logs
sync_status = {
    "is_running": False,
    "total_machines": 0,
    "current_machine_index": 0,
    "current_machine_ip": "",
    "processed_count": 0,
    "last_sync_time": None,
    "fail_count": 0,
    "total_added": 0
}

status_lock = threading.Lock()

def sync_all_machines(start_date: datetime.date | None = None, end_date: datetime.date | None = None):
    global sync_status
    
    if DEMO_MODE:
        logger.info("[DEMO] sync_all_machines skipped — no hardware in demo mode")
        with status_lock:
            sync_status["is_running"] = False
            sync_status["total_added"] = 0
        return 0
    
    machine_configs = get_all_machine_configs()
    
    with status_lock:
        if not sync_status["is_running"]:
            # Direct call (not pre-initialized by router) - set state now
            sync_status["is_running"] = True
            sync_status["total_machines"] = len(machine_configs)
            sync_status["current_machine_index"] = 0
            sync_status["total_added"] = 0
            sync_status["fail_count"] = 0

    if not machine_configs:
        with status_lock:
            sync_status["is_running"] = False
        return 0

    local_total_added = 0
    db = SessionLocal()

    for i, machine in enumerate(machine_configs):
        ip = machine["ip"]
        protocol = machine.get("protocol", "hanvon")
        with status_lock:
            sync_status["current_machine_index"] = i + 1
            sync_status["current_machine_ip"] = ip
            
        try:
            logger.info(f"Connecting to {protocol} machine {i+1}/{len(machine_configs)} at {ip}...")
            added = _sync_hanvon_machine(db, ip, start_date, end_date)
            local_total_added += added
            
            logger.info(f"Machine {ip}: Finished. Added {added} records, {local_total_added} total.")
            
        except Exception as e:
            logger.error(f"Error syncing machine {ip}: {e}")
            db.rollback()
            with status_lock:
                sync_status["fail_count"] += 1

    db.close()
    
    with status_lock:
        sync_status["is_running"] = False
        sync_status["total_added"] = local_total_added
        sync_status["last_sync_time"] = datetime.datetime.now().isoformat()
    
    return local_total_added

def _sync_hanvon_machine(
    db,
    ip: str,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
) -> int:
    today = datetime.date.today()
    requested_start = start_date
    requested_end = end_date
    if requested_start and requested_end and requested_start > requested_end:
        requested_start, requested_end = requested_end, requested_start

    full_device_sync = requested_start is None and requested_end is None
    range_start = requested_start or config.HANVON_FULL_SYNC_START_DATE
    range_end = requested_end or today

    added = 0
    new_logs = []
    device_seen_keys = set()
    existing_keys_by_date: dict[datetime.date, set[tuple[str, datetime.datetime]]] = {}
    with HanvonClient(
        ip,
        port=config.HANVON_PORT,
        secret_key=config.HANVON_SECRET_KEY,
    ) as client:
        device_info = client.get_device_info()
        device_record_count = int(device_info.get("real_facerecord") or 0)
        logger.info(
            "Hanvon machine %s: connected model=%s sn=%s records=%s",
            ip,
            device_info.get("model") or device_info.get("type"),
            device_info.get("sn"),
            device_info.get("real_facerecord"),
        )
        if full_device_sync and device_record_count == 0:
            return 0

        if full_device_sync:
            dates_to_query = _iter_dates_desc(range_end, range_start)
            logger.info(
                "Hanvon machine %s: full sync from %s back to %s until %s device records are seen",
                ip,
                range_end,
                range_start,
                device_record_count,
            )
        else:
            dates_to_query = iter_dates(range_start, range_end)
            logger.info("Hanvon machine %s: range sync from %s to %s", ip, range_start, range_end)

        for target_date in dates_to_query:
            records = client.get_records_by_day(target_date)
            logger.info("Hanvon machine %s: %s records on %s", ip, len(records), target_date)
            for record in records:
                user_id = record.employee_id.strip()
                timestamp = record.attendance_time.replace(tzinfo=None)
                device_seen_keys.add((user_id, timestamp))
                if user_id == '1':
                    continue

                attendance_date = timestamp.date()
                existing_keys = existing_keys_by_date.get(attendance_date)
                if existing_keys is None:
                    existing_keys = load_existing_log_keys(db, ip, attendance_date)
                    existing_keys_by_date[attendance_date] = existing_keys

                if (user_id, timestamp) in existing_keys:
                    continue

                new_item = AttendanceLog(
                    employee_id=user_id,
                    attendance_date=attendance_date,
                    attendance_time=timestamp,
                    machine_ip=ip
                )
                db.add(new_item)
                new_logs.append(new_item)
                existing_keys.add((user_id, timestamp))

                if len(new_logs) >= 500:
                    db.commit()
                    added += len(new_logs)
                    new_logs = []

            if full_device_sync and device_record_count and len(device_seen_keys) >= device_record_count:
                logger.info(
                    "Hanvon machine %s: full sync reached device record count (%s)",
                    ip,
                    device_record_count,
                )
                break

    if new_logs:
        db.commit()
        added += len(new_logs)
    return added

def load_existing_log_keys(
    db,
    ip: str,
    attendance_date: datetime.date,
) -> set[tuple[str, datetime.datetime]]:
    rows = db.query(AttendanceLog.employee_id, AttendanceLog.attendance_time).filter(
        AttendanceLog.machine_ip == ip,
        AttendanceLog.attendance_date == attendance_date,
    ).all()
    return {
        (employee_id, attendance_time.replace(tzinfo=None))
        for employee_id, attendance_time in rows
    }

def _iter_dates_desc(start_date: datetime.date, end_date: datetime.date):
    current = start_date
    while current >= end_date:
        yield current
        current -= datetime.timedelta(days=1)

def get_users_from_machine(ip: str):
    """Fetch Hanvon employee and manager IDs from a specific machine."""
    try:
        with HanvonClient(
            ip,
            port=config.HANVON_PORT,
            secret_key=config.HANVON_SECRET_KEY,
            timeout=15,
        ) as client:
            employee_ids, face_ids = client.get_employee_ids()
            manager_ids = client.get_manager_ids()

        users = [
            {"user_id": employee_id, "has_face": employee_id in face_ids, "role": "Employee"}
            for employee_id in employee_ids
        ]
        for manager_id in manager_ids:
            existing = next((u for u in users if u["user_id"] == manager_id), None)
            if existing:
                existing["role"] = "Machine Manager"
            else:
                users.append({"user_id": manager_id, "has_face": False, "role": "Machine Manager"})
        return users, "Success"
    except Exception as e:
        logger.error(f"Error fetching Hanvon users from machine {ip}: {e}")
        return [], str(e)
