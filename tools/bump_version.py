#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import argparse
from datetime import datetime


def get_git_hash():
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.STDOUT
            )
            .decode("utf-8")
            .strip()
        )
    except:
        return None


def update_json_file(file_path, new_version):
    if not os.path.exists(file_path):
        return False
    with open(file_path, "r") as f:
        data = json.load(f)
    data["version"] = new_version
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return True


def update_toml_file(file_path, new_version):
    if not os.path.exists(file_path):
        return False
    with open(file_path, "r") as f:
        content = f.read()

    # Replace version = "..." with version = "new_version"
    new_content = re.sub(
        r'version\s*=\s*"[^"]+"', f'version = "{new_version}"', content, count=1
    )

    if new_content == content:
        return False

    with open(file_path, "w") as f:
        f.write(new_content)
    return True


def main():
    parser = argparse.ArgumentParser(description="Bump version in project files")
    parser.add_argument("version", help="The version to set (e.g., 0.5.0)")
    parser.add_argument(
        "--snapshot", action="store_true", help="Add -SNAPSHOT and git hash"
    )
    args = parser.parse_args()

    version = args.version
    if args.snapshot:
        git_hash = get_git_hash()
        suffix = f"-SNAPSHOT"
        if git_hash:
            suffix += f"+{git_hash}"
        version += suffix

    # Files to update
    json_files = ["package.json", "frontend/package.json"]
    toml_files = ["backend/pyproject.toml"]

    updated = []
    for f in json_files:
        if update_json_file(f, version):
            updated.append(f)

    for f in toml_files:
        if update_toml_file(f, version):
            updated.append(f)

    if updated:
        print(f"Successfully bumped version to {version} in: {', '.join(updated)}")
        # Prepare git command for the user
        print(f"\nNext steps:")
        print(f"git add {' '.join(updated)}")
        print(f'git commit -m "📦 config: bump version to {version}"')
    else:
        print("No files were updated.")
        sys.exit(1)


if __name__ == "__main__":
    main()
