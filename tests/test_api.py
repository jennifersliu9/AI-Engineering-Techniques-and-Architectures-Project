from fastapi.testclient import TestClient

from harborline.api import app

client = TestClient(app)


def test_home_serves_chat_ui():
    res = client.get("/")
    assert res.status_code == 200
    assert "Harborline People Desk" in res.text
    assert "demo-remote" in res.text
    assert "demo-pto" in res.text


def test_health_includes_mcp():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["app"] == "ok"
    assert "mcp" in body
    assert body["mcp"]["available"] is True
    assert "search_policy_documents" in body["mcp"]["discovered_tools"]


def test_demos_list():
    res = client.get("/demos")
    assert res.status_code == 200
    ids = [d["id"] for d in res.json()["demos"]]
    assert ids == ["remote-emp-1008", "pto-emp-1014"]


def test_chat_remote_demo():
    res = client.post(
        "/chat",
        json={
            "query": "Am I eligible for fully remote work living in Tacoma?",
            "employee_id": "EMP-1008",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert "Alex Kim" in body["answer"]
    assert body["citations"]
    assert body["snippets"]
    tools = [step["tool"] for step in body["trace"]]
    assert "lookup_employee_profile" in tools
    assert "search_policy_documents" in tools


def test_chat_pto_demo():
    res = client.post(
        "/chat",
        json={"query": "Can I take PTO next week?", "employee_id": "EMP-1014"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "Devon Walsh" in body["answer"]
    assert body["trace"]
    assert body["citations"] or body["snippets"]
