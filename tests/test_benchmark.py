from harborline.benchmark import contains_all, load_tasks, run_report, tool_recall


def test_eval_tasks_cover_required_families():
    tasks = load_tasks()
    assert 20 <= len(tasks) <= 30
    families = {t["family"] for t in tasks}
    assert {"policy_qa", "multi_doc", "tool", "ambiguous", "oos"} <= families
    assert any(t.get("gold_answer") for t in tasks)
    assert any(t.get("expected_tools") for t in tasks)
    assert any(t.get("expect_clarification") for t in tasks)
    assert any(t.get("write_attempt") for t in tasks)


def test_scoring_helpers():
    assert contains_all("Alex Kim is hub_seattle", ["Alex Kim", "hub"])
    assert not contains_all("nope", ["Alex Kim"])
    assert tool_recall(["lookup_employee_profile", "search_policy_documents"], ["lookup_employee_profile"]) == 1.0
    assert tool_recall(["search_policy_documents"], ["lookup_employee_profile", "check_pto_balance"]) == 0.0


def test_report_smoke_limit():
    report = run_report(limit=3, transport="mcp-inproc")
    assert report["n"] == 3
    assert "groundedness" in report["answer_quality"]
    assert "tool_selection_accuracy" in report["agent_behavior"]
    assert "p50_ms" in report["system"]
    assert "retrieval_recall_by_top_k" in report["ablation"]
    assert set(report["ablation"]["retrieval_recall_by_top_k"]) == {"3", "5", "8"}
