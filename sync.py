from zk import ZK
from db import SessionLocal, AttendanceLog
from sqlalchemy import exists, and_
import logging
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_machine_list(file_path="machines.txt"):
    try:
        with open(file_path, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Could not read machines.txt: {e}")
        return []

def sync_all_machines():
    machine_ips = get_machine_list()
    if not machine_ips:
        logger.warning("No machines to sync.")
        return 0

    total_added = 0
    db = SessionLocal()

    for ip in machine_ips:
        logger.info(f"Connecting to machine at {ip}...")
        zk = ZK(ip, port=4370, timeout=10, force_udp=False)
        conn = None
        try:
            conn = zk.connect()
            # Disable device while reading
            # conn.disable_device()
            attendances = conn.get_attendance()
            logger.info(f"Machine {ip}: Found {len(attendances)} records.")

            new_records = []
            for i, att in enumerate(attendances):
                user_id = str(att.user_id)
                timestamp = att.timestamp.replace(tzinfo=None)
                
                record_exists = db.query(AttendanceLog).filter(
                    AttendanceLog.employee_id == user_id,
                    AttendanceLog.attendance_time == timestamp,
                    AttendanceLog.machine_ip == ip
                ).first()

                if not record_exists:
                    new_log = AttendanceLog(
                        employee_id=user_id,
                        attendance_date=timestamp.date(),
                        attendance_time=timestamp,
                        machine_ip=ip
                    )
                    db.add(new_log)
                    new_records.append(new_log)
                    
                # Commit in batches of 100 for better throughput and visibility
                if len(new_records) >= 100:
                    db.commit()
                    total_added += len(new_records)
                    logger.info(f"Machine {ip}: Committed batch of {len(new_records)} records.")
                    new_records = []

            if new_records:
                db.commit()
                total_added += len(new_records)
                logger.info(f"Machine {ip}: Added final {len(new_records)} records.")
            else:
                logger.info(f"Machine {ip}: Sync finished (no more new records).")

            # conn.enable_device()
        except Exception as e:
            logger.error(f"Error syncing machine {ip}: {e}")
            db.rollback()
        finally:
            if conn:
                try:
                    conn.disconnect()
                except:
                    pass

    db.close()
    return total_added

if __name__ == "__main__":
    count = sync_all_machines()
    print(f"Sync complete. Total new records added: {count}")
