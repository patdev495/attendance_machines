import sys
import os
from datetime import time

# Ensure we can import from backend.src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.src.utils.shift_utils import get_shift_rules

def verify():
    test_cases = [
        ("Xưởng 1", "D", "Xưởng 1 Night"),
        ("Xưởng 1", "N", "Xưởng 1 Day"),
        (None, "D", "Default Night"),
        (None, "N", "Default Day")
    ]
    
    expected = {
        "Xưởng 1 Night": dict(official_start=time(20,0), official_end=time(8,0), end_next_day=True,
                             max_hours=12.0, standard_hours=12.0, deduct_break=False, has_overtime=False),
        "Xưởng 1 Day":   dict(official_start=time(8,0),  official_end=time(20,0), end_next_day=False,
                             max_hours=12.0, standard_hours=12.0, deduct_break=False, has_overtime=False),
        "Default Night": dict(official_start=time(20,0), official_end=time(5,0),  end_next_day=True,
                             max_hours=None,  standard_hours=8.0,  deduct_break=True,  has_overtime=True),
        "Default Day":   dict(official_start=time(8,0),  official_end=time(17,0), end_next_day=False,
                             max_hours=None,  standard_hours=8.0,  deduct_break=True,  has_overtime=True)
    }

    errors = 0
    for dept, shift, label in test_cases:
        res = get_shift_rules(dept, shift)
        exp = expected[label]
        
        print(f"--- Checking {label} ---")
        for k in exp:
            if res[k] != exp[k]:
                print(f"Mismatch in {k}: Expected {exp[k]}, Got {res[k]}")
                errors += 1
            else:
                print(f"Ok: {k} = {res[k]}")
    
    if errors == 0:
        print("Verification PASSED: Parity maintained.")
    else:
        print(f"Verification FAILED: {errors} mismatches found.")

if __name__ == "__main__":
    verify()
