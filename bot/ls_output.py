import os
path = r"C:\Users\Jorda\Documents\GantryOracle_Handoff\output"
if os.path.exists(path):
    print(f"Contents of {path}:")
    for f in os.listdir(path):
        print(f" - {f}")
else:
    print(f"Path not found: {path}")
