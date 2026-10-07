import sys
import os

# Ensure the core module is accessible
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.card_db as card_db

if __name__ == "__main__":
    force = "--force" in sys.argv
    print("Updating Riftbound Card Database...")
    card_db.update_db(force=force, verbose=True)
    print("Update complete.")
