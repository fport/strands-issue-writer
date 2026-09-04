from strands_issue_writer.tools.tracker import push_to_tracker, render_issue

ISSUE = {
    "issue_type": "Bug", "summary": "Cart empties when a guest signs in",
    "description": "h2. Summary\nThe cart empties.\n\nh2. Steps to Reproduce\n# add item\n# sign in",
    "priority": "High", "severity": "Critical", "labels": ["cart"],
    "components": ["Checkout"], "assumptions": ["assumed production web"],
    "clarifying_questions": ["which browser?"],
    "dor_check": {"ready": False, "missing": ["environment"]},
    "_meta": {"valid": True},
}


def test_render_hides_internal_meta():
    out = render_issue(issue=ISSUE)
    assert "_meta" not in out
    assert "Cart empties" in out and "Critical" in out
    assert "assumed production web" in out


def test_push_is_dry_run_without_confirmation():
    """Publishing is an outward action; it must not happen by accident."""
    r = push_to_tracker(issue=ISSUE, project_key="SHOP")
    assert r["dry_run"] is True
    assert r["payload"]["fields"]["project"]["key"] == "SHOP"
    assert r["payload"]["fields"]["issuetype"]["name"] == "Bug"


def test_adf_conversion_shape():
    r = push_to_tracker(issue=ISSUE, project_key="SHOP")
    doc = r["payload"]["fields"]["description"]
    assert doc["type"] == "doc"
    kinds = [b["type"] for b in doc["content"]]
    assert "heading" in kinds and "orderedList" in kinds


def test_spike_maps_to_task():
    r = push_to_tracker(issue={**ISSUE, "issue_type": "Spike", "severity": None},
                        project_key="X")
    assert r["payload"]["fields"]["issuetype"]["name"] == "Task"
