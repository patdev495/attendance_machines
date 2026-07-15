import sys
import base64
from pathlib import Path
import xml.etree.ElementTree as ET

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database import EmployeeLocalRegistry

def test_generate_card_print_btxml_success(client, db_session, monkeypatch):
    # Mock machine calls
    mock_jpg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x0c\x01\x01\x11\x00?\x00\x37\x00\xff\xd9'
    mock_base64 = base64.b64encode(mock_jpg).decode('utf-8')
    monkeypatch.setattr(
        "features.employees.router.get_biometric_coverage",
        lambda employee_id: [{"ip": "192.168.209.63", "status": "Online", "registered": True, "has_face": True}]
    )
    monkeypatch.setattr(
        "features.employees.router.get_user_photo_from_machine",
        lambda ip, employee_id: (mock_base64, "Success")
    )

    # Seed test employees
    db_session.add_all([
        EmployeeLocalRegistry(
            employee_id="1001", 
            emp_name="Nguyen Van A", 
            department="Xuong 1", 
            group_name="To 1",
            source_status="excel_synced"
        ),
        EmployeeLocalRegistry(
            employee_id="1002", 
            emp_name="Tran Thi B", 
            department="Xuong 2", 
            group_name="To 2",
            source_status="excel_synced"
        ),
    ])
    db_session.commit()

    # Call endpoint
    response = client.post("/api/employees/card-print-btxml", json={
        "employee_ids": ["1001", "1002"]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "btxml" in data
    
    # Parse generated BTXML
    btxml = data["btxml"]
    root = ET.fromstring(btxml)
    
    # Verify XML structure
    print_el = root.find(".//Print")
    assert print_el is not None
    
    # Extract NamedSubStrings
    substrings = {}
    for ns in print_el.findall("NamedSubString"):
        name = ns.get("Name")
        val_el = ns.find("Value")
        if name and val_el is not None:
            substrings[name] = val_el.text or ""
            
    # Verify Employee 1
    assert substrings.get("id1") == "1001"
    assert substrings.get("name1") == "Nguyen Van A"
    assert substrings.get("dept1") == "Xuong 1"
    assert substrings.get("group1") == "To 1"
    assert substrings.get("image1") == "http://testserver/assets/avatars/1001.jpg"
    
    # Verify Employee 2
    assert substrings.get("id2") == "1002"
    assert substrings.get("name2") == "Tran Thi B"
    assert substrings.get("dept2") == "Xuong 2"
    assert substrings.get("group2") == "To 2"
    assert substrings.get("image2") == "http://testserver/assets/avatars/1002.jpg"
    
    # Verify Padded Empty Slots (3 to 6)
    for i in range(3, 7):
        assert substrings.get(f"id{i}") == ""
        assert substrings.get(f"name{i}") == ""
        assert substrings.get(f"dept{i}") == ""
        assert substrings.get(f"group{i}") == ""
        assert substrings.get(f"image{i}") == ""


def test_photo_caching_behavior(client, db_session, tmp_path, monkeypatch):
    # Mock machine calls
    mock_jpg = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x0c\x01\x01\x11\x00?\x00\x37\x00\xff\xd9'
    mock_base64 = base64.b64encode(mock_jpg).decode('utf-8')
    monkeypatch.setattr(
        "features.employees.router.get_biometric_coverage",
        lambda employee_id: [{"ip": "192.168.209.63", "status": "Online", "registered": True, "has_face": True}]
    )
    monkeypatch.setattr(
        "features.employees.router.get_user_photo_from_machine",
        lambda ip, employee_id: (mock_base64, "Success")
    )

    # Mock config.STATIC_DIR to use tmp_path for isolation
    from config import config
    original_static_dir = config.STATIC_DIR
    config.STATIC_DIR = tmp_path
    
    try:
        # Seed test employee
        db_session.add(
            EmployeeLocalRegistry(
                employee_id="2001", 
                emp_name="Test Cache", 
                department="QC", 
                group_name="QC 1",
                source_status="excel_synced"
            )
        )
        db_session.commit()
        
        avatar_dir = tmp_path / "assets" / "avatars"
        avatar_file = avatar_dir / "2001.jpg"
        
        # Verify cache file does not exist initially
        assert not avatar_file.exists()
        
        # First call: triggers retrieval (in demo mode writes mock)
        response = client.post("/api/employees/card-print-btxml", json={
            "employee_ids": ["2001"]
        })
        assert response.status_code == 200
        
        # Verify file was written to cache
        assert avatar_file.exists()
        assert avatar_file.read_bytes() == mock_jpg
        
        # Modify cached file content to verify subsequent call hits the cache
        avatar_file.write_bytes(b"custom-cached-image-data")
        
        # Second call: should hit cache and not overwrite the modified file
        response2 = client.post("/api/employees/card-print-btxml", json={
            "employee_ids": ["2001"]
        })
        assert response2.status_code == 200
        assert avatar_file.read_bytes() == b"custom-cached-image-data"
        
    finally:
        config.STATIC_DIR = original_static_dir
