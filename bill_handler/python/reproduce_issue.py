import os
import sys

# Add the project root to the python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(project_root)

from bill_storage import BillStorage, DEFAULT_FILE

def test_file_creation():
    # Ensure file does not exist (we expect it to be in root now)
    # But wait, the user said it DOES exist in root.
    # So we should just check if it loads correctly.
    
    print(f"Checking for file at: {DEFAULT_FILE}")
    if not os.path.exists(DEFAULT_FILE):
        print(f"WARNING: {DEFAULT_FILE} does not exist yet.")
    else:
        print(f"Found existing file at {DEFAULT_FILE}")

    print("Initializing BillStorage...")
    storage = BillStorage()
    
    # Check if we can read from it
    data = storage.get_storage()
    print(f"Loaded storage: {data}")


if __name__ == "__main__":
    test_file_creation()
