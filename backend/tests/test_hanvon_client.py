import json
import struct
import sys
from datetime import date
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from features.hanvon.client import HanvonClient, make_derived_key, xor_from_zero


class FakeSocket:
    def __init__(self, response_body):
        self.sent = b""
        self.recv_buffer = struct.pack("!I", len(response_body)) + response_body

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


def make_fake_client_response(response):
    key = make_derived_key("123")
    body = xor_from_zero(json.dumps(response).encode("utf-8"), key)
    fake_socket = FakeSocket(body)
    client = HanvonClient("192.168.209.61")
    client._sock = fake_socket
    return client, fake_socket


def sent_payload(fake_socket):
    key = make_derived_key("123")
    sent_len = struct.unpack("!I", fake_socket.sent[:4])[0]
    return json.loads(xor_from_zero(fake_socket.sent[4:4 + sent_len], key).decode("utf-8"))


def test_derived_key_matches_verified_protocol_doc():
    assert make_derived_key("123") == bytes([0x31, 0x33, 0x35, 0x04, 0x08, 0x10, 0x20, 0x40])


def test_xor_resets_from_zero_for_each_transaction():
    key = make_derived_key("123")
    payload = b'{"RETURN":"GetRequest"}'

    assert xor_from_zero(payload, key) == xor_from_zero(payload, key)
    assert xor_from_zero(xor_from_zero(payload, key), key) == payload


def test_client_sends_client_get_record_and_parses_records():
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
    client, fake_socket = make_fake_client_response(fake_response)

    records = client.get_records_by_day(date(2026, 6, 4))

    payload = sent_payload(fake_socket)
    assert payload["PARAM"]["command"] == "ClientGetRecord"
    assert payload["PARAM"]["start_time"] == "2026-06-04 00:00:00"
    assert payload["PARAM"]["end_time"] == "2026-06-04 23:59:59"
    assert records[0].employee_id == "232604090"
    assert records[0].attendance_time.isoformat() == "2026-06-04T15:43:05"


def test_client_sends_get_employee_id_and_parses_face_ids():
    client, fake_socket = make_fake_client_response({
        "COMMAND": "Return",
        "PARAM": {
            "result": "success",
            "ids": ["1001", " 1002 ", ""],
            "fids": ["1002"],
        },
    })

    ids, face_ids = client.get_employee_ids()

    payload = sent_payload(fake_socket)
    assert payload["PARAM"]["command"] == "GetEmployeeID"
    assert payload["PARAM"]["userType"] == "0"
    assert ids == ["1001", "1002"]
    assert face_ids == {"1002"}


def test_client_sends_delete_employee():
    client, fake_socket = make_fake_client_response({
        "COMMAND": "Return",
        "PARAM": {"result": "success"},
    })

    client.delete_employee("1001")

    payload = sent_payload(fake_socket)
    assert payload["PARAM"]["command"] == "DeleteEmployee"
    assert payload["PARAM"]["id"] == "1001"


def test_client_sends_delete_manager():
    client, fake_socket = make_fake_client_response({
        "COMMAND": "Return",
        "PARAM": {"result": "success"},
    })

    client.delete_manager("admin1")

    payload = sent_payload(fake_socket)
    assert payload["PARAM"]["command"] == "DeleteManager"
    assert payload["PARAM"]["id"] == "admin1"


def test_client_sends_set_employee_shell():
    """Without biometric data, face_data/finger_data must NOT be sent (device rejects them)."""
    client, fake_socket = make_fake_client_response({
        "COMMAND": "Return",
        "PARAM": {"result": "success", "reason": ""},
    })

    client.set_employee("1001", "Nguyen Van A")

    payload = sent_payload(fake_socket)
    assert payload["PARAM"]["command"] == "SetEmployee"
    assert payload["PARAM"]["id"] == "1001"
    assert payload["PARAM"]["job_num"] == "1001"
    assert payload["PARAM"]["name"] == "Nguyen Van A"
    assert payload["PARAM"]["userType"] == "1"
    assert payload["PARAM"]["recogPermission"] == "face"
    assert payload["PARAM"]["capturejpg"] == ""
    # face_data and finger_data must be absent when no biometric data is provided
    assert "face_data" not in payload["PARAM"]
    assert "finger_data" not in payload["PARAM"]


def test_client_sends_set_employee_with_face_data():
    """With biometric data, face_data and finger_data must be included in the payload."""
    client, fake_socket = make_fake_client_response({
        "COMMAND": "Return",
        "PARAM": {"result": "success", "reason": ""},
    })

    fake_face = [{"type": "face", "data": "base64abc"}]
    client.set_employee("1001", "Nguyen Van A", face_data=fake_face)

    payload = sent_payload(fake_socket)
    assert payload["PARAM"]["face_data"] == fake_face
    assert payload["PARAM"]["finger_data"] == []


def test_client_sends_set_manager():
    client, fake_socket = make_fake_client_response({
        "COMMAND": "Return",
        "PARAM": {"result": "success", "reason": ""},
    })

    client.set_manager("admin_user", "photo_base64_data", password="password123", authority=0)

    payload = sent_payload(fake_socket)
    assert payload["PARAM"]["command"] == "SetManager"
    assert payload["PARAM"]["id"] == "admin_user"
    assert payload["PARAM"]["capturejpg"] == "photo_base64_data"
    assert payload["PARAM"]["password"] == "password123"
    assert payload["PARAM"]["authority"] == 0


def test_client_sends_get_manager_ids():
    client, fake_socket = make_fake_client_response({
        "COMMAND": "Return",
        "PARAM": {
            "result": "success",
            "ids": ["admin1", "admin2", ""],
        },
    })

    ids = client.get_manager_ids()

    payload = sent_payload(fake_socket)
    assert payload["PARAM"]["command"] == "GetManagerID"
    assert ids == ["admin1", "admin2"]


def test_client_sends_get_manager():
    client, fake_socket = make_fake_client_response({
        "COMMAND": "Return",
        "PARAM": {
            "result": "success",
            "id": "admin1",
            "authority": 2,
            "password": "my_password",
        },
    })

    param = client.get_manager("admin1")

    payload = sent_payload(fake_socket)
    assert payload["PARAM"]["command"] == "GetManager"
    assert payload["PARAM"]["id"] == "admin1"
    assert param["id"] == "admin1"
    assert param["authority"] == 2

