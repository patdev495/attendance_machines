"""
Demo Live Simulator — replaces LiveMonitorManager in DEMO_MODE.

Periodically broadcasts fake attendance events via WebSocket to simulate
real-time monitoring without any ZKTeco hardware connections.
"""
import threading
import time
import random
import logging
import asyncio
from datetime import datetime

from database import SessionLocal, EmployeeLocalRegistry
from shared.socket_manager import manager

logger = logging.getLogger(__name__)


class DemoLiveSimulator:
    """Simulates live attendance events for demo purposes."""
    
    def __init__(self):
        self.is_running = False
        self._loop = None
        self._thread = None
        self._employees = []
        self._status = {}
        
        from shared.hardware import get_live_machine_list, get_canteen_machine_list
        configs = get_live_machine_list()
        self._machine_ips = [c["ip"] for c in configs if not c["is_canteen"]]
        canteen_ips = get_canteen_machine_list()
        self._canteen_ip = canteen_ips[0] if canteen_ips else (self._machine_ips[0] if self._machine_ips else "127.0.0.1")
    
    def set_loop(self, loop):
        self._loop = loop
    
    def start(self):
        if self.is_running:
            return
        self.is_running = True
        
        # Load employee list from DB
        db = SessionLocal()
        try:
            self._employees = [
                {"id": e.employee_id, "name": e.emp_name, "dept": e.department}
                for e in db.query(EmployeeLocalRegistry).limit(200).all()
            ]
        finally:
            db.close()
        
        if not self._employees:
            logger.warning("[DEMO] No employees found — simulator will not emit events")
            return
        
        # Set status for all demo machines
        for ip in self._machine_ips + [self._canteen_ip]:
            self._status[ip] = "connected"
        
        logger.info(f"[DEMO] Starting simulator with {len(self._employees)} employees")
        self._thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        self.is_running = False
        logger.info("[DEMO] Simulator stopped")
    
    def _simulation_loop(self):
        """Emit a random attendance event every 10-25 seconds."""
        while self.is_running:
            # Wait random interval
            wait_time = random.randint(10, 25)
            for _ in range(wait_time):
                if not self.is_running:
                    return
                time.sleep(1)
            
            if not self._employees or not self._loop:
                continue
            
            # Pick a random employee
            emp = random.choice(self._employees)
            
            # 20% chance of canteen event, 80% normal attendance
            is_canteen = random.random() < 0.20
            machine_ip = self._canteen_ip if is_canteen else random.choice(self._machine_ips)
            
            now = datetime.now()
            
            if is_canteen:
                # Meal event
                meal_codes = ["RICE", "NOODLE", "BREAD"]
                meal_names = {"RICE": "Cơm", "NOODLE": "Phở", "BREAD": "Bánh mì"}
                meal_code = random.choice(meal_codes)
                is_registered = random.random() < 0.85  # 85% registered
                
                payload = {
                    "type": "meal_event",
                    "data": {
                        "employee_id": emp["id"],
                        "emp_name": emp["name"] or f"ID: {emp['id']}",
                        "department": emp["dept"] or "-",
                        "attendance_time": now.isoformat(),
                        "machine_ip": machine_ip,
                        "is_live": True,
                        "is_canteen": True,
                        "is_duplicate": False,
                        "meal_info": {
                            "emp_no": emp["id"],
                            "emp_name": emp["name"],
                            "department": emp["dept"],
                            "meal_code": meal_code,
                            "meal_name_vi": meal_names[meal_code],
                            "is_registered": is_registered,
                        } if is_registered else None,
                    }
                }
            else:
                # Normal attendance event
                payload = {
                    "type": "new_log",
                    "data": {
                        "employee_id": emp["id"],
                        "emp_name": emp["name"] or f"ID: {emp['id']}",
                        "department": emp["dept"] or "-",
                        "attendance_time": now.isoformat(),
                        "machine_ip": machine_ip,
                        "is_live": True,
                        "is_canteen": False,
                        "meal_info": None,
                        "is_duplicate": False,
                    }
                }
            
            # Broadcast via WebSocket
            self._broadcast(payload)
    
    def _broadcast(self, payload):
        if self._loop and self._loop.is_running():
            ws_count = len(manager.active_connections)
            if ws_count > 0:
                logger.info(
                    f"[DEMO] Broadcasting to {ws_count} client(s): "
                    f"type={payload['type']} emp={payload['data']['employee_id']}"
                )
            asyncio.run_coroutine_threadsafe(manager.broadcast(payload), self._loop)
    
    def get_status(self):
        """Returns simulated connection status for all demo machines."""
        return self._status


# Global instance
demo_simulator = DemoLiveSimulator()
