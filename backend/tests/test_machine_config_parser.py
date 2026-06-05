import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from shared.hardware import _parse_machine_line


def test_parse_machine_line_defaults_to_hanvon():
    cfg = _parse_machine_line("192.168.209.21")

    assert cfg["ip"] == "192.168.209.21"
    assert cfg["protocol"] == "hanvon"
    assert cfg["is_live"] is True
    assert cfg["is_canteen"] is False


def test_parse_hanvon_machine_line():
    cfg = _parse_machine_line("192.168.209.61 # hanvon # canteen # nolive")

    assert cfg["ip"] == "192.168.209.61"
    assert cfg["protocol"] == "hanvon"
    assert cfg["is_live"] is False
    assert cfg["is_canteen"] is True


def test_parse_protocol_tag_machine_line():
    cfg = _parse_machine_line("192.168.209.61 # protocol:hanvon")

    assert cfg["protocol"] == "hanvon"


def test_parse_legacy_zkteco_tag_is_ignored():
    cfg = _parse_machine_line("192.168.209.21 # zkteco")

    assert cfg["protocol"] == "hanvon"
