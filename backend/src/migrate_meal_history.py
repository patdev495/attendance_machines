import logging
import sys
import os

# Add the src directory to path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, MealTrackingHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    logger.info("Creating MealTrackingHistory table in the MIS database...")
    MealTrackingHistory.__table__.create(bind=engine, checkfirst=True)
    logger.info("MealTrackingHistory table successfully created.")

if __name__ == "__main__":
    migrate()
