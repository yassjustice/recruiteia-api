"""
RecruteIA — Database Initializer
Run this once to set up the SQLite database.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import engine, Base
import src.api.models  # noqa: F401 — registers all models

def init():
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized at:", engine.url)

if __name__ == "__main__":
    init()