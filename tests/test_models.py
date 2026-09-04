"""The output contract. These mirror the rules the model was trained on."""
import pytest
from pydantic import ValidationError

from strands_issue_writer.models import Issue

BASE = {
    "issue_type": "Task",
    "summary": "Rotate the payment service credentials",
    "description": "h2. Objective\n" + "x" * 60,
    "priority": "Medium",
    "components": ["Platform"],
    "dor_check": {"ready": True, "missing": []},
}


def test_minimal_issue_validates():
    Issue.model_validate(BASE)


@pytest.mark.parametrize("summary", [
    "Bug: checkout is broken",
    "[Story] Add saved addresses",
    "Task - migrate the logs",
])
def test_type_prefix_rejected(summary):
    with pytest.raises(ValidationError):
        Issue.model_validate({**BASE, "summary": summary})


def test_trailing_period_rejected():
    with pytest.raises(ValidationError):
        Issue.model_validate({**BASE, "summary": "Add the export button."})


def test_severity_only_on_bugs():
    with pytest.raises(ValidationError):
        Issue.model_validate({**BASE, "severity": "Major"})
    Issue.model_validate({**BASE, "issue_type": "Bug", "severity": "Major"})


def test_story_criteria_bounds():
    ac = [{"id": f"AC{i}", "given": "a state", "when": "an action",
           "then": "an outcome"} for i in range(1, 9)]
    with pytest.raises(ValidationError):
        Issue.model_validate({**BASE, "issue_type": "Story",
                              "acceptance_criteria": ac})
    Issue.model_validate({**BASE, "issue_type": "Story",
                          "acceptance_criteria": ac[:4]})


def test_labels_must_be_kebab_case():
    with pytest.raises(ValidationError):
        Issue.model_validate({**BASE, "labels": ["Needs Design"]})
    Issue.model_validate({**BASE, "labels": ["needs-design"]})


def test_story_points_are_fibonacci():
    with pytest.raises(ValidationError):
        Issue.model_validate({**BASE, "story_points": 4})
    Issue.model_validate({**BASE, "story_points": 5})
