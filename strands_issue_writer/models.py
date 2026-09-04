"""Output contract, shared with the training dataset.

Kept byte-compatible with `schema/models.py` in fport/issue-writer so the agent
validates exactly what the model was trained to produce.
"""
from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

IssueType = Literal["Epic", "Story", "Task", "Bug", "Spike", "Sub-task"]
Priority = Literal["Highest", "High", "Medium", "Low", "Lowest"]
Severity = Literal["Critical", "Major", "Minor", "Trivial"]
StoryPoints = Literal[1, 2, 3, 5, 8, 13]

Label = Annotated[str, Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
_TYPE_PREFIX = re.compile(r"^\s*(\[(bug|story|task|epic)\]|(bug|story|task|epic)\s*[:\-])", re.I)


class AcceptanceCriterion(BaseModel):
    id: Annotated[str, Field(pattern=r"^AC[0-9]+$")]
    given: Annotated[str, Field(min_length=3)]
    when: Annotated[str, Field(min_length=3)]
    then: Annotated[str, Field(min_length=3)]


class DorCheck(BaseModel):
    ready: bool
    missing: list[str] = []


class Issue(BaseModel):
    """What the fine-tuned model emits, and what the tracker tools consume."""

    issue_type: IssueType
    summary: Annotated[str, Field(min_length=8, max_length=120)]
    description: Annotated[str, Field(min_length=40)]
    priority: Priority
    severity: Severity | None = None
    labels: Annotated[list[Label], Field(max_length=6)] = []
    components: Annotated[list[str], Field(min_length=1)]
    story_points: StoryPoints | None = None
    acceptance_criteria: Annotated[list[AcceptanceCriterion], Field(max_length=10)] = []
    subtasks: list[str] = []
    parent_hint: str | None = None
    assumptions: list[str] = []
    clarifying_questions: list[str] = []
    dor_check: DorCheck

    @field_validator("summary")
    @classmethod
    def no_type_prefix(cls, v: str) -> str:
        if _TYPE_PREFIX.match(v):
            raise ValueError("summary must not repeat the issue type; the field already carries it")
        if v.endswith("."):
            raise ValueError("summary must not end with a period")
        return v

    @field_validator("severity")
    @classmethod
    def severity_only_for_bugs(cls, v, info):
        if v is not None and info.data.get("issue_type") != "Bug":
            raise ValueError("severity applies to bugs only")
        return v

    @field_validator("acceptance_criteria")
    @classmethod
    def story_criteria_count(cls, v, info):
        if info.data.get("issue_type") == "Story" and not (3 <= len(v) <= 7):
            raise ValueError(f"a Story carries 3-7 criteria, got {len(v)}; split it instead")
        return v
