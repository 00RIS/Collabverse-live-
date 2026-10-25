"""
COLLABVERSE - Multidisciplinary Skill Knowledge Graph Seeder
=============================================================

Purpose
-------
Build semantic relationships between existing COLLABVERSE skills.

The graph supports:

1. Parent -> child relationships
   Used only for genuine specialization.

   Example:
       Artificial Intelligence
           -> Machine Learning
               -> Deep Learning

2. Related-skill relationships
   Used when two skills are relevant but neither is a specialization
   of the other.

   Example:
       Machine Learning <-> Linear Algebra
       Financial Modeling <-> Corporate Finance
       UI Design <-> UX Design

Safety
------
- Existing skills only.
- Does NOT create skills.
- Does NOT rename skills.
- Does NOT delete skills.
- Does NOT overwrite an existing different parent.
- Related relationships are symmetric.
- Prevents self-parenting.
- Prevents self-relations.
- Dry-run by default.
- Idempotent.

Usage
-----
Dry run:

    python -m app.scripts.seed_skill_graph

Apply:

    python -m app.scripts.seed_skill_graph --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.skill import Skill


# =============================================================================
# NAME NORMALIZATION / ALIASES
# =============================================================================

# These aliases are only used by this graph seeder to find the canonical
# database row.
#
# They do NOT rename anything in the database.

GRAPH_ALIASES: dict[str, str] = {
    "Backend Development": "Backend development",
    "Embedded Systems": "Embedded systems",

    # Keep graph references canonical where possible.
    "AI": "Artificial Intelligence",
    "ML": "Machine Learning",
    "NLP": "Natural Language Processing",
}


def normalize_name(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("&", " and ")

    value = re.sub(
        r"[\(\)\[\]\{\}]",
        " ",
        value,
    )

    value = re.sub(
        r"[^a-z0-9+#]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# =============================================================================
# PARENT -> CHILD RELATIONSHIPS
# =============================================================================
#
# Only genuine specialization belongs here.
#
# Do NOT use parent/child merely because two skills are related.
# =============================================================================

PARENT_CHILD_RELATIONSHIPS: dict[str, list[str]] = {

    # =========================================================================
    # AI / MACHINE LEARNING
    # =========================================================================

    "Artificial Intelligence": [
        "Machine Learning",
        "Natural Language Processing",
        "Computer Vision",
        "Generative AI",
    ],

    "Machine Learning": [
        "Deep Learning",
        "Reinforcement Learning",
        "Supervised Learning",
        "Unsupervised Learning",
        "Predictive Modeling",
    ],

    "Natural Language Processing": [
        "Text Classification",
        "Sentiment Analysis",
        "Named Entity Recognition",
        "Text Generation",
    ],

    "Computer Vision": [
        "Image Processing",
    ],

    # =========================================================================
    # DATA / ANALYTICS
    # =========================================================================

    "Data Science": [
        "Data Analysis",
        "Data Visualization",
        "Exploratory Data Analysis",
        "Predictive Modeling",
    ],

    "Statistics": [
        "Descriptive Statistics",
        "Inferential Statistics",
        "Regression Analysis",
        "Hypothesis Testing",
        "Time Series Analysis",
        "Statistical Modeling",
    ],

    # =========================================================================
    # SOFTWARE / WEB
    # =========================================================================

    "Software Development": [
        "Software Engineering",
        "Web Development",
        "Mobile Application Development",
    ],

    "Web Development": [
        "Frontend Development",
        "Backend Development",
    ],

    "Backend Development": [
        "API Development",
    ],

    # =========================================================================
    # CYBERSECURITY
    # =========================================================================

    "Cybersecurity": [
        "Ethical Hacking",
        "Network Security",
        "Web Application Security",
        "Vulnerability Assessment",
        "Digital Forensics",
    ],

    "Ethical Hacking": [
        "Penetration Testing",
    ],

    # =========================================================================
    # CLOUD / INFRASTRUCTURE
    # =========================================================================

    "Cloud Computing": [
        "AWS",
        "Microsoft Azure",
        "Google Cloud Platform",
    ],

    # =========================================================================
    # BUSINESS
    # =========================================================================

    "Business Analytics": [
        "Data Analysis",
    ],

    "Marketing": [
        "Digital Marketing",
        "Market Research",
        "Brand Management",
        "Social Media Marketing",
    ],

    "Entrepreneurship": [
        "Business Strategy",
        "Business Planning",
        "Innovation Management",
    ],

    # =========================================================================
    # FINANCE
    # =========================================================================

    "Finance": [
        "Financial Analysis",
        "Corporate Finance",
        "Investment Analysis",
        "Financial Modeling",
        "Risk Management",
        "Financial Derivatives",
        "Financial Markets",
    ],

    "Investment Analysis": [
        "Portfolio Management",
    ],

    # =========================================================================
    # ECONOMICS
    # =========================================================================

    "Economics": [
        "Microeconomics",
        "Macroeconomics",
        "Econometrics",
    ],

    # =========================================================================
    # DESIGN
    # =========================================================================

    "Graphic Design": [
        "Illustration",
        "Typography",
        "Visual Communication",
    ],

    "UX Design": [
        "UX Research",
        "Wireframing",
        "Prototyping",
    ],

    # =========================================================================
    # ROBOTICS
    # =========================================================================

    "Robotics": [
        "Robotics Kinematics",
        "Sensor Integration",
        "Embedded Systems",
        "Autonomous Systems",
    ],

    # =========================================================================
    # BIOLOGY
    # =========================================================================

    "Biology": [
        "Biotechnology",
    ],

    # =========================================================================
    # COMMUNICATION
    # =========================================================================

    "Communication": [
        "Written Communication",
        "Verbal Communication",
        "Business Communication",
        "Technical Communication",
        "Public Speaking",
        "Presentation Skills",
    ],

    # =========================================================================
    # LEADERSHIP
    # =========================================================================

    "Leadership": [
        "Team Management",
        "Decision Making",
        "Conflict Resolution",
    ],
}


# =============================================================================
# RELATED SKILL PAIRS
# =============================================================================
#
# Every pair is conceptually symmetric.
#
# Because skill_relations is directional in the database, this script creates:
#
#     A -> B
#     B -> A
#
# =============================================================================

RELATED_SKILL_PAIRS: list[tuple[str, str]] = [

    # =========================================================================
    # AI / ML
    # =========================================================================

    ("Artificial Intelligence", "Python"),
    ("Artificial Intelligence", "Problem Solving"),
    ("Artificial Intelligence", "Data Science"),

    ("Machine Learning", "Python"),
    ("Machine Learning", "Statistics"),
    ("Machine Learning", "Probability"),
    ("Machine Learning", "Linear Algebra"),
    ("Machine Learning", "Calculus"),
    ("Machine Learning", "Optimization"),
    ("Machine Learning", "Data Science"),
    ("Machine Learning", "Data Analysis"),
    ("Machine Learning", "Predictive Modeling"),

    ("Deep Learning", "Computer Vision"),
    ("Deep Learning", "Natural Language Processing"),

    ("Natural Language Processing", "Python"),
    ("Natural Language Processing", "Machine Learning"),
    ("Natural Language Processing", "Text Classification"),
    ("Natural Language Processing", "Sentiment Analysis"),

    ("Computer Vision", "Python"),
    ("Computer Vision", "Machine Learning"),
    ("Computer Vision", "Image Processing"),

    ("Generative AI", "Natural Language Processing"),
    ("Generative AI", "Machine Learning"),
    ("Generative AI", "Artificial Intelligence"),

    ("Reinforcement Learning", "Machine Learning"),

    # =========================================================================
    # MATHEMATICS / STATISTICS
    # =========================================================================

    ("Statistics", "Data Science"),
    ("Statistics", "Data Analysis"),
    ("Statistics", "Business Analytics"),
    ("Statistics", "Econometrics"),

    ("Probability", "Statistics"),
    ("Probability", "Machine Learning"),
    ("Probability", "Risk Management"),

    ("Linear Algebra", "Machine Learning"),
    ("Linear Algebra", "Computer Vision"),

    ("Calculus", "Machine Learning"),
    ("Optimization", "Machine Learning"),

    ("Regression Analysis", "Machine Learning"),
    ("Regression Analysis", "Predictive Modeling"),
    ("Regression Analysis", "Econometrics"),

    ("Hypothesis Testing", "Statistics"),
    ("Hypothesis Testing", "Data Analysis"),

    ("Time Series Analysis", "Forecasting"),
    ("Time Series Analysis", "Financial Analysis"),

    ("Statistical Modeling", "Data Science"),
    ("Statistical Modeling", "Predictive Modeling"),

    # =========================================================================
    # DATA / ANALYTICS
    # =========================================================================

    ("Data Science", "Python"),
    ("Data Science", "SQL"),
    ("Data Science", "Data Visualization"),
    ("Data Science", "Exploratory Data Analysis"),

    ("Data Analysis", "Python"),
    ("Data Analysis", "SQL"),
    ("Data Analysis", "Excel"),
    ("Data Analysis", "Data Visualization"),
    ("Data Analysis", "Exploratory Data Analysis"),

    ("Data Visualization", "Power BI"),
    ("Data Visualization", "Tableau"),

    ("Business Analytics", "Data Analysis"),
    ("Business Analytics", "Statistics"),
    ("Business Analytics", "Excel"),
    ("Business Analytics", "SQL"),
    ("Business Analytics", "Power BI"),
    ("Business Analytics", "Tableau"),

    ("Forecasting", "Predictive Modeling"),
    ("Forecasting", "Statistics"),

    # =========================================================================
    # SOFTWARE DEVELOPMENT
    # =========================================================================

    ("Software Development", "Problem Solving"),
    ("Software Development", "Git"),

    ("Software Engineering", "Software Development"),
    ("Software Engineering", "Git"),

    ("Web Development", "JavaScript"),
    ("Web Development", "Git"),

    ("Frontend Development", "JavaScript"),
    ("Frontend Development", "UI Design"),
    ("Frontend Development", "UX Design"),

    ("Backend Development", "SQL"),
    ("Backend Development", "Database Management"),
    ("Backend Development", "API Development"),
    ("Backend Development", "Python"),

    ("API Development", "Database Management"),
    ("API Development", "Software Development"),

    ("Database Management", "SQL"),

    ("Git", "Version Control Systems (Git, SVN)"),
    ("Git", "Software Development"),

    # =========================================================================
    # DEVOPS / CLOUD
    # =========================================================================

    ("DevOps", "Git"),
    ("DevOps", "Docker"),
    ("DevOps", "Kubernetes"),
    ("DevOps", "Linux"),
    ("DevOps", "Cloud Computing"),

    ("Docker", "Kubernetes"),
    ("Docker", "DevOps"),

    ("Kubernetes", "Cloud Computing"),

    ("Cloud Computing", "Backend Development"),
    ("Cloud Computing", "AWS"),
    ("Cloud Computing", "Microsoft Azure"),
    ("Cloud Computing", "Google Cloud Platform"),

    # =========================================================================
    # CYBERSECURITY
    # =========================================================================

    ("Cybersecurity", "Networking"),
    ("Cybersecurity", "Linux"),
    ("Cybersecurity", "Python"),

    ("Ethical Hacking", "Cybersecurity"),
    ("Ethical Hacking", "Network Security"),
    ("Ethical Hacking", "Vulnerability Assessment"),
    ("Ethical Hacking", "Penetration Testing"),

    ("Network Security", "Networking"),
    ("Network Security", "Cybersecurity"),

    ("Web Application Security", "Web Development"),
    ("Web Application Security", "Cybersecurity"),

    ("Vulnerability Assessment", "Cybersecurity"),
    ("Vulnerability Assessment", "Penetration Testing"),

    ("Digital Forensics", "Cybersecurity"),

    # =========================================================================
    # BUSINESS / MANAGEMENT
    # =========================================================================

    ("Business Strategy", "Entrepreneurship"),
    ("Business Strategy", "Market Research"),
    ("Business Strategy", "Product Management"),

    ("Marketing", "Market Research"),
    ("Marketing", "Brand Management"),
    ("Marketing", "Sales"),
    ("Marketing", "Digital Marketing"),

    ("Digital Marketing", "Social Media Marketing"),
    ("Digital Marketing", "Content Writing"),
    ("Digital Marketing", "Content Creation"),

    ("Brand Management", "Marketing"),
    ("Brand Management", "Market Research"),

    ("Sales", "Communication"),
    ("Sales", "Negotiation"),
    ("Sales", "Business Communication"),

    ("Product Management", "Market Research"),
    ("Product Management", "UX Design"),
    ("Product Management", "Project Management"),
    ("Product Management", "Business Strategy"),

    ("Project Management", "Leadership"),
    ("Project Management", "Team Management"),
    ("Project Management", "Time Management"),
    ("Project Management", "Communication"),

    ("Operations Management", "Supply Chain Management"),
    ("Operations Management", "Project Management"),

    ("Entrepreneurship", "Innovation Management"),
    ("Entrepreneurship", "Business Planning"),
    ("Entrepreneurship", "Creativity"),

    ("Innovation Management", "Creativity"),
    ("Innovation Management", "Business Strategy"),

    # =========================================================================
    # FINANCE
    # =========================================================================

    ("Finance", "Economics"),

    ("Financial Analysis", "Accounting"),
    ("Financial Analysis", "Financial Modeling"),
    ("Financial Analysis", "Excel"),
    ("Financial Analysis", "Statistics"),

    ("Financial Modeling", "Corporate Finance"),
    ("Financial Modeling", "Investment Analysis"),
    ("Financial Modeling", "Excel"),
    ("Financial Modeling", "Forecasting"),

    ("Corporate Finance", "Financial Analysis"),
    ("Corporate Finance", "Financial Modeling"),

    ("Investment Analysis", "Portfolio Management"),
    ("Investment Analysis", "Financial Analysis"),
    ("Investment Analysis", "Financial Markets"),

    ("Portfolio Management", "Risk Management"),
    ("Portfolio Management", "Financial Markets"),
    ("Portfolio Management", "Investment Analysis"),

    ("Financial Derivatives", "Risk Management"),
    ("Financial Derivatives", "Financial Markets"),

    ("Risk Management", "Statistics"),
    ("Risk Management", "Probability"),
    ("Risk Management", "Financial Analysis"),

    ("Econometrics", "Statistics"),
    ("Econometrics", "Regression Analysis"),
    ("Econometrics", "Economics"),

    ("Microeconomics", "Economics"),
    ("Macroeconomics", "Economics"),

    # =========================================================================
    # DESIGN / CREATIVE
    # =========================================================================

    ("UI Design", "UX Design"),
    ("UI Design", "Graphic Design"),
    ("UI Design", "Frontend Development"),

    ("UX Design", "UX Research"),
    ("UX Design", "Wireframing"),
    ("UX Design", "Prototyping"),
    ("UX Design", "Product Management"),

    ("Graphic Design", "Visual Communication"),
    ("Graphic Design", "Illustration"),
    ("Graphic Design", "Typography"),

    ("Animation", "Graphic Design"),
    ("Animation", "Video Editing"),

    ("Photography", "Visual Communication"),
    ("Photography", "Video Editing"),

    ("Video Editing", "Content Creation"),

    ("Content Creation", "Content Writing"),
    ("Content Creation", "Digital Marketing"),

    # =========================================================================
    # ROBOTICS / IOT / ENGINEERING
    # =========================================================================

    ("Robotics", "Artificial Intelligence"),
    ("Robotics", "Computer Vision"),
    ("Robotics", "Embedded Systems"),
    ("Robotics", "Mechanical Engineering"),
    ("Robotics", "Electronics Engineering"),

    ("Embedded Systems", "Electronics Engineering"),
    ("Embedded Systems", "IoT"),

    ("Sensor Integration", "IoT Sensor Integration"),
    ("Sensor Integration", "Robotics"),

    ("IoT", "Embedded Systems"),
    ("IoT", "Cloud Computing"),
    ("IoT", "Sensor Integration"),

    ("Mechanical Engineering", "Robotics"),
    ("Mechanical Engineering", "Materials Science"),

    ("Electrical Engineering", "Electronics Engineering"),
    ("Electrical Engineering", "Embedded Systems"),

    ("Electronics Engineering", "Robotics"),
    ("Electronics Engineering", "Embedded Systems"),

    # =========================================================================
    # SCIENCE
    # =========================================================================

    ("Physics", "Calculus"),
    ("Physics", "Linear Algebra"),
    ("Physics", "Mechanical Engineering"),

    ("Chemistry", "Materials Science"),

    ("Biology", "Biotechnology"),

    ("Biotechnology", "Data Analysis"),
    ("Biotechnology", "Statistics"),

    ("Environmental Science", "Sustainability"),

    ("Materials Science", "Mechanical Engineering"),
    ("Materials Science", "Chemistry"),

    # =========================================================================
    # COMMUNICATION
    # =========================================================================

    ("Communication", "Public Speaking"),
    ("Communication", "Presentation Skills"),
    ("Communication", "Written Communication"),
    ("Communication", "Verbal Communication"),
    ("Communication", "Business Communication"),
    ("Communication", "Technical Communication"),
    ("Communication", "Teamwork"),

    ("Technical Communication", "Technical Writing"),
    ("Technical Communication", "Presentation Skills"),

    ("Business Communication", "Sales"),
    ("Business Communication", "Marketing"),
    ("Business Communication", "Negotiation"),

    ("Public Speaking", "Presentation Skills"),
    ("Public Speaking", "Leadership"),

    ("Content Writing", "Written Communication"),
    ("Content Writing", "Communication"),

    # =========================================================================
    # LEADERSHIP / PROFESSIONAL / SOFT SKILLS
    # =========================================================================

    ("Leadership", "Communication"),
    ("Leadership", "Decision Making"),
    ("Leadership", "Team Management"),
    ("Leadership", "Conflict Resolution"),

    ("Collaboration", "Teamwork"),
    ("Collaboration", "Communication"),
    ("Collaboration", "Problem Solving"),

    ("Teamwork", "Communication"),
    ("Teamwork", "Leadership"),
    ("Teamwork", "Conflict Resolution"),

    ("Problem Solving", "Critical Thinking"),
    ("Problem Solving", "Logical Reasoning"),
    ("Problem Solving", "Decision Making"),
    ("Problem Solving", "Analytical Thinking"),

    ("Critical Thinking", "Decision Making"),
    ("Critical Thinking", "Analytical Thinking"),
    ("Critical Thinking", "Logical Reasoning"),

    ("Decision Making", "Analytical Thinking"),

    ("Time Management", "Project Management"),

    ("Negotiation", "Communication"),
    ("Negotiation", "Sales"),
    ("Negotiation", "Conflict Resolution"),

    ("Creativity", "Innovation Management"),
    ("Creativity", "Problem Solving"),
]


# =============================================================================
# REPORTING
# =============================================================================


@dataclass
class GraphStats:
    parent_created: int = 0
    parent_already_exists: int = 0
    parent_missing: int = 0
    parent_conflicts: int = 0
    parent_self_skipped: int = 0

    related_created: int = 0
    related_already_exists: int = 0
    related_missing: int = 0
    related_self_skipped: int = 0

    alias_resolutions: set[str] = field(
        default_factory=set
    )

    normalized_resolutions: set[str] = field(
        default_factory=set
    )

    missing_skills: set[str] = field(
        default_factory=set
    )

    parent_conflict_details: list[str] = field(
        default_factory=list
    )


# =============================================================================
# DISPLAY
# =============================================================================


def separator(title: str | None = None) -> None:
    print()
    print("=" * 96)

    if title:
        print(title)
        print("=" * 96)


# =============================================================================
# SKILL LOOKUP
# =============================================================================


class SkillLookup:
    """
    Safe skill lookup for graph construction.

    Resolution order:

        1. Exact name
        2. Explicit graph alias
        3. Unique normalized-name match

    No fuzzy matching is performed here.
    """

    def __init__(
        self,
        db: Session,
        stats: GraphStats,
    ) -> None:

        self.db = db
        self.stats = stats

        skills = (
            db.query(Skill)
            .order_by(Skill.name.asc())
            .all()
        )

        self.skills = skills

        self.exact: dict[str, Skill] = {
            skill.name: skill
            for skill in skills
        }

        self.normalized: dict[str, list[Skill]] = {}

        for skill in skills:

            key = normalize_name(
                skill.name
            )

            self.normalized.setdefault(
                key,
                [],
            ).append(skill)

    def resolve(
        self,
        requested_name: str,
    ) -> Skill | None:

        # ---------------------------------------------------------------------
        # Exact
        # ---------------------------------------------------------------------

        exact = self.exact.get(
            requested_name
        )

        if exact is not None:
            return exact

        # ---------------------------------------------------------------------
        # Explicit alias
        # ---------------------------------------------------------------------

        alias_target = GRAPH_ALIASES.get(
            requested_name
        )

        if alias_target:

            alias_skill = self.exact.get(
                alias_target
            )

            if alias_skill is not None:

                self.stats.alias_resolutions.add(
                    f"{requested_name} -> {alias_skill.name}"
                )

                return alias_skill

        # ---------------------------------------------------------------------
        # Unique normalized match
        # ---------------------------------------------------------------------

        normalized = normalize_name(
            requested_name
        )

        matches = self.normalized.get(
            normalized,
            [],
        )

        if len(matches) == 1:

            skill = matches[0]

            self.stats.normalized_resolutions.add(
                f"{requested_name} -> {skill.name}"
            )

            return skill

        # Never guess if normalization produces multiple matches.
        return None


# =============================================================================
# DATABASE HELPERS
# =============================================================================


def relation_exists(
    db: Session,
    skill_id,
    related_skill_id,
) -> bool:

    row = db.execute(
        text(
            """
            SELECT 1
            FROM skill_relations
            WHERE skill_id = :skill_id
              AND related_skill_id = :related_skill_id
            LIMIT 1
            """
        ),
        {
            "skill_id": skill_id,
            "related_skill_id": related_skill_id,
        },
    ).first()

    return row is not None


def insert_relation(
    db: Session,
    skill_id,
    related_skill_id,
) -> bool:

    if skill_id == related_skill_id:
        return False

    if relation_exists(
        db,
        skill_id,
        related_skill_id,
    ):
        return False

    db.execute(
        text(
            """
            INSERT INTO skill_relations (
                skill_id,
                related_skill_id
            )
            VALUES (
                :skill_id,
                :related_skill_id
            )
            """
        ),
        {
            "skill_id": skill_id,
            "related_skill_id": related_skill_id,
        },
    )

    return True


# =============================================================================
# CONFIG VALIDATION
# =============================================================================


def validate_configuration() -> None:

    # -------------------------------------------------------------------------
    # Parent definitions
    # -------------------------------------------------------------------------

    for parent_name, children in PARENT_CHILD_RELATIONSHIPS.items():

        if not parent_name.strip():
            raise ValueError(
                "Blank parent skill found."
            )

        seen_children: set[str] = set()

        for child_name in children:

            if not child_name.strip():
                raise ValueError(
                    f"Blank child under '{parent_name}'."
                )

            if normalize_name(parent_name) == normalize_name(child_name):
                raise ValueError(
                    f"Self-parent definition: "
                    f"{parent_name} -> {child_name}"
                )

            normalized_child = normalize_name(
                child_name
            )

            if normalized_child in seen_children:
                raise ValueError(
                    f"Duplicate child '{child_name}' "
                    f"under '{parent_name}'."
                )

            seen_children.add(
                normalized_child
            )

    # -------------------------------------------------------------------------
    # Related definitions
    # -------------------------------------------------------------------------

    seen_pairs: set[tuple[str, str]] = set()

    for left, right in RELATED_SKILL_PAIRS:

        if normalize_name(left) == normalize_name(right):
            raise ValueError(
                f"Self-related graph definition: {left} <-> {right}"
            )

        pair = tuple(
            sorted(
                (
                    normalize_name(left),
                    normalize_name(right),
                )
            )
        )

        # Duplicate conceptual pairs are harmless at DB level,
        # but keeping the configuration clean is better.
        if pair in seen_pairs:
            continue

        seen_pairs.add(
            pair
        )


# =============================================================================
# PARENT GRAPH
# =============================================================================


def seed_parent_graph(
    db: Session,
    lookup: SkillLookup,
    stats: GraphStats,
) -> None:

    separator("PARENT / CHILD GRAPH")

    skill_by_id = {
        skill.id: skill
        for skill in lookup.skills
    }

    for requested_parent, children in PARENT_CHILD_RELATIONSHIPS.items():

        parent = lookup.resolve(
            requested_parent
        )

        if parent is None:

            stats.missing_skills.add(
                requested_parent
            )

            stats.parent_missing += len(
                children
            )

            print(
                f"SKIP PARENT: '{requested_parent}' does not exist."
            )

            continue

        for requested_child in children:

            child = lookup.resolve(
                requested_child
            )

            if child is None:

                stats.missing_skills.add(
                    requested_child
                )

                stats.parent_missing += 1

                print(
                    f"SKIP: {requested_parent} -> {requested_child} "
                    f"(child missing)"
                )

                continue

            if child.id == parent.id:

                stats.parent_self_skipped += 1

                print(
                    f"SKIP SELF: {parent.name} -> {child.name}"
                )

                continue

            # Already correct.
            if child.parent_skill_id == parent.id:

                stats.parent_already_exists += 1

                print(
                    f"EXISTS: {parent.name} -> {child.name}"
                )

                continue

            # Never overwrite an existing different parent.
            if child.parent_skill_id is not None:

                existing_parent = skill_by_id.get(
                    child.parent_skill_id
                )

                existing_parent_name = (
                    existing_parent.name
                    if existing_parent is not None
                    else str(child.parent_skill_id)
                )

                detail = (
                    f"{child.name}: existing parent "
                    f"'{existing_parent_name}', proposed "
                    f"'{parent.name}'"
                )

                stats.parent_conflicts += 1

                stats.parent_conflict_details.append(
                    detail
                )

                print(
                    f"CONFLICT: {detail}"
                )

                continue

            child.parent_skill_id = parent.id

            db.flush()

            stats.parent_created += 1

            print(
                f"CREATE: {parent.name} -> {child.name}"
            )


# =============================================================================
# RELATED GRAPH
# =============================================================================


def seed_related_graph(
    db: Session,
    lookup: SkillLookup,
    stats: GraphStats,
) -> None:

    separator("RELATED SKILL GRAPH")

    processed_pairs: set[tuple] = set()

    for requested_left, requested_right in RELATED_SKILL_PAIRS:

        left = lookup.resolve(
            requested_left
        )

        right = lookup.resolve(
            requested_right
        )

        missing: list[str] = []

        if left is None:
            missing.append(
                requested_left
            )
            stats.missing_skills.add(
                requested_left
            )

        if right is None:
            missing.append(
                requested_right
            )
            stats.missing_skills.add(
                requested_right
            )

        if missing:

            stats.related_missing += 1

            print(
                f"SKIP: {requested_left} <-> {requested_right} "
                f"(missing: {', '.join(missing)})"
            )

            continue

        if left.id == right.id:

            stats.related_self_skipped += 1

            print(
                f"SKIP SELF: {left.name}"
            )

            continue

        conceptual_pair = tuple(
            sorted(
                (
                    str(left.id),
                    str(right.id),
                )
            )
        )

        if conceptual_pair in processed_pairs:
            continue

        processed_pairs.add(
            conceptual_pair
        )

        forward_created = insert_relation(
            db,
            left.id,
            right.id,
        )

        reverse_created = insert_relation(
            db,
            right.id,
            left.id,
        )

        if forward_created:
            stats.related_created += 1
        else:
            stats.related_already_exists += 1

        if reverse_created:
            stats.related_created += 1
        else:
            stats.related_already_exists += 1

        if forward_created or reverse_created:

            print(
                f"CREATE: {left.name} <-> {right.name}"
            )

        else:

            print(
                f"EXISTS: {left.name} <-> {right.name}"
            )


# =============================================================================
# VALIDATION
# =============================================================================


def validate_graph(
    db: Session,
) -> None:

    separator("GRAPH VALIDATION")

    # -------------------------------------------------------------------------
    # Self-parent
    # -------------------------------------------------------------------------

    self_parent_count = int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM skills
                WHERE parent_skill_id = id
                """
            )
        ).scalar_one()
    )

    if self_parent_count:
        raise RuntimeError(
            f"{self_parent_count} self-parenting skills detected."
        )

    print(
        "PASS: no self-parenting skills."
    )

    # -------------------------------------------------------------------------
    # Self relation
    # -------------------------------------------------------------------------

    self_relation_count = int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM skill_relations
                WHERE skill_id = related_skill_id
                """
            )
        ).scalar_one()
    )

    if self_relation_count:
        raise RuntimeError(
            f"{self_relation_count} self-related skill rows detected."
        )

    print(
        "PASS: no self-related skills."
    )

    # -------------------------------------------------------------------------
    # Orphan parent
    # -------------------------------------------------------------------------

    orphan_parent_count = int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM skills child
                LEFT JOIN skills parent
                    ON parent.id = child.parent_skill_id
                WHERE child.parent_skill_id IS NOT NULL
                  AND parent.id IS NULL
                """
            )
        ).scalar_one()
    )

    if orphan_parent_count:
        raise RuntimeError(
            f"{orphan_parent_count} orphan parent references detected."
        )

    print(
        "PASS: no orphan parent references."
    )

    # -------------------------------------------------------------------------
    # Orphan relations
    # -------------------------------------------------------------------------

    orphan_relation_count = int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM skill_relations r
                LEFT JOIN skills s1
                    ON s1.id = r.skill_id
                LEFT JOIN skills s2
                    ON s2.id = r.related_skill_id
                WHERE s1.id IS NULL
                   OR s2.id IS NULL
                """
            )
        ).scalar_one()
    )

    if orphan_relation_count:
        raise RuntimeError(
            f"{orphan_relation_count} orphan skill relations detected."
        )

    print(
        "PASS: no orphan skill relations."
    )

    # -------------------------------------------------------------------------
    # Symmetry
    # -------------------------------------------------------------------------

    asymmetric_count = int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM skill_relations a
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM skill_relations b
                    WHERE b.skill_id = a.related_skill_id
                      AND b.related_skill_id = a.skill_id
                )
                """
            )
        ).scalar_one()
    )

    if asymmetric_count:
        raise RuntimeError(
            f"{asymmetric_count} asymmetric related-skill "
            f"relationships detected."
        )

    print(
        "PASS: all related-skill relationships are symmetric."
    )

    # -------------------------------------------------------------------------
    # Duplicate directional rows
    # -------------------------------------------------------------------------

    duplicate_relation_count = int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT skill_id, related_skill_id, COUNT(*) AS c
                    FROM skill_relations
                    GROUP BY skill_id, related_skill_id
                    HAVING COUNT(*) > 1
                ) duplicates
                """
            )
        ).scalar_one()
    )

    if duplicate_relation_count:
        raise RuntimeError(
            f"{duplicate_relation_count} duplicate related-skill "
            f"pairs detected."
        )

    print(
        "PASS: no duplicate directional skill relations."
    )


# =============================================================================
# SUMMARY
# =============================================================================


def print_summary(
    stats: GraphStats,
) -> None:

    separator("SKILL GRAPH SUMMARY")

    print("PARENT / CHILD")
    print(
        f"  created:               {stats.parent_created}"
    )
    print(
        f"  already existed:       {stats.parent_already_exists}"
    )
    print(
        f"  skipped missing:       {stats.parent_missing}"
    )
    print(
        f"  conflicts:             {stats.parent_conflicts}"
    )
    print(
        f"  self skipped:          {stats.parent_self_skipped}"
    )

    print()

    print("RELATED SKILLS")
    print(
        f"  directional created:   {stats.related_created}"
    )
    print(
        f"  already existed:       {stats.related_already_exists}"
    )
    print(
        f"  pairs skipped missing: {stats.related_missing}"
    )
    print(
        f"  self skipped:          {stats.related_self_skipped}"
    )

    if stats.alias_resolutions:

        separator("GRAPH ALIAS RESOLUTIONS")

        for value in sorted(
            stats.alias_resolutions
        ):
            print(
                f"  {value}"
            )

    if stats.normalized_resolutions:

        separator("NORMALIZED NAME RESOLUTIONS")

        for value in sorted(
            stats.normalized_resolutions
        ):
            print(
                f"  {value}"
            )

    if stats.parent_conflict_details:

        separator("PARENT CONFLICTS - REVIEW")

        for value in stats.parent_conflict_details:
            print(
                f"  {value}"
            )

    if stats.missing_skills:

        separator("GRAPH SKILLS STILL MISSING FROM CATALOG")

        print(
            "These were NOT created."
        )
        print()

        for name in sorted(
            stats.missing_skills
        ):
            print(
                f"  - {name}"
            )


# =============================================================================
# RUNNER
# =============================================================================


def run(
    db: Session,
    apply_changes: bool,
) -> None:

    separator(
        "COLLABVERSE MULTIDISCIPLINARY SKILL KNOWLEDGE GRAPH"
    )

    if apply_changes:

        print(
            "MODE: APPLY"
        )

        print()
        print(
            "Graph relationships will be committed if validation passes."
        )

    else:

        print(
            "MODE: DRY RUN"
        )

        print()
        print(
            "Graph relationships will be simulated and rolled back."
        )

    validate_configuration()

    skill_count = db.query(
        Skill
    ).count()

    print()
    print(
        f"Current skill catalog: {skill_count}"
    )

    if skill_count != 284:

        print()
        print(
            "WARNING:"
        )

        print(
            f"Expected 284 skills after core seeding, "
            f"but found {skill_count}."
        )

        print(
            "The graph seeder can continue, but review the output carefully."
        )

    stats = GraphStats()

    lookup = SkillLookup(
        db,
        stats,
    )

    seed_parent_graph(
        db,
        lookup,
        stats,
    )

    seed_related_graph(
        db,
        lookup,
        stats,
    )

    db.flush()

    validate_graph(
        db
    )

    print_summary(
        stats
    )

    if apply_changes:

        separator("COMMIT")

        db.commit()

        print(
            "SUCCESS: multidisciplinary skill knowledge graph committed."
        )

    else:

        separator("DRY RUN COMPLETE")

        db.rollback()

        print(
            "SUCCESS: graph construction and validation completed."
        )

        print()
        print(
            "NO DATABASE CHANGES WERE SAVED."
        )

        print()
        print(
            "Review skipped skills and parent conflicts before --apply."
        )


# =============================================================================
# CLI
# =============================================================================


def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Seed the COLLABVERSE multidisciplinary skill knowledge graph."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Commit graph relationships. "
            "Without this flag the script performs a dry run."
        ),
    )

    return parser.parse_args()


def main() -> None:

    args = parse_args()

    db = SessionLocal()

    try:

        run(
            db=db,
            apply_changes=args.apply,
        )

    except (
        SQLAlchemyError,
        RuntimeError,
        ValueError,
    ) as exc:

        db.rollback()

        separator("SKILL GRAPH SEED FAILED")

        print(
            "The transaction was rolled back."
        )

        print(
            "NO PARTIAL GRAPH CHANGES WERE COMMITTED."
        )

        print()

        print(
            f"ERROR: {exc}"
        )

        sys.exit(1)

    except Exception as exc:

        db.rollback()

        separator("UNEXPECTED ERROR")

        print(
            "The transaction was rolled back."
        )

        print(
            "NO PARTIAL GRAPH CHANGES WERE COMMITTED."
        )

        print()

        print(
            f"{type(exc).__name__}: {exc}"
        )

        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()