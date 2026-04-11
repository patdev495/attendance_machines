import sys
from pathlib import Path
import datetime
from unittest.mock import MagicMock

# Add src to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from features.machines.live_monitor import live_monitor
from shared.hardware import get_live_machine_list
import time

def simulate():
    print("--- SIMULATING LIVE EVENT ---")
    
    # 1. Manually trigger the management loop logic to pick up the new 127.0.0.1 config
    configs = get_live_machine_list()
    for cfg in configs:
        ip = cfg['ip']
        live_monitor.meal_configs[ip] = cfg['meal_url']
        # We don't actually need the thread to be running for _process_event to work
    
    print(f"Configs loaded: {live_monitor.meal_configs}")
    
    # 2. Mock a ZK Event
    mock_event = MagicMock()
    mock_event.user_id = "1904001" # ID that exists in EmployeeLocalRegistry
    mock_event.timestamp = datetime.datetime.now()
    
    # 3. Trigger processing
    print(f"Triggering event for User {mock_event.user_id} on 127.0.0.1...")
    live_monitor._process_event("127.0.0.1", mock_event)
    
    # Wait a bit for the async thread to send the request
    print("Wait 3 seconds for webhook thread to finish...")
    time.sleep(3)
    print("Simulation finished.")

if __name__ == "__main__":
    simulate()
