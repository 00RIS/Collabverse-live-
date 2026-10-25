"""
tests/test_readiness.py

WHAT THIS FILE DEMONSTRATES:
The Career Readiness formula (app/services/readiness.py) is pure Python,
so it can be tested completely independently of FastAPI, the database,
or HTTP — exactly what spec Section 34 asks for ("Critical business
logic should be testable independently of the UI").

Run with:  pytest tests/test_readiness.py -v
"""

from app.services.readiness import RequirementInput, calculate_readiness


def test_perfect_match_scores_100():
    requirements = [
        RequirementInput("s1", "Python", required_proficiency=3, importance_weight=1.0),
        RequirementInput("s2", "SQL", required_proficiency=2, importance_weight=1.0),
    ]
    student_skills = {"s1": 3, "s2": 4}  # exceeding SQL's requirement is fine

    result = calculate_readiness(requirements, student_skills)

    assert result.readiness_score == 100.0
    assert len(result.strong) == 2
    assert result.missing == []
    assert result.partial == []


def test_missing_skill_drags_score_down_proportionally_to_its_weight():
    requirements = [
        RequirementInput("s1", "Python", required_proficiency=4, importance_weight=3.0),  # heavy
        RequirementInput("s2", "Excel", required_proficiency=2, importance_weight=1.0),  # light
    ]
    # Student has Excel fully, but has never logged Python at all.
    student_skills = {"s2": 2}

    result = calculate_readiness(requirements, student_skills)

    # weighted_ratio_sum = (3 * 0) + (1 * 1.0) = 1.0 ; total_weight = 4.0
    # readiness = 1.0 / 4.0 * 100 = 25.0
    assert result.readiness_score == 25.0
    assert len(result.missing) == 1
    assert result.missing[0].skill_name == "Python"
    assert len(result.strong) == 1


def test_partial_proficiency_is_capped_at_full_credit_not_bonus():
    requirements = [RequirementInput("s1", "React", required_proficiency=2, importance_weight=1.0)]
    # Student is at EXPERT (4) but requirement only asks for level 2 —
    # should cap at 100% credit for this skill, not "200%".
    student_skills = {"s1": 4}

    result = calculate_readiness(requirements, student_skills)

    assert result.readiness_score == 100.0


def test_priority_gaps_sorted_by_importance_descending():
    requirements = [
        RequirementInput("s1", "Statistics", required_proficiency=3, importance_weight=0.5),
        RequirementInput("s2", "Power BI", required_proficiency=3, importance_weight=2.0),
    ]
    student_skills = {}  # missing both

    result = calculate_readiness(requirements, student_skills)

    assert [g.skill_name for g in result.priority_gaps] == ["Power BI", "Statistics"]
    # The top recommendation should reference the highest-weighted gap first.
    assert "Power BI" in result.recommended_actions[0]


def test_career_with_no_requirements_returns_zero_without_crashing():
    result = calculate_readiness([], {})
    assert result.readiness_score == 0.0
    assert result.priority_gaps == []
