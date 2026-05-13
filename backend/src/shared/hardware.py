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

def get_all_machine_configs(file_path=config.MACHINES_FILE):
    """
    Returns a list of ALL machine configurations, including nolive ones.
    """
    try:
        configs = []
        with open(file_path, "r") as f:
            for line in f:
                content = line.strip()
                if not content or content.startswith('#'):
                    continue
                
                # Extract IP (part before any #)
                ip = content.split('#')[0].strip()
                if not ip:
                    continue
                
                is_live = '# nolive' not in content.lower()
                is_canteen = '# canteen' in content.lower()
                
                configs.append({
                    "ip": ip,
                    "is_live": is_live,
                    "is_canteen": is_canteen
                })
        return configs
    except Exception as e:
        logger.error(f"Error reading all machine configs: {e}")
        return []

def get_canteen_machine_list(file_path=config.MACHINES_FILE):
    """
    Returns list of IPs marked with # canteen tag.
    """
    return [cfg['ip'] for cfg in get_live_machine_list(file_path) if cfg['is_canteen']]

def update_machine_tags(ip, is_live, is_canteen, file_path=config.MACHINES_FILE):
    """
    Updates the tags for a specific machine IP in machines.txt.
    is_live=False adds # nolive
    is_canteen=True adds # canteen
    """
    try:
        lines = []
        with open(file_path, "r") as f:
            lines = f.readlines()
            
        new_lines = []
        found = False
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                new_lines.append(line)
                continue
                
            line_ip = stripped.split('#')[0].strip()
            if line_ip == ip:
                found = True
                tags = []
                if not is_live:
                    tags.append("nolive")
                if is_canteen:
                    tags.append("canteen")
                
                new_line = f"{ip}"
                if tags:
                    new_line += " # " + " # ".join(tags)
                new_lines.append(new_line + "\n")
            else:
                new_lines.append(line)
                
        if not found:
            tags = []
            if not is_live: tags.append("nolive")
            if is_canteen: tags.append("canteen")
            new_line = f"{ip}"
            if tags: new_line += " # " + " # ".join(tags)
            new_lines.append(new_line + "\n")
            
        with open(file_path, "w") as f:
            f.writelines(new_lines)
        return True, "Success"
    except Exception as e:
        logger.error(f"Error updating machine tags: {e}")
        return False, str(e)
