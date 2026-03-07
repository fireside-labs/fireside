import os
import hashlib

def get_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

path = r"C:\Users\Jorda\Documents\GantryOracle_Handoff\output"
print(f"--- Heimdall Forensic Audit ---")
if not os.path.exists(path):
    print(f"ERROR: Audit path not found: {path}")
else:
    files = [f for f in os.listdir(path) if f.endswith(".pdf")]
    if not files:
        print("No PDF artifacts found for auditing.")
    for filename in files:
        f_path = os.path.join(path, filename)
        size = os.path.getsize(f_path)
        hash_val = get_sha256(f_path)
        print(f"Artifact: {filename}")
        print(f" - Size: {size} bytes")
        print(f" - SHA-256: {hash_val}")
        print(f" - Integrity: {'PASS' if size > 0 else 'FAIL (0-byte)'}")
        print("-" * 30)
print("Audit Complete.")
