# RESEARCH

## 1. Goal
Implement automatic time update (sync) for time attendance machines (ZKTeco) using the `pyzk` SDK.

## 2. Findings
The `pyzk` SDK allows setting the time on a connected ZKTeco device using the `conn.set_time(timestamp)` method, which takes a standard Python `datetime` object.

Example usage:
```python
from zk import ZK
from datetime import datetime

zk = ZK('192.168.1.201', port=4370, timeout=5)
conn = None
try:
    conn = zk.connect()
    conn.disable_device()
    conn.set_time(datetime.now())
    conn.enable_device()
except Exception as e:
    print(f"Error: {e}")
finally:
    if conn:
        conn.disconnect()
```

## 3. Integration Plan
- Add `sync_machine_time(ip)` and `bulk_sync_machine_time()` methods in `d:\Workspace\Time_Attendance_Machine\backend\src\features\machines\service.py`.
- Add an endpoint in `d:\Workspace\Time_Attendance_Machine\backend\src\features\machines\router.py` to trigger the time sync for a specific machine or all machines.

## RESEARCH COMPLETE
