"""Bearer-protected approval and evidence control plane for the sandbox."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import IO, Any


_PLAN_HASH = re.compile(r"^[a-f0-9]{64}$")
_REQUEST_ID = re.compile(r"^[a-zA-Z0-9._:-]{1,128}$")
_AUDIT_LOCK = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


def build_handler(
    *,
    token: str,
    data_dir: Path,
    evidence_path: Path,
    log_stream: IO[str] | None = None,
) -> type[BaseHTTPRequestHandler]:
    """Bind runtime configuration without placing credentials on the handler class."""
    if not token:
        raise ValueError("AGENT_DELIVERY_API_TOKEN is required")
    data_dir.mkdir(parents=True, exist_ok=True)
    stream = log_stream or sys.stdout

    class Handler(BaseHTTPRequestHandler):
        server_version = "AgentDeliveryControlPlane/0.1"

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _request_id(self) -> str:
            supplied = self.headers.get("X-Request-Id", "")
            return supplied if _REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex

        def _authorized(self) -> bool:
            header = self.headers.get("Authorization", "")
            prefix = "Bearer "
            candidate = header[len(prefix):] if header.startswith(prefix) else ""
            return hmac.compare_digest(candidate, token)

        def _write_log(
            self,
            *,
            request_id: str,
            status: int,
            started: float,
        ) -> None:
            event = {
                "timestamp": _utc_now(),
                "request_id": request_id,
                "method": self.command,
                "path": self.path.split("?", 1)[0],
                "status": status,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            }
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            stream.flush()

        def _send(
            self,
            status: int,
            payload: dict[str, Any],
            *,
            request_id: str,
            started: float,
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Request-Id", request_id)
            self.end_headers()
            self.wfile.write(body)
            self._write_log(request_id=request_id, status=status, started=started)

        def _deny(self, request_id: str, started: float) -> None:
            self._send(
                401,
                {"error": "unauthorized", "request_id": request_id},
                request_id=request_id,
                started=started,
            )

        def do_GET(self) -> None:
            started = time.perf_counter()
            request_id = self._request_id()
            path = self.path.split("?", 1)[0]
            if path == "/health":
                self._send(
                    200, {"status": "ok"}, request_id=request_id, started=started
                )
                return
            if path == "/ready":
                self._send(
                    200,
                    {
                        "status": "ready",
                        "token_fingerprint": _token_fingerprint(token),
                        "data_dir_writable": os.access(data_dir, os.W_OK),
                    },
                    request_id=request_id,
                    started=started,
                )
                return
            if not self._authorized():
                self._deny(request_id, started)
                return
            if path == "/v1/evidence":
                payload = json.loads(evidence_path.read_text(encoding="utf-8"))
                self._send(200, payload, request_id=request_id, started=started)
                return
            self._send(
                404,
                {"error": "not_found", "request_id": request_id},
                request_id=request_id,
                started=started,
            )

        def do_POST(self) -> None:
            started = time.perf_counter()
            request_id = self._request_id()
            if not self._authorized():
                self._deny(request_id, started)
                return
            if self.path.split("?", 1)[0] != "/v1/approvals":
                self._send(
                    404,
                    {"error": "not_found", "request_id": request_id},
                    request_id=request_id,
                    started=started,
                )
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 65536:
                    raise ValueError("body size is invalid")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                plan_sha = str(payload.get("plan_sha256") or "")
                approver = str(payload.get("approver") or "").strip()
                decision = str(payload.get("decision") or "")
                if not _PLAN_HASH.fullmatch(plan_sha):
                    raise ValueError("plan_sha256 must be 64 lowercase hex characters")
                if not approver or decision not in {"approve", "reject"}:
                    raise ValueError("approver and decision=approve|reject are required")
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                self._send(
                    400,
                    {"error": "invalid_request", "detail": str(exc), "request_id": request_id},
                    request_id=request_id,
                    started=started,
                )
                return

            event = {
                "timestamp": _utc_now(),
                "request_id": request_id,
                "plan_sha256": plan_sha,
                "approver": approver,
                "decision": decision,
                "allow_external_write": bool(payload.get("allow_external_write", False)),
            }
            audit_path = data_dir / "approvals.jsonl"
            with _AUDIT_LOCK, audit_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            self._send(
                201,
                {"status": "recorded", "approval": event},
                request_id=request_id,
                started=started,
            )

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("AGENT_DELIVERY_DATA_DIR", "artifacts/control-plane")),
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("evidence/experiment_20260814.json"),
    )
    args = parser.parse_args()
    token = os.environ.get("AGENT_DELIVERY_API_TOKEN", "")
    handler = build_handler(
        token=token, data_dir=args.data_dir, evidence_path=args.evidence
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(json.dumps({"event": "server_started", "host": args.host, "port": args.port}))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
