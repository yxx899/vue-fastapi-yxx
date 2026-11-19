"""端到端 API 冒烟测试（租户 + 平台）。用法: .venv/python scripts/test_all_api.py"""
from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BASE = "http://127.0.0.1:8000/api"
FAILURES: list[str] = []


def ok(name: str) -> None:
    print(f"  OK  {name}")


def fail(name: str, detail: str) -> None:
    print(f"  FAIL {name}: {detail}")
    FAILURES.append(f"{name}: {detail}")


def tenant_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Auth-Type": "tenant"}


def platform_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Auth-Type": "platform"}


def parse_sse_answer(text: str) -> str | None:
    answer = None
    for block in text.split("\n\n"):
        if not block.startswith("data:"):
            continue
        import json

        try:
            payload = json.loads(block[5:].strip())
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "answer":
            answer = payload.get("content")
    return answer


def main() -> int:
    print("=== Health ===")
    with httpx.Client(timeout=120.0) as c:
        r = c.get(f"{BASE}/health")
        if r.status_code != 200:
            fail("health", r.text)
            return 1
        ok("health")

        r = c.get(f"{BASE}/health/qwen")
        if r.status_code != 200:
            fail("health/qwen", r.text)
        else:
            ok("health/qwen")

        print("=== Tenant auth ===")
        r = c.post(f"{BASE}/auth/login", json={"username": "admin", "password": "admin123"})
        if r.status_code != 200:
            fail("tenant login", f"{r.status_code} {r.text} (可运行 init_demo_tenant.py --reset-password)")
            return 1
        token = r.json()["access_token"]
        th = tenant_headers(token)
        ok("tenant login")

        r = c.get(f"{BASE}/auth/me", headers=th)
        if r.status_code != 200:
            fail("auth/me", r.text)
        else:
            me = r.json()
            ok(f"auth/me role={me.get('role')}")

        print("=== Knowledge bases ===")
        r = c.get(f"{BASE}/knowledge-bases", headers=th)
        kb_id = None
        if r.status_code != 200:
            fail("list kbs", r.text)
        else:
            items = r.json().get("items") or []
            ok(f"list kbs count={len(items)}")
            kb_id = items[0]["id"] if items else None

        suffix = uuid.uuid4().hex[:6]
        r = c.post(
            f"{BASE}/knowledge-bases",
            headers=th,
            json={"name": f"测试库_{suffix}", "description": "auto test", "is_public_in_tenant": True},
        )
        test_kb_id = None
        if r.status_code not in (200, 201):
            fail("create kb", f"{r.status_code} {r.text}")
        else:
            test_kb_id = r.json().get("id")
            ok(f"create kb id={test_kb_id}")

        use_kb = test_kb_id or kb_id

        print("=== Users / departments ===")
        r = c.get(f"{BASE}/users", headers=th, params={"page": 1, "page_size": 100})
        if r.status_code != 200:
            fail("list users", f"{r.status_code} {r.text}")
        else:
            ok(f"list users total={r.json().get('total')}")

        r = c.get(f"{BASE}/departments/tree", headers=th)
        if r.status_code != 200:
            fail("departments tree", r.text)
        else:
            ok("departments tree")

        print("=== Chat stream ===")
        session_id = None
        if use_kb:
            with c.stream(
                "POST",
                f"{BASE}/chat/stream",
                headers=th,
                json={"question": "Tools Workflow Agent 是什么？", "kb_ids": [use_kb]},
            ) as stream:
                body = stream.read().decode("utf-8", errors="replace")
                if stream.status_code != 200:
                    fail("chat stream", f"{stream.status_code} {body[:300]}")
                else:
                    ans = parse_sse_answer(body)
                    if not ans:
                        fail("chat stream", "no answer event in SSE")
                    else:
                        ok(f"chat stream answer_len={len(ans)}")

        r = c.get(f"{BASE}/chat/sessions", headers=th)
        if r.status_code != 200:
            fail("list sessions", r.text)
        else:
            sessions = r.json().get("items") or r.json()
            if isinstance(sessions, list) and sessions:
                session_id = sessions[0].get("id")
            ok("list sessions")

        print("=== Audit / dashboard ===")
        r = c.get(f"{BASE}/audit/dashboard", headers=th)
        if r.status_code != 200:
            fail("audit dashboard", r.text)
        else:
            ok("audit dashboard")

        r = c.get(f"{BASE}/audit/logs", headers=th, params={"page": 1, "page_size": 20})
        if r.status_code != 200:
            fail("audit logs", r.text)
        else:
            ok(f"audit logs total={r.json().get('total')}")

        r = c.post(f"{BASE}/audit/logs/actions/batch-delete", headers=th, params={"today_only": True})
        if r.status_code != 200:
            fail("audit batch-delete", f"{r.status_code} {r.text}")
        else:
            ok(f"audit batch-delete deleted={r.json().get('deleted')}")

        r = c.get(f"{BASE}/audit/documents/failed", headers=th)
        if r.status_code != 200:
            fail("audit failed docs", r.text)
        else:
            ok("audit failed docs")

        r = c.get(f"{BASE}/documents/failed/list", headers=th)
        if r.status_code != 200:
            fail("documents failed list", r.text)
        else:
            ok("documents failed list")

        print("=== Documents ===")
        doc_id = None
        if use_kb:
            r = c.get(f"{BASE}/documents", headers=th, params={"kb_id": use_kb})
            if r.status_code != 200:
                fail("list documents", r.text)
            else:
                ok("list documents")

            md_content = b"# Test Doc\n\nTools Workflow Agent demo paragraph for RAG.\n"
            r = c.post(
                f"{BASE}/documents/upload",
                headers=th,
                params={"kb_id": use_kb},
                files={"file": ("test_auto.md", md_content, "text/markdown")},
            )
            if r.status_code not in (200, 201):
                fail("upload document", f"{r.status_code} {r.text[:300]}")
            else:
                doc_id = r.json().get("id")
                ok(f"upload document id={doc_id}")

            if doc_id:
                for _ in range(30):
                    r = c.get(f"{BASE}/documents", headers=th, params={"kb_id": use_kb, "page_size": 100})
                    st = next((x["status"] for x in r.json().get("items", []) if x["id"] == doc_id), None)
                    if st in ("success", "failed"):
                        ok(f"document parse status={st}")
                        break
                    time.sleep(0.5)
                else:
                    fail("document parse", "timeout waiting success/failed")

        print("=== KB toggle / cleanup ===")
        if test_kb_id:
            r = c.post(f"{BASE}/knowledge-bases/{test_kb_id}/toggle", headers=th, params={"active": False})
            if r.status_code != 200:
                fail("deactivate kb", f"{r.status_code} {r.text}")
            else:
                ok("deactivate kb")

            r = c.get(f"{BASE}/knowledge-bases", headers=th)
            if r.status_code == 200:
                ids = [x["id"] for x in r.json().get("items") or []]
                if test_kb_id in ids:
                    ok("inactive kb visible to admin")
                else:
                    fail("inactive kb visible to admin", "disabled kb not in admin list")

            if doc_id:
                r = c.delete(f"{BASE}/documents/{doc_id}", headers=th)
                if r.status_code != 200:
                    fail("delete document", f"{r.status_code} {r.text}")
                else:
                    ok("delete document")

            r = c.delete(f"{BASE}/knowledge-bases/{test_kb_id}", headers=th)
            if r.status_code != 200:
                fail("delete test kb", f"{r.status_code} {r.text}")
            else:
                ok("delete test kb")

        if session_id:
            r = c.delete(f"{BASE}/chat/sessions/{session_id}", headers=th)
            if r.status_code != 200:
                fail("delete session", r.text)
            else:
                ok("delete session")

        print("=== Employee login ===")
        r = c.post(f"{BASE}/auth/login", json={"username": "employee", "password": "employee123"})
        if r.status_code != 200:
            fail("employee login", f"{r.status_code} {r.text}")
        else:
            eh = tenant_headers(r.json()["access_token"])
            r2 = c.get(f"{BASE}/knowledge-bases", headers=eh)
            if r2.status_code != 200:
                fail("employee list kbs", r2.text)
            else:
                ok("employee list kbs")

        print("=== Platform ===")
        r = c.post(f"{BASE}/platform/auth/login", json={"username": "platform", "password": "platform123"})
        if r.status_code != 200:
            fail("platform login", f"{r.status_code} {r.text}")
        else:
            ph = platform_headers(r.json()["access_token"])
            ok("platform login")

            r = c.get(f"{BASE}/platform/tenants", headers=ph)
            if r.status_code != 200:
                fail("platform tenants", r.text)
            else:
                ok(f"platform tenants count={len(r.json().get('items') or [])}")

            r = c.get(f"{BASE}/platform/stats/overview", headers=ph)
            if r.status_code != 200:
                fail("platform stats overview", r.text)
            else:
                ok("platform stats overview")

    print("\n=== Summary ===")
    if FAILURES:
        for f in FAILURES:
            print("!", f)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
