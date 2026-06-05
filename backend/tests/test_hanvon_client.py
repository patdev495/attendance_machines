import json
import struct
import sys
from datetime import date
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from features.hanvon.client import HanvonClient, make_derived_key, xor_from_zero


def test_derived_key_matches_verified_protocol_doc():
    assert make_derived_key("123") == bytes([0x31, 0x33, 0x35, 0x04, 0x08, 0x10, 0x20, 0x40])


def test_xor_resets_from_zero_for_each_transaction():
    key = make_derived_key("123")
    payload = b'{"RETURN":"GetRequest"}'

    assert xor_from_zero(payload, key) == xor_from_zero(payload, key)
    assert xor_from_zero(xor_from_zero(payload, key), key) == payload


def test_client_sends_client_get_record_and_parses_records():
    key = make_derived_key("123")
    fake_response = {
        "COMMAND": "Return",
        "PARAM": {
            "result": "success",
            "count": "1",
            "record": [
                {
                    "id": "232604090",
                    "job_num": "232604090",
                    "time": "2026-06-04 15:43:05",
                    "type": "HW-C302A",
                    "userType": "0",
                    "recogType": "0",
                }
            ],
        },
    }
    body = xor_from_zero(json.dumps(fake_response).encode("utf-8"), key)

    class FakeSocket:
        def __init__(self):
            self.sent = b""
            self.recv_buffer = struct.pack("!I", len(body)) + body

        def settimeout(self, timeout):
            pass

        def connect(self, address):
            pass

        def sendall(self, data):
            self.sent += data

        def recv(self, n):
            chunk = self.recv_buffer[:n]
            self.recv_buffer = self.recv_buffer[n:]
            return chunk

        def close(self):
            pass

    fake_socket = FakeSocket()
    client = HanvonClient("192.168.209.61")
    client._sock = fake_socket

    records = client.get_records_by_day(date(2026, 6, 4))

    sent_len = struct.unpack("!I", fake_socket.sent[:4])[0]
    sent_payload = json.loads(xor_from_zero(fake_socket.sent[4:4 + sent_len], key).decode("utf-8"))
    assert sent_payload["PARAM"]["command"] == "ClientGetRecord"
    assert sent_payload["PARAM"]["start_time"] == "2026-06-04 00:00:00"
    assert sent_payload["PARAM"]["end_time"] == "2026-06-04 23:59:59"
    assert records[0].employee_id == "232604090"
    assert records[0].attendance_time.isoformat() == "2026-06-04T15:43:05"
