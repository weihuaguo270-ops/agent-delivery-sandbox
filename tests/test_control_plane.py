from __future__ import annotations

import io
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from sandbox_service.control_plane import build_handler


def _request(url, *, token=None, data=None, request_id=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if request_id:
        headers["X-Request-Id"] = request_id
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, headers=headers, data=body)
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_control_plane_auth_audit_and_structured_logs(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"decision":"hold"}', encoding="utf-8")
    logs = io.StringIO()
    handler = build_handler(
        token="test-token",
        data_dir=tmp_path / "data",
        evidence_path=evidence,
        log_stream=logs,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        status, health = _request(f"{base}/health")
        assert status == 200
        assert health == {"status": "ok"}

        try:
            _request(f"{base}/v1/evidence")
            raise AssertionError("missing token should fail")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401

        status, payload = _request(
            f"{base}/v1/approvals",
            token="test-token",
            request_id="approval-test-1",
            data={
                "plan_sha256": "a" * 64,
                "approver": "reviewer",
                "decision": "approve",
                "allow_external_write": True,
            },
        )
        assert status == 201
        assert payload["approval"]["request_id"] == "approval-test-1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    audit = (tmp_path / "data" / "approvals.jsonl").read_text(encoding="utf-8")
    assert "test-token" not in audit
    assert '"decision": "approve"' in audit
    events = [json.loads(line) for line in logs.getvalue().splitlines()]
    assert {event["status"] for event in events} == {200, 201, 401}
    assert all("latency_ms" in event and "request_id" in event for event in events)


def test_control_plane_requires_token(tmp_path):
    try:
        build_handler(
            token="",
            data_dir=tmp_path,
            evidence_path=tmp_path / "missing.json",
        )
        raise AssertionError("empty token should fail")
    except ValueError as exc:
        assert "TOKEN" in str(exc)
