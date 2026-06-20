from config import config
import logging
from typing import Any

logger = logging.getLogger(__name__)

def _parse_machine_line(content: str) -> dict[str, Any] | None:
    raw = content.strip()
    if not raw or raw.startswith('#'):
        return None

    ip = raw.split('#')[0].strip()
    if not ip:
        return None

    tags_text = ""
    if '#' in raw:
        tags_text = raw[raw.index('#'):].lower()

    protocol = "hanvon"

    meal_url = None
    if '# meal:' in tags_text:
        parts = raw.split('# meal:')
        if len(parts) > 1:
            meal_url = parts[1].strip().split(' ')[0]

    return {
        "ip": ip,
        "protocol": protocol,
        "meal_url": meal_url,
        "is_live": '# nolive' not in tags_text,
        "is_canteen": '# canteen' in tags_text,
    }

def get_machine_list(file_path=config.MACHINES_FILE) -> list[str]:
    """
    Reads all machine IPs, stripping comments.
    """
    try:
        with open(file_path, "r") as f:
            return [
                cfg["ip"]
                for line in f
                if (cfg := _parse_machine_line(line)) is not None
            ]
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
                cfg = _parse_machine_line(line)
                if not cfg:
                    continue
                if not cfg["is_live"]:
                    continue

                live_configs.append({
                    "ip": cfg["ip"],
                    "meal_url": cfg["meal_url"],
                    "is_canteen": cfg["is_canteen"],
                    "protocol": cfg["protocol"],
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
                cfg = _parse_machine_line(line)
                if not cfg:
                    continue

                configs.append({
                    "ip": cfg["ip"],
                    "is_live": cfg["is_live"],
                    "is_canteen": cfg["is_canteen"],
                    "protocol": cfg["protocol"],
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
                existing_cfg = _parse_machine_line(line) or {}
                tags = []
                if not is_live:
                    tags.append("nolive")
                if is_canteen:
                    tags.append("canteen")
                if existing_cfg.get("meal_url"):
                    tags.append(f"meal:{existing_cfg['meal_url']}")
                
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

def delete_machine_config(ip, file_path=config.MACHINES_FILE):
    """
    Deletes the configuration for a specific machine IP from machines.txt.
    """
    try:
        lines = []
        with open(file_path, "r") as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
                continue
                
            if stripped.startswith('#'):
                new_lines.append(line)
                continue
                
            line_ip = stripped.split('#')[0].strip()
            if line_ip == ip:
                continue
            new_lines.append(line)
            
        with open(file_path, "w") as f:
            f.writelines(new_lines)
        return True, "Success"
    except Exception as e:
        logger.error(f"Error deleting machine config: {e}")
        return False, str(e)

