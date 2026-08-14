import json
import logging
import socket
import struct
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Iterable

logger = logging.getLogger(__name__)


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
        import time as _time
        logger.info(f"[HANVON-CLIENT] Connecting to {self.ip}:{self.port} (timeout={self.timeout}s)")
        t0 = _time.monotonic()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.ip, self.port))
            elapsed = _time.monotonic() - t0
            logger.info(f"[HANVON-CLIENT] TCP connected to {self.ip}:{self.port} in {elapsed:.2f}s")
        except Exception as e:
            elapsed = _time.monotonic() - t0
            logger.error(f"[HANVON-CLIENT] TCP connect FAILED to {self.ip}:{self.port} in {elapsed:.2f}s | {type(e).__name__}: {e}")
            sock.close()
            raise
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

    def get_employee(self, employee_id: str) -> dict[str, Any]:
        response = self._send_command("ClientGetEmployee", job_num=employee_id, userType="0")
        param = response.get("PARAM", {})
        if param.get("result") != "success":
            raise HanvonProtocolError(f"ClientGetEmployee failed: {param.get('reason') or response}")
        return param

    def delete_employee(self, employee_id: str) -> None:
        response = self._send_command("DeleteEmployee", id=employee_id)
        param = response.get("PARAM", {})
        if param.get("result") != "success":
            raise HanvonProtocolError(f"DeleteEmployee failed: {param.get('reason') or response}")

    def delete_manager(self, manager_id: str) -> None:
        response = self._send_command("DeleteManager", id=manager_id)
        param = response.get("PARAM", {})
        if param.get("result") != "success":
            raise HanvonProtocolError(f"DeleteManager failed: {param.get('reason') or response}")

    def set_employee(self, employee_id: str, name: str = "", photo_base64: str = "", face_data: list | None = None) -> None:
        """Create or update a standard employee on the device.

        Protocol note: userType MUST be "1" — any other value is rejected by the
        firmware with 不支持的用户类型. Photo is optional; omitting it creates the
        employee without face-recognition capability.
        """
        employee_id = employee_id.strip()
        if not employee_id:
            raise ValueError("employee_id is required")

        params: dict[str, Any] = {
            "id": employee_id,
            "name": (name or "").strip(),
            "sex": 2,
            "nation": "Vietnamese",
            "address": "",
            "userType": "1",
            "job_num": employee_id,
            "icCard": "",
            "recogPermission": "face",
            "capturejpg": photo_base64 or "",
        }
        # Only include face/finger arrays when non-empty to avoid device rejecting unknown fields
        if face_data:
            params["face_data"] = face_data
            params["finger_data"] = []

        response = self._send_command("SetEmployee", **params)
        param = response.get("PARAM", {})
        if param.get("result") != "success":
            raise HanvonProtocolError(f"SetEmployee failed: {param.get('reason') or response}")

    def set_manager(
        self,
        manager_id: str,
        photo_base64: str,
        password: str = "123456",
        authority: int = 2,
    ) -> None:
        """Create or update a manager (admin) on the device.

        Protocol constraints (verified experimentally):
        - capturejpg MUST be a real JPEG base64 string (≥15KB) — empty or tiny
          images are rejected with 缺少图片 / 照片过大或过小.
        - authority: 0 = Super Admin, 2 = Ordinary Admin (1/3 are normalised to 2).
        - password must be unique across all managers (密码已存在 if duplicate).
        """
        manager_id = manager_id.strip()
        if not manager_id:
            raise ValueError("manager_id is required")
        if not photo_base64 or not photo_base64.strip():
            raise ValueError(
                "A real JPEG photo (base64) is required to create a Hanvon manager. "
                "Empty photos are rejected by the device with 缺少图片."
            )

        response = self._send_command(
            "SetManager",
            id=manager_id,
            capturejpg=photo_base64.strip(),
            password=password or "123456",
            authority=authority,
        )
        param = response.get("PARAM", {})
        if param.get("result") != "success":
            reason = param.get("reason", "")
            # Surface device error messages in English for the frontend
            if "缺少图片" in reason:
                raise HanvonProtocolError("Manager photo is missing or empty (device rejected: 缺少图片).")
            if "照片过大或过小" in reason:
                raise HanvonProtocolError("Manager photo is too small or too large — must be a real JPEG ≥15KB (device rejected: 照片过大或过小).")
            if "密码已存在" in reason:
                raise HanvonProtocolError("Manager password already exists on the device. Choose a different password (device rejected: 密码已存在).")
            raise HanvonProtocolError(f"SetManager failed: {reason or response}")

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

    def get_manager_ids(self) -> list[str]:
        response = self._send_command("GetManagerID")
        param = response.get("PARAM", {})
        if param.get("result") != "success":
            if "fail" in str(param.get("result")):
                return []
            raise HanvonProtocolError(f"GetManagerID failed: {param.get('reason') or response}")
        return [str(item).strip() for item in param.get("ids", []) if str(item).strip()]

    def get_manager(self, manager_id: str) -> dict[str, Any]:
        response = self._send_command("GetManager", id=manager_id)
        param = response.get("PARAM", {})
        if param.get("result") != "success":
            raise HanvonProtocolError(f"GetManager failed: {param.get('reason') or response}")
        return param

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
            preview = decrypted[:300].hex()
            raise HanvonProtocolError(
                f"Invalid JSON response from Hanvon device (command={command}, raw_hex={preview})"
            ) from exc

    def _recv_exact(self, n: int) -> bytes:
        assert self._sock is not None
        chunks = bytearray()
        while len(chunks) < n:
            chunk = self._sock.recv(n - len(chunks))
            if not chunk:
                raise ConnectionError("Connection closed by Hanvon device")
            chunks.extend(chunk)
        return bytes(chunks)
