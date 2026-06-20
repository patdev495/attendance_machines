from datetime import date, datetime
from typing import Union, Optional

def parse_date_robust(date_val: Optional[Union[str, date]]) -> Optional[date]:
    """
    Parse a date from a string or date object supporting multiple formats:
    - YYYY-MM-DD (ISO)
    - DD/MM/YYYY (Vietnamese, UK)
    - MM/DD/YYYY (US)
    - YYYY/MM/DD
    - DD-MM-YYYY
    - MM-DD-YYYY
    - ISO datetime strings containing 'T'
    """
    if date_val is None:
        return None
    if isinstance(date_val, date):
        return date_val
        
    date_val_str = str(date_val).strip()
    if not date_val_str or date_val_str.lower() in ('null', 'none', 'undefined', ''):
        return None
        
    formats = [
        "%Y-%m-%d",  # 2026-06-20
        "%d/%m/%Y",  # 20/06/2026
        "%m/%d/%Y",  # 06/20/2026
        "%Y/%m/%d",  # 2026/06/20
        "%d-%m-%Y",  # 20-06-2026
        "%m-%d-%Y",  # 06-20-2026
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_val_str, fmt).date()
        except ValueError:
            continue
            
    # Try handling ISO datetime formats (e.g. 2026-06-20T13:14:06)
    if 'T' in date_val_str:
        try:
            return datetime.fromisoformat(date_val_str).date()
        except ValueError:
            pass
            
    # Fallback to date.fromisoformat
    try:
        return date.fromisoformat(date_val_str)
    except ValueError:
        pass
        
    raise ValueError(f"Invalid date format: '{date_val_str}'. Expected YYYY-MM-DD or DD/MM/YYYY.")
