"""The review tool is the safety net over a small local model."""
from strands_issue_writer.tools.review import review_issue

STORY = {
    "issue_type": "Story",
    "summary": "Let customers export invoice history as one PDF",
    "description": ("h2. User Story\nAs a customer, I want to export invoices.\n\n"
                    "h2. Context\nAccountants download 30-40 a month.\n\n"
                    "h2. Acceptance Criteria\n*AC1* something observable"),
    "priority": "Medium",
    "components": ["Billing"],
    "acceptance_criteria": [
        {"id": "AC1", "given": "invoices exist", "when": "the user exports",
         "then": "a single PDF downloads containing every invoice in range"},
        {"id": "AC2", "given": "no invoices in range", "when": "the user exports",
         "then": "an empty-state message names the range instead of an empty file"},
        {"id": "AC3", "given": "the export exceeds 50 invoices", "when": "requested",
         "then": "it is produced in the background and delivered by email"},
    ],
    "assumptions": [], "clarifying_questions": [],
    "dor_check": {"ready": True, "missing": []},
}


def test_clean_story_passes():
    v = review_issue(issue=STORY, raw_input="x" * 400)
    assert v["ok"], v["violations"]


def test_bug_without_reproduction_steps_is_rejected():
    bug = {**STORY, "issue_type": "Bug", "severity": "Major",
           "acceptance_criteria": [],
           "description": "h2. Summary\nIt breaks.\n\nh2. Impact\nSome users.\n\nh2. Notes\nn/a"}
    v = review_issue(issue=bug, raw_input="x" * 400)
    assert not v["ok"]
    assert any("reproduction" in x for x in v["violations"])


def test_invented_version_numbers_are_caught():
    """The model must not add a version the input never mentioned."""
    issue = {**STORY, "description": STORY["description"] + "\n\nSeen in 7.2.1"}
    v = review_issue(issue=issue, raw_input="invoices export slow, no version given")
    assert not v["ok"]
    assert any("7.2.1" in x for x in v["violations"])


def test_version_present_in_input_is_allowed():
    issue = {**STORY, "description": STORY["description"] + "\n\nSeen in 7.2.1"}
    v = review_issue(issue=issue, raw_input="broken since 7.2.1, invoices export slow")
    assert v["ok"], v["violations"]


def test_vague_criteria_warn():
    issue = {**STORY, "acceptance_criteria": [
        {"id": "AC1", "given": "a user", "when": "they export", "then": "it works correctly"},
        *STORY["acceptance_criteria"][1:],
    ]}
    v = review_issue(issue=issue, raw_input="x" * 400)
    assert any("observable" in w for w in v["warnings"])


def test_thin_input_without_questions_warns():
    """Short input plus no assumptions means the model filled gaps silently."""
    v = review_issue(issue=STORY, raw_input="export invoices pls")
    assert any("invented" in w for w in v["warnings"])
