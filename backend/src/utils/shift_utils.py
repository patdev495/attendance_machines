from datetime import time
from ..database import SessionLocal, ShiftRule

def get_shift_rules(department, shift):
    """
    Return shift rules dict based on department + shift type.
    Queries the ShiftRules table for dynamic configuration.
    Mapping (legacy): shift == 'D' is Night, else Day ('N').
    """
    db = SessionLocal()
    try:
        # In current system, 'D' usually refers to Night shift (20:00 start) 
        # and 'N' (or else) refers to Day shift (08:00 start). 
        # We search for a matching dept keyword first.
        
        # 1. Search for specific department rule
        # Normalize shift code ('D' or 'N')
        lookup_shift = 'D' if shift == 'D' else 'N'
        
        rules = db.query(ShiftRule).all()
        
        # Sort rules so that rules WITH dept_keyword are checked FIRST
        # and specific keywords are prioritize if multiple (though rare here)
        matching_rule = None
        
        # Filter for the specific shift code
        shift_rules = [r for r in rules if r.shift_code == lookup_shift]
        
        # Find the'Dept' match
        if department:
            for r in shift_rules:
                if r.dept_keyword and r.dept_keyword in department:
                    matching_rule = r
                    break
        
        # 2. Fallback to default rule (dept_keyword is None)
        if not matching_rule:
            for r in shift_rules:
                if not r.dept_keyword:
                    matching_rule = r
                    break
        
        if not matching_rule:
             # Critical fallback if DB is empty - return original default (same as legacy Rule D)
             return dict(official_start=time(8,0),  official_end=time(17,0), end_next_day=False,
                        max_hours=None,  standard_hours=8.0,  deduct_break=True,  has_overtime=True)

        return {
            "official_start": matching_rule.official_start,
            "official_end": matching_rule.official_end,
            "end_next_day": matching_rule.end_next_day,
            "max_hours": matching_rule.max_hours,
            "standard_hours": matching_rule.standard_hours,
            "deduct_break": matching_rule.deduct_break,
            "has_overtime": matching_rule.has_overtime
        }
    finally:
        db.close()
