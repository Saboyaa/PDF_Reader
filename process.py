import json
import time
import os

def mock_processing():
    with open("files_to_process.json", "r", encoding="utf-8") as f:
        files = json.load(f)

    results = []
    for idx, fpath in enumerate(files, start=1):
        info = {
            "index": idx,
            "file": os.path.basename(fpath),
            "size": os.path.getsize(fpath) if os.path.exists(fpath) else 0,
            "status": "ok"
        }
        results.append(info)
        with open("result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        time.sleep(0.1)  # simula tempo de processamento

if __name__ == "__main__":
    mock_processing()
