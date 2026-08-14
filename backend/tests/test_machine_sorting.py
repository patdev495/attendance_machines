import sys
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from shared.hardware import ip_sort_key, get_machine_list, get_all_machine_configs, get_live_machine_list
from features.machines.service import get_devices_capacity_info


def test_ip_sort_key_orders_ips_numerically():
    unsorted_ips = [
        "192.168.209.200",
        "192.168.209.20",
        "192.168.209.19",
        "192.168.209.21",
        "192.168.209.2",
    ]
    sorted_ips = sorted(unsorted_ips, key=ip_sort_key)
    assert sorted_ips == [
        "192.168.209.2",
        "192.168.209.19",
        "192.168.209.20",
        "192.168.209.21",
        "192.168.209.200",
    ]


def test_ip_sort_key_handles_dicts_and_non_ips():
    items = [
        {"ip": "192.168.209.100", "name": "Device C"},
        {"ip": "192.168.209.2", "name": "Device A"},
        {"ip": "192.168.209.20", "name": "Device B"},
        {"ip": "invalid-ip-string", "name": "Device Invalid"},
    ]
    sorted_items = sorted(items, key=ip_sort_key)
    assert [x["ip"] for x in sorted_items] == [
        "192.168.209.2",
        "192.168.209.20",
        "192.168.209.100",
        "invalid-ip-string",
    ]


def test_get_machine_list_returns_sorted_order(tmp_path):
    test_file = tmp_path / "machines.txt"
    test_file.write_text(
        "192.168.209.245 # nolive\n"
        "192.168.209.20\n"
        "192.168.209.19\n"
        "192.168.209.241 # canteen\n"
        "192.168.209.21\n"
    )

    ips = get_machine_list(file_path=test_file)
    assert ips == [
        "192.168.209.19",
        "192.168.209.20",
        "192.168.209.21",
        "192.168.209.241",
        "192.168.209.245",
    ]

    all_configs = get_all_machine_configs(file_path=test_file)
    assert [c["ip"] for c in all_configs] == [
        "192.168.209.19",
        "192.168.209.20",
        "192.168.209.21",
        "192.168.209.241",
        "192.168.209.245",
    ]

    live_configs = get_live_machine_list(file_path=test_file)
    assert [c["ip"] for c in live_configs] == [
        "192.168.209.19",
        "192.168.209.20",
        "192.168.209.21",
        "192.168.209.241",
    ]


def test_get_devices_capacity_info_returns_sorted_order():
    mock_configs = [
        {"ip": "192.168.209.245", "is_live": True},
        {"ip": "192.168.209.19", "is_live": True},
        {"ip": "192.168.209.20", "is_live": True},
    ]

    def mock_check(ip: str):
        # Deliberately mock responses with different simulated status
        return {
            "ip": ip,
            "status": "Online",
            "users": 10,
            "users_cap": 1000,
            "fingers": 10,
            "fingers_cap": 1000,
            "records": 50,
            "records_cap": 50000,
            "admins": 1,
            "admins_cap": 10,
        }

    with patch("features.machines.service.get_all_machine_configs", return_value=mock_configs), \
         patch("features.machines.service._check_one_machine_capacity", side_effect=mock_check):
        results = get_devices_capacity_info()

    assert [r["ip"] for r in results] == [
        "192.168.209.19",
        "192.168.209.20",
        "192.168.209.245",
    ]
