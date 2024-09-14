import json
import os
import shutil
import sqlite3
import sys
from typing import Optional

import requests


def download_artifact(owner: str, repo: str, artifact_name: str, output_path: Optional[str]=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    response = requests.get(url)
    response.raise_for_status()
    release = response.json()
    asset = next((asset for asset in release['assets'] if asset['name'] == artifact_name), None)
    if asset is None:
        raise ValueError(f"Artifact '{artifact_name}' not found in the latest release")
    download_url = asset['browser_download_url']
    response = requests.get(download_url)
    response.raise_for_status()
    with open(artifact_name if not output_path else output_path, 'wb') as f:
        f.write(response.content)
    print(f"Successfully downloaded {artifact_name}")

def main() -> int:
    print("Downloading database...")
    download_artifact("e9x", "chrome-versions", "chrome.db")
    print("Cleaning old tree...")
    shutil.rmtree("boards")
    os.makedirs("boards")
    conn = sqlite3.connect("chrome.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT DISTINCT board FROM cros_recovery_image")
    unique = [row["board"] for row in cursor.fetchall()]
    print(f"Found {len(unique)} boards.")
    for board in unique:
        cursor.execute(f"SELECT * FROM cros_recovery_image WHERE board = ?", (board,))
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        cursor.execute(f"SELECT * FROM cros_brand WHERE board = ?", (board,))
        rows = cursor.fetchall()
        brands = [dict(row)["brand"] for row in rows]
        filename = f"{board}.json"
        filepath = os.path.join("boards", filename)
        with open(filepath, 'w') as f:
            json.dump({
                "pageProps": {
                    "board": board,
                    "images": data,
                    "brands": brands,
                },
                "__N_SSP": True
            }, f, indent=2)
        print(f"Created {filepath}")
    return 0

if __name__ == "__main__":
    sys.exit(main())