"""Build-time download of pinned official data files; no repository code execution."""

import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

root = Path(__file__).parent
manifest = json.loads((root / "manifest.json").read_text())
for name, expected in manifest["files"].items():
    url = f"https://huggingface.co/{manifest['model']}/resolve/{manifest['revision']}/{name}"
    with urlopen(url, timeout=90) as response:
        data = response.read(expected["size"] + 1)
    if len(data) != expected["size"]:
        raise ValueError("MODEL_SIZE_MISMATCH")
    if "sha256" in expected:
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected["sha256"]:
            raise ValueError("MODEL_DIGEST_MISMATCH")
    else:
        blob = f"blob {len(data)}\0".encode() + data
        if hashlib.sha1(blob).hexdigest() != expected["git_blob_sha1"]:
            raise ValueError("TOKENIZER_DIGEST_MISMATCH")
    target = root / "model" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    print(
        json.dumps({"file": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    )
