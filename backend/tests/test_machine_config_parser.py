import sys
import threading
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from shared.hardware import _parse_machine_line, get_machine_list, update_machine_tags


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


def test_concurrent_machine_additions_preserve_both_ips(tmp_path):
    """Two simultaneous add requests must not overwrite each other."""
    config_file = tmp_path / "machines.txt"
    config_file.write_text("192.168.209.10 # nolive\n")
    start = threading.Barrier(2)
    results = []

    def add_machine(ip: str):
        start.wait()
        results.append(update_machine_tags(ip, False, False, file_path=config_file))

    threads = [
        threading.Thread(target=add_machine, args=("192.168.209.40",)),
        threading.Thread(target=add_machine, args=("192.168.209.41",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == [(True, "added"), (True, "added")]
    assert get_machine_list(file_path=config_file) == [
        "192.168.209.10",
        "192.168.209.40",
        "192.168.209.41",
    ]
