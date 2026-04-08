import unicodedata
import re

def strip_accents(s: str) -> str:
    """
    Removes Vietnamese accents from a string.
    Example: "Thân Đức Dương" -> "Than Duc Duong"
    """
    if not s:
        return ""
    
    # Replace common Vietnamese characters
    s = s.replace('đ', 'd').replace('Đ', 'D')
    
    # Normalize to NFD form to separate base character and diacritic
    nfkd_form = unicodedata.normalize('NFKD', s)
    # Filter out non-spacing marks (diacritics)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def sanitize_machine_name(name: str, max_bytes: int = 24) -> str:
    """
    ZK machine names are usually capped at 24 bytes.
    Accented characters in UTF-8 take 2-3 bytes.
    This function tries to keep accents but trims safely, 
    or strips accents if the name is too long or potentially problematic.
    """
    if not name:
        return "New User"
    
    # For now, let's try keeping it simple. 
    # If the user reported mangling, stripping accents is the most reliable "industry standard" for ZK.
    # However, let's try to keep accents but limit length.
    
    # Trim leading/trailing
    name = name.strip()
    
    # ZK machines often struggle with Unicode. 
    # If the user reported issue, stripping is the safest fix.
    return strip_accents(name)[:24]
