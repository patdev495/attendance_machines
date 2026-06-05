import json
import socket
import struct
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable


STATIC_KEY = [0, 1, 2, 4, 8, 16, 32, 64]
DEFAULT_PORT = 9922
DEFAULT_SECRET_KEY = "123"


class HanvonProtocolError(RuntimeError):
    pass


def make_derived_key(secret_key: str = DEFAULT_SECRET_KEY) -> bytes:
    secret_bytes = secret_key.encode("utf-8")
    return bytes(
        ((secret_bytes[i] if i < len(secret_bytes) else 0) + STATIC_KEY[i]) & 0xFF
        for i in range(8)
    )


def xor_from_zero(data: bytes, key: bytes) -> bytes:
    return bytes(byte ^ key[i % len(key)] for i, byte in enumerate(data))


def iter_dates(start_date: date, end_date: date) -> Iterable[date]:
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


@dataclass(frozen=True)
class HanvonRecord:
    employee_id: str
    attendance_time: datetime
    machine_ip: str
    raw: dict[str, Any]


class HanvonClient:
    def __init__(
        self,
        ip: str,
        port: int = DEFAULT_PORT,
        secret_key: str = DEFAULT_SECRET_KEY,
        timeout: int = 15,
    ):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.key = make_derived_key(secret_key)
        self._sock: socket.socket | None = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def connect(self):
        if self._sock:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.ip, self.port))
        self._sock = sock

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def get_device_info(self) -> dict[str, Any]:
        response = self._send_command("GetDeviceInfo")
        param = response.get("PARAM", {})
        if param.get("result") != "success":
            raise HanvonProtocolError(f"GetDeviceInfo failed: {param.get('reason') or response}")
        return param.get("deviceInfo", {})

    def get_employee_ids(self) -> tuple[list[str], set[str]]:
        response = self._send_command("GetEmployeeID", userType="0")
        param = response.get("PARAM", {})
        if param.get("result") != "success":
            raise HanvonProtocolError(f"GetEmployeeID failed: {param.get('reason') or response}")
        ids = [str(item).strip() for item in param.get("ids", []) if str(item).strip()]
        face_ids = {str(item).strip() for item in param.get("fids", []) if str(item).strip()}
        return ids, face_ids

    def delete_employee(self, employee_id: str) -> None:
        response = self._send_command("DeleteEmployee", id=str(employee_id))
        param = response.get("PARAM", {})
        if param.get("result") != "success":
            raise HanvonProtocolError(f"DeleteEmployee failed: {param.get('reason') or response}")

    def set_employee(self, employee_id: str, name: str = "") -> None:
        employee_id = str(employee_id).strip()
        if not employee_id:
            raise ValueError("employee_id is required")

        response = self._send_command(
            "SetEmployee",
            id=employee_id,
            name=str(name or "").strip(),
            sex=2,
            nation="Vietnamese",
            address="",
            userType="1",
            job_num=employee_id,
            icCard="",
            recogPermission="face",
            capturejpg="",
            face_data=[],
            finger_data=[],
        )
        param = response.get("PARAM", {})
        if param.get("result") != "success":
            raise HanvonProtocolError(f"SetEmployee failed: {param.get('reason') or response}")

    def get_records(self, start_dt: datetime, end_dt: datetime) -> list[HanvonRecord]:
        response = self._send_command(
            "ClientGetRecord",
            start_time=start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            end_time=end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        )
        param = response.get("PARAM", {})
        if param.get("result") != "success":
            raise HanvonProtocolError(f"ClientGetRecord failed: {param.get('reason') or response}")

        records = param.get("record", [])
        if isinstance(records, dict):
            records = [records]
        if not records:
            return []

        parsed: list[HanvonRecord] = []
        for record in records:
            employee_id = str(record.get("job_num") or record.get("id") or "").strip()
            raw_time = str(record.get("time") or "").strip()
            if not employee_id or not raw_time:
                continue
            try:
                attendance_time = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S")
            except ValueError as exc:
                raise HanvonProtocolError(f"Invalid Hanvon record time '{raw_time}'") from exc
            parsed.append(
                HanvonRecord(
                    employee_id=employee_id,
                    attendance_time=attendance_time,
                    machine_ip=self.ip,
                    raw=record,
                )
            )
        return parsed

    def get_records_by_day(self, target_date: date) -> list[HanvonRecord]:
        start_dt = datetime.combine(target_date, time.min).replace(microsecond=0)
        end_dt = datetime.combine(target_date, time.max).replace(microsecond=0)
        return self.get_records(start_dt, end_dt)

    def _send_command(self, command: str, **params: Any) -> dict[str, Any]:
        if not self._sock:
            self.connect()
        assert self._sock is not None

        payload = {
            "RETURN": "GetRequest",
            "PARAM": {
                "result": "success",
                "reason": "",
                "command": command,
                **params,
            },
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        encrypted = xor_from_zero(body, self.key)
        self._sock.sendall(struct.pack("!I", len(encrypted)) + encrypted)

        header = self._recv_exact(4)
        body_len = struct.unpack("!I", header)[0]
        if body_len <= 0:
            raise HanvonProtocolError(f"Invalid response body length: {body_len}")

        response_body = self._recv_exact(body_len)
        decrypted = xor_from_zero(response_body, self.key)
        try:
            return json.loads(decrypted.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HanvonProtocolError("Invalid JSON response from Hanvon device") from exc

    def _recv_exact(self, n: int) -> bytes:
        assert self._sock is not None
        chunks = bytearray()
        while len(chunks) < n:
            chunk = self._sock.recv(n - len(chunks))
            if not chunk:
                raise ConnectionError("Connection closed by Hanvon device")
            chunks.extend(chunk)
        return bytes(chunks)
