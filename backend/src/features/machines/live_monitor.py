import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from zk import ZK
from sqlalchemy import func
from database import SessionLocal, AttendanceLog, EmployeeLocalRegistry
from shared.hardware import get_machine_list
from shared.socket_manager import manager
import asyncio

logger = logging.getLogger(__name__)

class LiveMonitorManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.active_monitors = {} # ip -> thread/future
        self.is_running = False
        self._loop = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        logger.info("Starting Live Monitor Manager...")
        
        # Start management loop in a background thread
        management_thread = threading.Thread(target=self._management_loop, daemon=True)
        management_thread.start()

    def _management_loop(self):
        """Periodically checks machine list and ensures all monitors are active."""
        while self.is_running:
            try:
                ips = get_machine_list()
                for ip in ips:
                    # Start monitor if it's new or the previous thread died
                    if ip not in self.active_monitors or not self.active_monitors[ip].is_alive():
                        self._start_monitor(ip)
                
                # Optional: Clean up monitors for IPs that are no longer in the list
                current_ips = set(ips)
                monitored_ips = list(self.active_monitors.keys())
                for ip in monitored_ips:
                    if ip not in current_ips:
                        # Monitor for removed IP will stop eventually due to is_running being False 
                        # or we can add a more specific stop flag if needed.
                        # For now, just remove from tracking map.
                        if not self.active_monitors[ip].is_alive():
                           del self.active_monitors[ip]
                           
            except Exception as e:
                logger.error(f"Error in Live Monitor management loop: {e}")
            
            # Wait 60 seconds before next check
            for _ in range(60):
                if not self.is_running: break
                time.sleep(1)

    def stop(self):
        self.is_running = False
        logger.info("Stopping Live Monitor Manager...")
        # Threads will exit on their next loop iteration or timeout

    def _start_monitor(self, ip):
        if ip in self.active_monitors and self.active_monitors[ip].is_alive():
            return
        
        thread = threading.Thread(target=self._monitor_loop, args=(ip,), daemon=True)
        thread.start()
        self.active_monitors[ip] = thread
        logger.info(f"Started live monitor thread for {ip}")

    def _monitor_loop(self, ip):
        """Background loop for a single machine."""
        while self.is_running:
            zk = ZK(ip, port=4370, timeout=10, force_udp=False)
            conn = None
            try:
                conn = zk.connect()
                logger.info(f"Monitor connected to {ip}")
                
                # live_capture is a generator that yields attendance records
                for event in conn.live_capture():
                    if not self.is_running:
                        break
                    if event is None:
                        continue
                        
                    self._process_event(ip, event)
                    
            except Exception as e:
                if self.is_running:
                    logger.error(f"Monitor error on {ip}: {e}. Retrying in 30s...")
                    time.sleep(30)
            finally:
                if conn:
                    try: conn.disconnect()
                    except: pass
                time.sleep(5) # Cooldown before reconnect

    def _process_event(self, ip, event):
        """Processes a single live attendance event."""
        user_id = str(event.user_id)
        # Skip system user '1' if necessary (custom logic from logs/service.py)
        if user_id == '1':
            return

        timestamp = event.timestamp
        logger.info(f"LIVE EVENT: Machine {ip}, User {user_id}, Time {timestamp}")

        # 1. Save to DB
        db = SessionLocal()
        try:
            # Check if exists to avoid double-processing (live_capture can sometimes repeat)
            exists = db.query(AttendanceLog).filter(
                AttendanceLog.employee_id == user_id,
                AttendanceLog.attendance_time == timestamp,
                AttendanceLog.machine_ip == ip
            ).first()

            if not exists:
                new_log = AttendanceLog(
                    employee_id=user_id,
                    attendance_date=timestamp.date(),
                    attendance_time=timestamp,
                    machine_ip=ip
                )
                db.add(new_log)
                db.commit()
                logger.debug(f"Saved live log for {user_id} to DB")
            
            # 2. Get Employee Name for broadcast
            emp = db.query(EmployeeLocalRegistry).filter(
                func.ltrim(func.rtrim(EmployeeLocalRegistry.employee_id)) == user_id.strip()
            ).first()
            emp_name = emp.emp_name if emp else f"ID: {user_id}"

            # 3. Broadcast to WebSockets
            # Since this is in a thread, we use a helper to bridge to the async manager
            payload = {
                "type": "new_log",
                "data": {
                    "employee_id": user_id,
                    "emp_name": emp_name,
                    "attendance_time": timestamp.isoformat(),
                    "machine_ip": ip,
                    "is_live": True
                }
            }
            
            # Use asyncio.run_coroutine_threadsafe if we have a loop, 
            # but for simplicity since we don't have easy access to the main loop here 
            # without more plumbing, we can use a simpler broadcast pattern 
            # OR register the loop on startup.
            self._broadcast_async(payload)

        except Exception as e:
            logger.error(f"Error processing live event: {e}")
            db.rollback()
        finally:
            db.close()

    def set_loop(self, loop):
        self._loop = loop

    def _broadcast_async(self, payload):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(payload), self._loop)
        else:
            # Fallback for startup/shutdown edge cases
            pass

# Global instance
live_monitor = LiveMonitorManager()
