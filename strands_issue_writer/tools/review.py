"""Rule review. Deliberately not model-based: these are the checks a rule can
make, so a rule should make them — cheaply, deterministically, every time."""
from __future__ import annotations

import re

from strands import tool

from ..models import Issue

VERSION = re.compile(r"\b\d+\.\d+(?:\.\d+)?\b")
H2 = re.compile(r"^h2\. ", re.M)
VAGUE_EN = ("works correctly", "works as expected", "is fast", "is user friendly",
            "should work", "properly", "as needed")
VAGUE_TR = ("düzgün çalışır", "doğru çalışır", "hızlı olur", "kullanıcı dostu",
            "gerektiği gibi", "sorunsuz")


@tool
def review_issue(issue: dict, raw_input: str = "") -> dict:
    """Check a drafted issue against the writing rules.

    Args:
        issue: the dict returned by draft_issue.
        raw_input: the original text, used to detect invented facts.

    Returns:
        {"ok": bool, "violations": [...], "warnings": [...]} — violations block
        publishing, warnings are worth mentioning to the user.
    """
    violations: list[str] = []
    warnings: list[str] = []

    payload = {k: v for k, v in issue.items() if not k.startswith("_")}
    try:
        parsed = Issue.model_validate(payload)
    except Exception as e:
        return {"ok": False, "violations": [f"schema: {e}"], "warnings": []}

    if len(H2.findall(parsed.description)) < 3:
        violations.append("description has fewer than three sections")

    if parsed.issue_type == "Bug":
        if not any(k in parsed.description for k in ("Steps to Reproduce", "Yeniden Üretme")):
            violations.append("a bug without reproduction steps cannot be verified")
        if not any(k in parsed.description for k in ("Environment", "Ortam")):
            violations.append("a bug without environment detail closes as cannot-reproduce")

    # invented facts: version numbers in the output that were never in the input
    if raw_input:
        invented = set(VERSION.findall(str(payload))) - set(VERSION.findall(raw_input))
        if invented:
            violations.append(
                f"version numbers not present in the input: {', '.join(sorted(invented))}")

    for ac in parsed.acceptance_criteria:
        blob = f"{ac.given} {ac.when} {ac.then}".lower()
        if any(v in blob for v in VAGUE_EN + VAGUE_TR):
            warnings.append(f"{ac.id} is not observable enough to test")

    if parsed.issue_type == "Story" and not parsed.acceptance_criteria:
        violations.append("a story without acceptance criteria has no definition of done")

    thin = len(raw_input) < 220
    if thin and not (parsed.assumptions or parsed.clarifying_questions):
        warnings.append(
            "the input was thin but nothing was assumed or asked — check for invented detail")

    if parsed.dor_check.ready and parsed.clarifying_questions:
        warnings.append("marked ready while open questions remain")

    return {"ok": not violations, "violations": violations, "warnings": warnings,
            "checked": ["schema", "sections", "reproduction", "invented facts",
                        "criteria observability", "gap honesty"]}
