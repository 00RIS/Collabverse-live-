"""
COLLABVERSE - Core Multidisciplinary Skill Catalog Seeder

Purpose
-------
Add a curated set of foundational skills that should exist independently
of external opportunity sources such as Unstop.

Architecture
------------
CORE CATALOG
    +
DYNAMIC RESOLVER
    +
SKILL KNOWLEDGE GRAPH

The core catalog provides stable, multidisciplinary concepts.

The dynamic resolver remains responsible for discovering legitimate
long-tail skills from real opportunities.

Safety
------
- DRY RUN by default.
- Existing skills are never overwritten.
- Existing UUIDs are preserved.
- No skills are deleted.
- No aliases are merged here.
- No graph relationships are created here.
- Exact names are checked first.
- Normalized names are checked to avoid obvious duplicate creation.
- Entire operation is transactional.

Usage
-----
Dry run:

    python -m app.scripts.seed_core_skills

Apply:

    python -m app.scripts.seed_core_skills --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.skill import Skill, SkillCategory


# =============================================================================
# CURATED CORE SKILLS
# =============================================================================
#
# IMPORTANT:
# These are real reusable skills / knowledge areas.
#
# We intentionally avoid adding broad artificial container nodes merely
# to support hierarchy.
#
# Example:
#   GOOD: Linear Algebra
#   GOOD: Financial Modeling
#   GOOD: Public Speaking
#
#   NOT NECESSARY HERE:
#       Science
#       Engineering
#       Management
#       Programming
#
# The knowledge graph can use relationships between real skills without
# requiring every branch to have an abstract root node.
# =============================================================================


CORE_SKILLS: dict[SkillCategory, list[str]] = {

    # =========================================================================
    # TECHNICAL
    # =========================================================================

    SkillCategory.TECHNICAL: [

        # AI / ML
        "Computer Vision",
        "Generative AI",
        "Reinforcement Learning",
        "Supervised Learning",
        "Unsupervised Learning",
        "Text Classification",
        "Named Entity Recognition",
        "Text Generation",
        "Image Processing",

        # Data
        "Data Science",
        "Data Visualization",
        "Exploratory Data Analysis",

        # Software / Web
        "Software Development",
        "Software Engineering",
        "Web Development",
        "Frontend Development",
        "Backend Development",
        "API Development",

        # Infrastructure
        "DevOps",
        "Docker",
        "Kubernetes",

        # Database
        "Database Management",

        # Cybersecurity
        "Network Security",
        "Networking",
        "Web Application Security",
        "Penetration Testing",

        # IoT / Embedded / Robotics
        "IoT",
        "Embedded Systems",
        "Robotics",

        # Cloud
        "AWS",
        "Google Cloud Platform",
    ],

    # =========================================================================
    # ANALYTICAL / MATHEMATICS / STATISTICS
    # =========================================================================

    SkillCategory.ANALYTICAL: [

        "Linear Algebra",
        "Probability",
        "Calculus",
        "Optimization",

        "Descriptive Statistics",
        "Inferential Statistics",
        "Regression Analysis",
        "Hypothesis Testing",
        "Statistical Modeling",

        "Forecasting",
        "Econometrics",

        "Analytical Thinking",
    ],

    # =========================================================================
    # BUSINESS / FINANCE / ECONOMICS
    # =========================================================================

    SkillCategory.BUSINESS: [

        # Finance
        "Corporate Finance",
        "Investment Analysis",
        "Portfolio Management",
        "Financial Modeling",
        "Risk Management",
        "Financial Derivatives",
        "Financial Markets",
        "Accounting",

        # Economics
        "Microeconomics",
        "Macroeconomics",

        # Marketing
        "Digital Marketing",
        "Brand Management",
        "Social Media Marketing",
        "Sales",

        # Operations
        "Supply Chain Management",
    ],

    # =========================================================================
    # COMMUNICATION
    # =========================================================================

    SkillCategory.COMMUNICATION: [

        "Public Speaking",
        "Business Communication",
        "Technical Writing",
        "Verbal Communication",
    ],

    # =========================================================================
    # LEADERSHIP
    # =========================================================================

    SkillCategory.LEADERSHIP: [

        "Conflict Resolution",
        "Negotiation",
    ],

    # =========================================================================
    # DESIGN / CREATIVE
    # =========================================================================

    SkillCategory.DESIGN: [

        "Illustration",
        "Typography",
        "Visual Communication",

        "UX Research",
        "Wireframing",
        "Prototyping",

        "Animation",
        "Photography",
        "Video Editing",
        "Content Creation",
    ],

    # =========================================================================
    # DOMAIN KNOWLEDGE
    # =========================================================================

    SkillCategory.DOMAIN_KNOWLEDGE: [

        # Engineering
        "Mechanical Engineering",
        "Electrical Engineering",
        "Electronics Engineering",

        # Science
        "Physics",
        "Chemistry",
        "Biology",
        "Biotechnology",
        "Environmental Science",
        "Materials Science",

        # Sustainability
        "Sustainability",
    ],

    # =========================================================================
    # SOFT SKILLS
    # =========================================================================

    SkillCategory.SOFT_SKILLS: [
        # Keep intentionally small.
        #
        # Most important soft skills such as:
        # Problem Solving
        # Critical Thinking
        # Teamwork
        # Collaboration
        # Creativity
        # Time Management
        #
        # already exist in the catalog.
    ],
}


# =============================================================================
# DESCRIPTION TEMPLATES
# =============================================================================


CATEGORY_DESCRIPTIONS: dict[SkillCategory, str] = {
    SkillCategory.TECHNICAL:
        "Core technical skill used across technology, engineering, "
        "software, data, or digital projects.",

    SkillCategory.ANALYTICAL:
        "Core analytical, mathematical, statistical, or quantitative skill.",

    SkillCategory.BUSINESS:
        "Core business, finance, economics, marketing, or operational skill.",

    SkillCategory.COMMUNICATION:
        "Core communication skill used in academic and professional work.",

    SkillCategory.LEADERSHIP:
        "Core leadership and professional management skill.",

    SkillCategory.DESIGN:
        "Core design, creative, visual, or media skill.",

    SkillCategory.DOMAIN_KNOWLEDGE:
        "Core domain knowledge used in science, engineering, or "
        "specialized professional work.",

    SkillCategory.SOFT_SKILLS:
        "Core transferable professional and interpersonal skill.",
}


# =============================================================================
# REPORTING
# =============================================================================


@dataclass
class SeedStats:
    total_requested: int = 0

    created: int = 0
    exact_existing: int = 0
    normalized_existing: int = 0

    created_by_category: dict[str, int] = field(
        default_factory=dict
    )

    existing_by_category: dict[str, int] = field(
        default_factory=dict
    )

    normalized_conflicts: list[str] = field(
        default_factory=list
    )

    created_names: list[str] = field(
        default_factory=list
    )


# =============================================================================
# HELPERS
# =============================================================================


def separator(title: str | None = None) -> None:
    print()
    print("=" * 92)

    if title:
        print(title)
        print("=" * 92)


def normalize_skill_name(value: str) -> str:
    """
    Conservative normalization used only for duplicate detection.

    We do NOT aggressively remove words such as:
        design
        development
        analysis
        engineering

    because those words can materially change skill meaning.
    """

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


def category_value(category: SkillCategory) -> str:
    value = category.value

    if isinstance(value, str):
        return value

    return str(value)


def build_skill_indexes(
    db: Session,
) -> tuple[
    dict[str, Skill],
    dict[str, list[Skill]],
]:
    """
    Build:
        exact-name index
        normalized-name index

    Normalized index stores a list because multiple existing skills may
    theoretically normalize to the same value.
    """

    skills = (
        db.query(Skill)
        .order_by(Skill.name.asc())
        .all()
    )

    exact: dict[str, Skill] = {}
    normalized: dict[str, list[Skill]] = {}

    for skill in skills:

        exact[skill.name] = skill

        key = normalize_skill_name(
            skill.name
        )

        normalized.setdefault(
            key,
            [],
        ).append(skill)

    return exact, normalized


def increment(
    mapping: dict[str, int],
    key: str,
) -> None:
    mapping[key] = (
        mapping.get(key, 0) + 1
    )


# =============================================================================
# VALIDATE CONFIGURATION
# =============================================================================


def validate_core_configuration() -> None:
    """
    Catch accidental duplicate definitions in this Python file before
    touching the database.
    """

    seen_exact: dict[str, SkillCategory] = {}
    seen_normalized: dict[str, tuple[str, SkillCategory]] = {}

    for category, names in CORE_SKILLS.items():

        for name in names:

            clean_name = name.strip()

            if not clean_name:
                raise ValueError(
                    f"Blank skill name found in category "
                    f"{category_value(category)}."
                )

            if clean_name in seen_exact:
                raise ValueError(
                    f"Skill '{clean_name}' appears more than once "
                    f"in CORE_SKILLS."
                )

            seen_exact[clean_name] = category

            normalized = normalize_skill_name(
                clean_name
            )

            previous = seen_normalized.get(
                normalized
            )

            if previous is not None:
                previous_name, previous_category = previous

                raise ValueError(
                    "Core configuration contains normalized duplicates: "
                    f"'{previous_name}' "
                    f"({category_value(previous_category)}) and "
                    f"'{clean_name}' "
                    f"({category_value(category)})."
                )

            seen_normalized[normalized] = (
                clean_name,
                category,
            )


# =============================================================================
# CORE SEEDING
# =============================================================================


def seed_core_skills(
    db: Session,
    stats: SeedStats,
) -> None:

    exact_index, normalized_index = build_skill_indexes(
        db
    )

    separator("CORE SKILL SEED")

    for category, names in CORE_SKILLS.items():

        category_name = category_value(
            category
        )

        print()
        print(
            f"[{category_name.upper()}]"
        )

        for name in names:

            stats.total_requested += 1

            # -----------------------------------------------------------------
            # Exact existing skill
            # -----------------------------------------------------------------

            existing = exact_index.get(
                name
            )

            if existing is not None:

                stats.exact_existing += 1

                increment(
                    stats.existing_by_category,
                    category_name,
                )

                existing_category = category_value(
                    existing.category
                )

                if existing.category != category:

                    print(
                        f"EXISTS: {name} "
                        f"[database category={existing_category}, "
                        f"proposed={category_name}]"
                    )

                else:

                    print(
                        f"EXISTS: {name}"
                    )

                continue

            # -----------------------------------------------------------------
            # Normalized existing skill
            # -----------------------------------------------------------------

            normalized_name = normalize_skill_name(
                name
            )

            normalized_matches = normalized_index.get(
                normalized_name,
                [],
            )

            if normalized_matches:

                stats.normalized_existing += 1

                increment(
                    stats.existing_by_category,
                    category_name,
                )

                matched_names = ", ".join(
                    skill.name
                    for skill in normalized_matches
                )

                conflict = (
                    f"'{name}' was not created because normalized "
                    f"matching found: {matched_names}"
                )

                stats.normalized_conflicts.append(
                    conflict
                )

                print(
                    f"NORMALIZED EXISTS: {name} -> {matched_names}"
                )

                continue

            # -----------------------------------------------------------------
            # Create new core skill
            # -----------------------------------------------------------------

            skill = Skill(
                name=name,
                category=category,
                description=CATEGORY_DESCRIPTIONS[
                    category
                ],
            )

            db.add(
                skill
            )

            db.flush()

            stats.created += 1

            increment(
                stats.created_by_category,
                category_name,
            )

            stats.created_names.append(
                name
            )

            print(
                f"CREATE: {name}"
            )

            # Update indexes immediately so this execution remains idempotent.
            exact_index[name] = skill

            normalized_index.setdefault(
                normalized_name,
                [],
            ).append(skill)


# =============================================================================
# VALIDATION
# =============================================================================


def validate_seed_result(
    db: Session,
    stats: SeedStats,
    before_count: int,
) -> int:

    separator("VALIDATION")

    after_count = db.query(
        Skill
    ).count()

    expected_count = (
        before_count
        + stats.created
    )

    print(
        f"Skills before:   {before_count}"
    )
    print(
        f"Skills created:  {stats.created}"
    )
    print(
        f"Skills after:    {after_count}"
    )
    print(
        f"Expected after:  {expected_count}"
    )

    if after_count != expected_count:
        raise RuntimeError(
            "Unexpected skill count after core seeding."
        )

    print(
        "PASS: skill count matches expected result."
    )

    # -------------------------------------------------------------------------
    # Confirm every requested core concept is now represented.
    # -------------------------------------------------------------------------

    exact_index, normalized_index = build_skill_indexes(
        db
    )

    missing: list[str] = []

    for names in CORE_SKILLS.values():

        for name in names:

            if name in exact_index:
                continue

            normalized = normalize_skill_name(
                name
            )

            if normalized in normalized_index:
                continue

            missing.append(
                name
            )

    if missing:
        raise RuntimeError(
            "Core skills still missing after seed: "
            + ", ".join(
                sorted(missing)
            )
        )

    print(
        "PASS: every requested core skill is represented."
    )

    # -------------------------------------------------------------------------
    # Check exact duplicate names.
    # -------------------------------------------------------------------------

    duplicate_rows = (
        db.query(
            Skill.name
        )
        .all()
    )

    names = [
        row[0]
        for row in duplicate_rows
    ]

    if len(names) != len(set(names)):
        raise RuntimeError(
            "Exact duplicate skill names detected."
        )

    print(
        "PASS: no exact duplicate skill names."
    )

    return after_count


# =============================================================================
# SUMMARY
# =============================================================================


def print_summary(
    stats: SeedStats,
) -> None:

    separator("CORE SKILL SUMMARY")

    print(
        f"Requested core skills:      {stats.total_requested}"
    )
    print(
        f"Already existed exact:      {stats.exact_existing}"
    )
    print(
        f"Already existed normalized: {stats.normalized_existing}"
    )
    print(
        f"New skills created:         {stats.created}"
    )

    if stats.created_by_category:

        print()
        print(
            "CREATED BY CATEGORY"
        )

        for category in sorted(
            stats.created_by_category
        ):

            print(
                f"  {category:<22} "
                f"{stats.created_by_category[category]}"
            )

    if stats.created_names:

        separator("NEW CORE SKILLS")

        for name in stats.created_names:
            print(
                f"  + {name}"
            )

    if stats.normalized_conflicts:

        separator("NORMALIZED MATCHES - REVIEW")

        print(
            "These proposed skills were NOT created because an "
            "existing skill normalized to the same name."
        )
        print()

        for conflict in stats.normalized_conflicts:
            print(
                f"  {conflict}"
            )


# =============================================================================
# RUNNER
# =============================================================================


def run(
    db: Session,
    apply_changes: bool,
) -> None:

    separator(
        "COLLABVERSE CORE MULTIDISCIPLINARY SKILL CATALOG"
    )

    if apply_changes:

        print(
            "MODE: APPLY"
        )

        print()
        print(
            "New core skills will be committed if all validation passes."
        )

    else:

        print(
            "MODE: DRY RUN"
        )

        print()
        print(
            "New core skills will be simulated and rolled back."
        )

    validate_core_configuration()

    before_count = db.query(
        Skill
    ).count()

    print()
    print(
        f"Current catalog size: {before_count}"
    )

    if before_count != 202:

        print()
        print(
            "WARNING:"
        )

        print(
            f"The cleaned catalog was expected to contain 202 skills, "
            f"but the database currently contains {before_count}."
        )

        print(
            "The seeder will continue safely, but review the output."
        )

    stats = SeedStats()

    seed_core_skills(
        db,
        stats,
    )

    db.flush()

    after_count = validate_seed_result(
        db,
        stats,
        before_count,
    )

    print_summary(
        stats
    )

    # =========================================================================
    # COMMIT / ROLLBACK
    # =========================================================================

    if apply_changes:

        separator("COMMIT")

        db.commit()

        print(
            "SUCCESS: core multidisciplinary skill catalog committed."
        )

        print()
        print(
            f"Final catalog size: {after_count}"
        )

    else:

        separator("DRY RUN COMPLETE")

        db.rollback()

        print(
            "SUCCESS: core skill seeding completed successfully "
            "inside the transaction."
        )

        print()
        print(
            "The transaction has been rolled back."
        )

        print(
            "NO DATABASE CHANGES WERE SAVED."
        )

        print()
        print(
            "Do NOT run --apply until the dry-run output has been reviewed."
        )


# =============================================================================
# CLI
# =============================================================================


def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Seed the COLLABVERSE core multidisciplinary skill catalog."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Commit new core skills. "
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

        separator("CORE SKILL SEED FAILED")

        print(
            "The transaction was rolled back."
        )

        print(
            "NO PARTIAL CORE-SKILL CHANGES WERE COMMITTED."
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
            "NO PARTIAL CORE-SKILL CHANGES WERE COMMITTED."
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