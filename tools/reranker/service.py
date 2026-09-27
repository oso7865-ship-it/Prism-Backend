"""Local CPU scoring endpoint. No access/body logging, tracing, or runtime downloads."""

import json
import math
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

ROOT = Path(__file__).parent
ort.disable_telemetry_events()
MANIFEST = json.loads((ROOT / "manifest.json").read_text())
OPTIONS = ort.SessionOptions()
OPTIONS.intra_op_num_threads = 2
OPTIONS.inter_op_num_threads = 1
OPTIONS.log_severity_level = 4
SESSION = ort.InferenceSession(
    str(ROOT / "model/onnx/model.onnx"), OPTIONS, providers=["CPUExecutionProvider"]
)
TOKENIZER = Tokenizer.from_file(str(ROOT / "model/tokenizer.json"))
TOKENIZER.enable_truncation(max_length=512)
TOKENIZER.enable_padding(pad_id=0, pad_token="[PAD]")
LOCK = threading.BoundedSemaphore(1)


def score(data):
    if set(data) != {"query", "documents"}:
        raise ValueError("INVALID_INPUT")
    query, documents = data["query"], data["documents"]
    if (
        not isinstance(query, str)
        or len(query) > 2000
        or not isinstance(documents, list)
        or not 1 <= len(documents) <= 24
        or any(not isinstance(d, str) or len(d.encode()) > 6000 for d in documents)
    ):
        raise ValueError("INPUT_LIMIT")
    query = TOKENIZER.decode(TOKENIZER.encode(query, add_special_tokens=False).ids[:96])
    scores, truncated = [], 0
    for start in range(0, len(documents), 4):
        encoded = TOKENIZER.encode_batch([(query, doc) for doc in documents[start : start + 4]])
        truncated += sum(bool(item.overflowing) for item in encoded)
        inputs = {
            "input_ids": np.asarray([e.ids for e in encoded], dtype=np.int64),
            "attention_mask": np.asarray([e.attention_mask for e in encoded], dtype=np.int64),
            "token_type_ids": np.asarray([e.type_ids for e in encoded], dtype=np.int64),
        }
        scores.extend(float(v) for v in SESSION.run(None, inputs)[0].reshape(-1))
    if any(not math.isfinite(v) for v in scores):
        raise ValueError("INVALID_SCORES")
    return {
        "scores": scores,
        "model": MANIFEST["model"],
        "revision": MANIFEST["revision"],
        "truncated_documents": truncated,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def setup(self):
        super().setup()
        self.connection.settimeout(3)

    def reply(self, status, data):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.reply(200 if self.path == "/health" else 404, {"ready": self.path == "/health"})

    def do_POST(self):
        if self.path != "/rerank":
            self.reply(404, {"error": "NOT_FOUND"})
            return
        if not LOCK.acquire(blocking=False):
            self.reply(503, {"error": "BUSY"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 196608:
                self.reply(413, {"error": "INPUT_LIMIT"})
                return
            data = json.loads(self.rfile.read(size))
            self.reply(200, score(data))
        except Exception:
            # Never echo inputs, parser errors, or inference diagnostics.
            try:
                self.reply(400, {"error": "RERANK_FAILED"})
            except OSError:
                pass
        finally:
            LOCK.release()


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8091), Handler).serve_forever()
