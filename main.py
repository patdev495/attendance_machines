from zk import ZK
from collections import defaultdict

zk = ZK('192.168.209.30', port=4370, timeout=20)

try:
    conn = zk.connect()
    attendances = conn.get_attendance()

    # Nhóm theo employee_id
    grouped = defaultdict(list)

    for att in attendances:
        grouped[att.user_id].append(att.timestamp)

    # Xử lý từng nhân viên
    for user_id, times in grouped.items():
        times.sort()

        print(f"\nEmployee: {user_id}")

        for t in times:
            print("  -", t)

finally:
    conn.disconnect()