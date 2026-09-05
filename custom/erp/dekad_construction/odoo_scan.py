import os
import re

# Patterns to hunt for
PATTERNS = {
    "Legacy Decorator (@api.one)": r"@api\.one",
    "Legacy Decorator (@api.multi)": r"@api\.multi",
    "Single-Record create": r"def create\(self, vals\):",
    "Old-style onchange": r"@api\.onchange",
    "Legacy _columns/_defaults": r"(_columns|_defaults)\s*=",
    "Direct SQL with ID": r"self\._cr\.execute\(.*where id\s*=",
    "Hardcoded XML ID": r"self\.env\.ref\(",
}

def scan_module(path):
    print(f"--- Scanning Odoo Module: {os.path.abspath(path)} ---")
    found_count = 0

    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        for label, pattern in PATTERNS.items():
                            if re.search(pattern, line):
                                print(f"[{label}] -> {file}:{line_num}")
                                print(f"    Line: {line.strip()}")
                                found_count += 1
    
    print(f"\nScan complete. Found {found_count} potential migration points.")

if __name__ == "__main__":
    # Scan the current directory
    scan_module(".")
