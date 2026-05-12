import threading
import time
import socket
import requests
from requests.adapters import HTTPAdapter
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
        self._recent_events = {}  # (user_id, ip) -> timestamp for dedup
        self._dedup_lock = threading.Lock()
        self._session = requests.Session() # Reuse connections for hooks
        self._session.mount('http://', HTTPAdapter(pool_connections=10, pool_maxsize=20))
        self._last_activity = {} # ip -> timestamp of last seen packet (including None)
        self._status = {}        # ip -> "connected" | "stuck" | "disconnected"

    @staticmethod
    def _test_network_reach(ip, port=4370, timeout=3):
        """Quick TCP reachability test — returns (ok, error_msg)."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip, port))
            s.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        logger.info("="*60)
        logger.info("LIVE MONITOR STARTUP DIAGNOSTICS")
        logger.info("="*60)
        logger.info(f"asyncio loop set: {self._loop is not None}")
        
        # Run a quick network reachability test for all machines
        live_configs = get_live_machine_list()
        logger.info(f"machines.txt returned {len(live_configs)} live machines")
        for cfg in live_configs:
            ip = cfg['ip']
            ok, err = self._test_network_reach(ip)
            status = "✓ REACHABLE" if ok else f"✗ UNREACHABLE ({err})"
            tag = " [CANTEEN]" if cfg.get('is_canteen') else ""
            logger.info(f"  {ip}{tag}: {status}")
        logger.info("="*60)
        
        # Start management loop in a background thread
        management_thread = threading.Thread(target=self._management_loop, daemon=True)
        management_thread.start()

    def _management_loop(self):
        """Periodically checks machine list and ensures only permitted monitors are active."""
        loop_count = 0
        while self.is_running:
            loop_count += 1
            try:
                # Use the new filtered list for Live Mode
                live_configs = get_live_machine_list()
                live_ips_set = set(cfg['ip'] for cfg in live_configs)
                
                # Log detailed state every 30 iterations (~5 min) or on first run
                verbose = (loop_count == 1 or loop_count % 30 == 0)
                if verbose:
                    alive = {ip for ip, t in self.active_monitors.items() if t.is_alive()}
                    dead = {ip for ip, t in self.active_monitors.items() if not t.is_alive()}
                    logger.info(
                        f"[MGMT #{loop_count}] configs={len(live_configs)} | "
                        f"active_threads={len(alive)} | dead_threads={len(dead)} | "
                        f"canteen={self.canteen_ips} | loop_ok={self._loop is not None and self._loop.is_running()}"
                    )
                    if dead:
                        logger.warning(f"[MGMT] Dead threads will be restarted: {dead}")

                for cfg in live_configs:
                    ip = cfg['ip']
                    self.meal_configs[ip] = cfg['meal_url']
                    if cfg.get('is_canteen'):
                        self.canteen_ips.add(ip)
                    else:
                        self.canteen_ips.discard(ip)
                    # Start monitor if it's new or the previous thread died
                    if ip not in self.active_monitors or not self.active_monitors[ip].is_alive():
                        logger.info(f"[MGMT] Starting monitor thread for {ip} (canteen={cfg.get('is_canteen', False)})")
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
                        if ip in self._last_activity:
                            del self._last_activity[ip]

                # Watchdog: If a thread is alive but hasn't seen any activity for > 60s,
                # it's likely stuck in a blocking read. We should restart it.
                now = time.time()
                for ip, last_ts in list(self._last_activity.items()):
                    if ip in self.active_monitors and self.active_monitors[ip].is_alive():
                        if now - last_ts > 60: # 6x the 10s timeout
                            logger.warning(f"[WATCHDOG] Machine {ip} seems stuck (no activity for {int(now-last_ts)}s). Restarting thread.")
                            self._status[ip] = "stuck"
                            del self.active_monitors[ip] 
                           
            except Exception as e:
                logger.error(f"Error in Live Monitor management loop: {e}", exc_info=True)
            
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
        retry_count = 0
        logger.info(f"[MONITOR {ip}] Thread started")
        # Thread exits if manager stops OR if this IP is no longer in active_monitors
        while self.is_running and ip in self.active_monitors:
            retry_count += 1
            
            # Quick network reachability test before attempting ZK connection
            ok, err = self._test_network_reach(ip)
            if not ok:
                logger.error(f"[MONITOR {ip}] Network unreachable (attempt #{retry_count}): {err}")
                time.sleep(10)  # Back off longer when network is down
                continue
            
            logger.info(f"[MONITOR {ip}] Connecting (attempt #{retry_count})...")
            zk = ZK(ip, port=4370, timeout=10, force_udp=False)
            conn = None
            try:
                conn = zk.connect()
                retry_count = 0  # Reset on successful connect
                self._status[ip] = "connected"
                self._last_activity[ip] = time.time()
                logger.info(f"[MONITOR {ip}] Connected OK — entering live_capture")
                
                # Ignore buffered/replayed events that arrive immediately upon connection
                ignore_until = time.time() + 2
                
                # live_capture is a generator that yields attendance records
                for event in conn.live_capture():
                    # Update activity timestamp every time we get something (even None on timeout)
                    self._last_activity[ip] = time.time()

                    if not self.is_running or ip not in self.active_monitors:
                        logger.info(f"[MONITOR {ip}] Stopping (manager stopped or IP removed)")
                        break
                    
                    if event is None:
                        # This happens on timeout (10s), just keep waiting
                        continue
                        
                    if time.time() < ignore_until:
                        logger.debug(f"[MONITOR {ip}] Skipping replayed event: {event}")
                        continue
                        
                    logger.info(f"[MONITOR {ip}] EVENT: user_id={event.user_id}, time={event.timestamp}")
                    self._process_event(ip, event)
                    
            except Exception as e:
                if self.is_running:
                    self._status[ip] = "disconnected"
                    logger.error(f"[MONITOR {ip}] Error (attempt #{retry_count}): {e}")
                    time.sleep(5)
            finally:
                if conn:
                    try: 
                        # Ensure we really clear the SDK state
                        conn.disconnect()
                    except: pass
                logger.info(f"[MONITOR {ip}] Disconnected — cooldown 5s before reconnect")
                time.sleep(5) # Cooldown before reconnect

    def _process_event(self, ip, event):
        """Processes a single live attendance event."""
        user_id = str(event.user_id)
        # Skip system user '1' if necessary (custom logic from logs/service.py)
        if user_id == '1':
            return

        timestamp = event.timestamp
        
        # Server-side dedup: ZKTeco devices often fire 2 events for a single finger press,
        # or replay events 15-20 seconds later if the network lags.
        # Skip if same user on same machine within 2 seconds.
        dedup_key = (user_id, ip)
        with self._dedup_lock:
            last_time = self._recent_events.get(dedup_key)
            if last_time and (timestamp - last_time).total_seconds() < 2:
                logger.info(f"DEDUP SKIP: {user_id} on {ip} (last: {last_time}, now: {timestamp})")
                return
            self._recent_events[dedup_key] = timestamp
            
            # Cleanup old entries (older than 120 seconds)
            cutoff = timestamp
            expired = [k for k, v in self._recent_events.items() 
                      if (cutoff - v).total_seconds() > 120]
            for k in expired:
                del self._recent_events[k]

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
            is_duplicate = False
            if ip in self.canteen_ips:
                try:
                    from features.meal_tracking.service import check_meal_by_machine_id, log_meal_swipe, try_log_meal_pickup
                    
                    # 1. Look up meal info to get the canonical ID
                    meal_info = check_meal_by_machine_id(user_id, timestamp.date())
                    target_emp_id = str(meal_info.get("emp_no") or user_id) if meal_info else user_id
                    
                    logger.info(f"[MEAL {ip}] user_id={user_id}, target_emp_id='{target_emp_id}', date={timestamp.date()}")
                    
                    # 2. Atomic check-and-insert: try to log pickup, returns True if NEW
                    if meal_info and meal_info.get('is_registered'):
                        was_new = try_log_meal_pickup(meal_info, ip)
                        is_duplicate = not was_new
                    else:
                        is_duplicate = False  # Not registered = show as error, not duplicate
                    
                    logger.info(f"[MEAL {ip}] is_duplicate={is_duplicate}")
                    
                    if meal_info:
                        logger.info(f"MEAL FOUND for {target_emp_id}: {meal_info.get('meal_name_vi', '?')} (Duplicate: {is_duplicate})")
                    else:
                        logger.info(f"NO MEAL registered for {target_emp_id} on {timestamp.date()}")
                        
                    # 3. Log swipe to Local MealTrackingHistory (always, for auditing)
                    log_meal_swipe(target_emp_id, ip, timestamp, meal_info)

                except Exception as e:
                    logger.error(f"Error querying/logging meal info: {e}")

            # 4. Broadcast to WebSockets
            logger.info(f"[EVENT {ip}] Broadcasting type={'meal_event' if ip in self.canteen_ips else 'new_log'} for {user_id} (duplicate={is_duplicate})")
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
                    "meal_info": meal_info,
                    "is_duplicate": is_duplicate
                }
            }
            self._broadcast_async(payload)

            # 4. Meal Ticket Webhook (Target API)
            meal_url = self.meal_configs.get(ip)
            if meal_url:
                def send_meal_hook(url, data):
                    try:
                        logger.info(f"Sending meal ticket hook to {url} for {data['employee_id']}")
                        resp = self._session.post(url, json=data, timeout=5)
                        if resp.status_code >= 400:
                            logger.error(f"Meal hook error {resp.status_code}: {resp.text}")
                    except Exception as ex:
                        logger.error(f"Failed to send meal hook to {url}: {ex}")
                
                # Fetch extra info
                dept = emp.department if emp else "-"
                hook_payload = {
                    "employee_id": user_id,
                    "emp_name": emp_name,
                    "department": dept,
                    "timestamp": timestamp.isoformat(),
                    "machine_ip": ip
                }
                
                # Run in thread pool to avoid thread explosion
                self.executor.submit(send_meal_hook, meal_url, hook_payload)


        except Exception as e:
            logger.error(f"Error processing live event: {e}")
            db.rollback()
        finally:
            db.close()

    def set_loop(self, loop):
        self._loop = loop

    def _broadcast_async(self, payload):
        if self._loop and self._loop.is_running():
            ws_count = len(manager.active_connections)
            logger.info(
                f"[BROADCAST] Sending to {ws_count} WebSocket client(s): "
                f"type={payload.get('type')} emp={payload['data']['employee_id']}"
            )
            asyncio.run_coroutine_threadsafe(manager.broadcast(payload), self._loop)
        else:
            logger.warning(
                f"[BROADCAST] FAILED — loop_set={self._loop is not None}, "
                f"loop_running={self._loop.is_running() if self._loop else 'N/A'}"
            )

    def get_status(self):
        """Returns the current connection status of all monitored machines."""
        return self._status

# Global instance
live_monitor = LiveMonitorManager()
