import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from zk import ZK
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_machine(ip):
    print(f"Testing connection to {ip}...")
    zk = ZK(ip, port=4370, timeout=5, force_udp=False)
    conn = None
    try:
        conn = zk.connect()
        print(f"SUCCESS: Connected to {ip}")
        print(f"Firmware: {conn.get_firmware_version()}")
        print(f"Device Name: {conn.get_device_name()}")
    except Exception as e:
        print(f"FAILED: Could not connect to {ip}: {e}")
        print("Retrying with force_udp=True...")
        zk_udp = ZK(ip, port=4370, timeout=5, force_udp=True)
        try:
            conn = zk_udp.connect()
            print(f"SUCCESS: Connected to {ip} (UDP)")
        except Exception as e2:
            print(f"FAILED: Still could not connect to {ip}: {e2}")
    finally:
        if conn:
            conn.disconnect()

if __name__ == "__main__":
    test_machine("192.168.209.60")
    test_machine("192.168.209.54")
