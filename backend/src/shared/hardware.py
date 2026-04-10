from config import config
import logging

logger = logging.getLogger(__name__)

def get_machine_list(file_path=config.MACHINES_FILE):
    """
    Reads the machines list from a local file (machines.txt).
    """
    try:
        with open(file_path, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Could not read machines.txt: {e}")
        return []
