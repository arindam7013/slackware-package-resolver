import os
import json
import re
from pathlib import Path
import sys

def parse_info_file(file_path):
    """
    Parses a .info file to extract package name, version, and requires.
    """
    info = {}
    keys_to_find = ["PRGNAM", "VERSION", "REQUIRES"]

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            match = re.match(r'^\s*([A-Z_]+)\s*=\s*"(.*)"\s*$', line)
            if match:
                key, value = match.groups()
                if key in keys_to_find:
                    info[key] = value
    return info

def main(sbo_path_str):
    """
    Main function to walk the SBo repo and build the dependency database.
    """
    sbo_path = Path(sbo_path_str)
    if not sbo_path.is_dir():
        print(f" Error: The provided SlackBuilds path does not exist: {sbo_path}")
        sys.exit(1)

    print(f"🔍 Starting scan of SlackBuilds repository at: {sbo_path}")
    package_db = {}

    for root, dirs, files in os.walk(sbo_path):
        for file in files:
            if file.endswith(".info"):
                info_file_path = Path(root) / file
                
                try:
                    parsed_info = parse_info_file(info_file_path)
                    
                    if "PRGNAM" in parsed_info:
                        package_name = parsed_info["PRGNAM"]
                        
                        # Get the list of dependencies
                        raw_dependencies = parsed_info.get("REQUIRES", "").split()
                        
                        # --- THIS IS THE FIX ---
                        # Filter out any items that start with '%', like %README%
                        cleaned_dependencies = [dep for dep in raw_dependencies if not dep.startswith('%')]
                        
                        package_db[package_name] = {
                            "version": parsed_info.get("VERSION", "N/A"),
                            "requires": cleaned_dependencies
                        }
                except Exception as e:
                    print(f"  Could not parse {info_file_path}: {e}")

    print(f" Scan complete! Found {len(package_db)} packages.")

    output_file = Path("database.json")
    print(f"  Writing database to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(package_db, f, indent=2, sort_keys=True)

    print(" Database build complete!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build_database.py /path/to/your/slackbuilds/clone")
        sys.exit(1)
    
    sbo_repo_path = sys.argv[1]
    main(sbo_repo_path)