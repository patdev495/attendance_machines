from datetime import time
from ..database import SessionLocal, ShiftRule

def get_shift_rules(department, shift, rules_pool=None):
    """
    Return shift rules dict based on department + shift type.
    If rules_pool is provided (cached list of ShiftRule objects), it avoids DB queries.
    """
    # Normalize shift code ('D' or 'N')
    lookup_shift = 'D' if shift == 'D' else 'N'
    
    if rules_pool is not None:
        # Use provided cache
        shift_rules = [r for r in rules_pool if r.shift_code == lookup_shift]
    else:
        # Legacy: query DB
        db = SessionLocal()
        try:
            rules = db.query(ShiftRule).all()
            shift_rules = [r for r in rules if r.shift_code == lookup_shift]
        finally:
            db.close()
    
    matching_rule = None
    
    # 1. Search for specific department rule
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
         # Critical fallback if DB is empty
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
