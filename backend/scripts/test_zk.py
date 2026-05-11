from zk import ZK
from collections import defaultdict

zk = ZK('192.168.209.30', port=4370, timeout=20)

try:
    conn = zk.connect()
    attendances = conn.get_attendance()

    print(f"Total records found: {len(attendances)}\n")
    
    print("--- RAW ATTENDANCE OBJECTS (First 10) ---")
    # In ra 10 bản ghi đầu tiên dưới dạng raw nhất có thể
    for i, att in enumerate(attendances[:10]):
        # Sử dụng vars() để xem toàn bộ các thuộc tính bên trong object
        print(f"Record {i+1}: {vars(att)}")

    print("\n--- ALL RAW DATA (user_id, timestamp, status, punch, uid) ---")
    for att in attendances:
        print(att)

finally:
    if 'conn' in locals() and conn:
        conn.disconnect()