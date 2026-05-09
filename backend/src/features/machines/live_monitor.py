import threading
import time
import requests
import logging
from concurrent.futures import ThreadPoolExecutor
from zk import ZK
from sqlalchemy import func
from database import SessionLocal, AttendanceLog, EmployeeLocalRegistry
from shared.hardware import get_machine_list, get_live_machine_list
from shared.socket_manager import manager
import asyncio

logger = logging.getLogger(__name__)

class LiveMonitorManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.active_monitors = {} # ip -> thread/future
        self.meal_configs = {}    # ip -> meal_url
        self.canteen_ips = set()  # IPs tagged as canteen
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
        """Periodically checks machine list and ensures only permitted monitors are active."""
        while self.is_running:
            try:
                # Use the new filtered list for Live Mode
                live_configs = get_live_machine_list()
                live_ips_set = set(cfg['ip'] for cfg in live_configs)
                print(f"DEBUG: Live Monitor Manager found {len(live_configs)} machines to monitor.")

                for cfg in live_configs:
                    ip = cfg['ip']
                    self.meal_configs[ip] = cfg['meal_url']
                    if cfg.get('is_canteen'):
                        self.canteen_ips.add(ip)
                    else:
                        self.canteen_ips.discard(ip)
                    # Start monitor if it's new or the previous thread died
                    if ip not in self.active_monitors or not self.active_monitors[ip].is_alive():
                        print(f"DEBUG: Starting monitor thread for {ip}")
                        self._start_monitor(ip)
                
                # Stop monitors for IPs that are no longer marked as live
                # (either removed from file or marked with # nolive)
                monitored_ips = list(self.active_monitors.keys())
                for ip in monitored_ips:
                    if ip not in live_ips_set:
                        # By removing it from active_monitors, the thread will see 
                        # ip not in self.active_monitors and exit its loop.
                        if self.active_monitors[ip].is_alive():
                           logger.info(f"Stopping live monitor for {ip} (config changed)")
                        del self.active_monitors[ip]
                        if ip in self.meal_configs:
                            del self.meal_configs[ip]
                           
            except Exception as e:
                logger.error(f"Error in Live Monitor management loop: {e}")
            
            # Wait 10 seconds before next check for machines.txt changes
            for _ in range(10):
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
        print(f"DEBUG: Starting monitor loop for {ip}")
        # Thread exits if manager stops OR if this IP is no longer in active_monitors
        while self.is_running and ip in self.active_monitors:
            print(f"DEBUG: Attempting connection to {ip}")
            zk = ZK(ip, port=4370, timeout=10, force_udp=False)
            conn = None
            try:
                conn = zk.connect()
                logger.info(f"Monitor connected to {ip}")
                print(f"DEBUG: Monitor connected to {ip}. Entering live_capture...")
                
                # live_capture is a generator that yields attendance records
                for event in conn.live_capture():
                    if not self.is_running or ip not in self.active_monitors:
                        print(f"DEBUG: Monitor loop for {ip} stopping (manager stopped or IP removed)")
                        break
                    if event is None:
                        # This happens on timeout, just keep waiting
                        continue
                        
                    print(f"DEBUG: RECEIVED EVENT from {ip}: {event}")
                    self._process_event(ip, event)
                    
            except Exception as e:
                if self.is_running:
                    logger.error(f"Monitor error on {ip}: {e}. Retrying in 5s...")
                    print(f"DEBUG: Monitor ERROR on {ip}: {e}")
                    time.sleep(5)
            finally:
                if conn:
                    try: conn.disconnect()
                    except: pass
                print(f"DEBUG: Monitor loop for {ip} disconnected/restarting in 5s")
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

            # 3. Enrich with meal info if this is a canteen machine
            meal_info = None
            if ip in self.canteen_ips:
                try:
                    from features.meal_tracking.service import check_meal_by_machine_id, log_meal_swipe
                    meal_info = check_meal_by_machine_id(user_id, timestamp.date())
                    if meal_info:
                        logger.info(f"MEAL FOUND for {user_id}: {meal_info.get('meal_name_vi', '?')}")
                    else:
                        logger.info(f"NO MEAL registered for {user_id} on {timestamp.date()}")
                        
                    # Log swipe to MealTrackingHistory
                    log_meal_swipe(user_id, ip, timestamp, meal_info)
                except Exception as e:
                    logger.error(f"Error querying/logging meal info: {e}")

            # 4. Broadcast to WebSockets
            payload = {
                "type": "meal_event" if ip in self.canteen_ips else "new_log",
                "data": {
                    "employee_id": user_id,
                    "emp_name": emp_name,
                    "department": emp.department if emp else "-",
                    "attendance_time": timestamp.isoformat(),
                    "machine_ip": ip,
                    "is_live": True,
                    "is_canteen": ip in self.canteen_ips,
                    "meal_info": meal_info
                }
            }
            self._broadcast_async(payload)

            # 4. Meal Ticket Webhook (Target API)
            meal_url = self.meal_configs.get(ip)
            if meal_url:
                def send_meal_hook():
                    try:
                        # Fetch extra info if possible (department)
                        dept = emp.department if emp else "-"
                        hook_data = {
                            "employee_id": user_id,
                            "emp_name": emp_name,
                            "department": dept,
                            "timestamp": timestamp.isoformat(),
                            "machine_ip": ip
                        }
                        logger.info(f"Sending meal ticket hook to {meal_url} for {user_id}")
                        resp = requests.post(meal_url, json=hook_data, timeout=5)
                        if resp.status_code >= 400:
                            logger.error(f"Meal hook error {resp.status_code}: {resp.text}")
                    except Exception as ex:
                        logger.error(f"Failed to send meal hook: {ex}")
                
                # Run in a separate thread to avoid blocking the monitor loop
                threading.Thread(target=send_meal_hook, daemon=True).start()


        except Exception as e:
            logger.error(f"Error processing live event: {e}")
            db.rollback()
        finally:
            db.close()

    def set_loop(self, loop):
        self._loop = loop

    def _broadcast_async(self, payload):
        if self._loop and self._loop.is_running():
            print(f"DEBUG: Broadcasting event to WebSockets: {payload['data']['employee_id']}")
            asyncio.run_coroutine_threadsafe(manager.broadcast(payload), self._loop)
        else:
            print("DEBUG: Cannot broadcast - loop not running or not set")
            pass

# Global instance
live_monitor = LiveMonitorManager()
