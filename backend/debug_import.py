import sys
import traceback
import os

# Ensure local dir is in path
sys.path.insert(0, os.getcwd())

try:
    print("Attempting to import k...")
    import k
    print("Successfully imported k!")
except Exception:
    print("\n--- CAUGHT EXCEPTION ---")
    traceback.print_exc()
    print("------------------------\n")
