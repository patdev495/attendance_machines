from config import config
import logging

logger = logging.getLogger(__name__)

def get_machine_list(file_path=config.MACHINES_FILE):
    """
    Reads all machine IPs, stripping comments.
    """
    try:
        with open(file_path, "r") as f:
            # Strip comments (anything after #) and then trim whitespace
            return [line.split('#')[0].strip() for line in f if line.split('#')[0].strip()]
    except Exception as e:
        logger.error(f"Could not read machines.txt: {e}")
        return []

def get_live_machine_list(file_path=config.MACHINES_FILE):
    """
    Returns a list of machine configurations that are NOT marked with # nolive.
    Each item: {"ip": "...", "meal_url": "..." or None, "is_canteen": bool}
    """
    try:
        live_configs = []
        with open(file_path, "r") as f:
            for line in f:
                content = line.strip()
                if not content or content.startswith('#'):
                    continue
                
                # If # nolive is in the line, skip it for live monitoring
                if '# nolive' in content.lower():
                    continue
                
                # Extract IP (part before any #)
                ip = content.split('#')[0].strip()
                if not ip:
                    continue
                
                meal_url = None
                # Extract tag-based configs (e.g. # meal:http://...)
                if '# meal:' in content.lower():
                    parts = content.split('# meal:')
                    if len(parts) > 1:
                        meal_url = parts[1].strip().split(' ')[0] # take first word after tag

                # Check for canteen tag
                is_canteen = '# canteen' in content.lower()

                live_configs.append({
                    "ip": ip,
                    "meal_url": meal_url,
                    "is_canteen": is_canteen
                })
        return live_configs
    except Exception as e:
        logger.error(f"Error filtering live machines: {e}")
        return []

def get_canteen_machine_list(file_path=config.MACHINES_FILE):
    """
    Returns list of IPs marked with # canteen tag.
    """
    return [cfg['ip'] for cfg in get_live_machine_list(file_path) if cfg['is_canteen']]
