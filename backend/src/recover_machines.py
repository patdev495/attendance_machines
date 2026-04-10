from database import SessionLocal, AttendanceLog
from sqlalchemy import func
import os

def recover_machines():
    print("Checking database for machine IPs...")
    db = SessionLocal()
    try:
        # Get unique machine IPs from logs
        ips = db.query(AttendanceLog.machine_ip).distinct().all()
        ip_list = [ip[0] for ip in ips if ip[0]]
        
        if not ip_list:
            # Try getting from any other source? 
            # In this project, IPs are usually 192.168.1.201, 202, etc.
            print("No IPs found in logs.")
            return

        print(f"Found {len(ip_list)} IPs: {', '.join(ip_list)}")
        
        # Root directory is d:\Workspace\Time_Attendance_Machine
        # We are likely running from there
        machines_file = "machines.txt"
        with open(machines_file, "w") as f:
            for ip in ip_list:
                f.write(f"{ip}\n")
        
        print(f"Successfully recovered {machines_file}")
    except Exception as e:
        print(f"Recovery failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    recover_machines()
