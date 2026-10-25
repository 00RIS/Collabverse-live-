"""
app/scripts/audit_skill_catalog.py

READ-ONLY audit of the CollabVerse Skill Catalog.

This script:

1. Lists all skills.
2. Finds normalized duplicate candidates.
3. Finds known canonical duplicate groups.
4. Finds suspicious high-similarity names.
5. Discovers every PostgreSQL foreign key referencing skills.id.
6. Counts references to each duplicate candidate.
7. Makes NO database changes.

Run:

    python -m app.scripts.audit_skill_catalog
"""

import re
from collections import defaultdict
from difflib import SequenceMatcher

from sqlalchemy import inspect, select, text

from app.db.session import SessionLocal
from app.models.skill import Skill


# ============================================================
# CONFIRMED / HIGH-CONFIDENCE CANONICAL GROUPS
# ============================================================

CANONICAL_GROUPS = {
    "Artificial Intelligence": [
        "Artificial Intelligence",
        "Artificial Intelligence (AI)",
        "AI",
    ],

    "Natural Language Processing": [
        "Natural Language Processing",
        "Natural Language Processing (NLP)",
        "NLP",
    ],

    "Communication": [
        "Communication",
        "Communication Skills",
    ],

    "Collaboration": [
        "Collaboration",
        "Collaboration Skills",
    ],

    "Git": [
        "Git",
        "Git Version Control",
    ],

    "UI Design": [
        "UI Design",
        "User Interface (UI) Design",
    ],

    "UX Design": [
        "UX Design",
        "User Experience (UX) Design",
    ],

    "Time Management": [
        "Time Management",
        "Time Management Techniques",
    ],
}


# ============================================================
# NORMALIZATION
# ============================================================


def normalize_name(name: str) -> str:
    """
    Syntactic normalization only.

    This function intentionally does NOT perform semantic merging.
    """

    if not name:
        return ""

    value = name.strip().casefold()

    value = value.replace("&", " and ")

    value = re.sub(
        r"[\(\)\[\]\{\}]",
        " ",
        value,
    )

    value = re.sub(
        r"[/_,:;|]+",
        " ",
        value,
    )

    value = re.sub(
        r"[-]+",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# ============================================================
# FOREIGN KEY DISCOVERY
# ============================================================


def discover_skill_foreign_keys(db):
    """
    Ask PostgreSQL which columns reference skills.id.

    This is safer than maintaining a hard-coded list because future
    modules may add new skill references.
    """

    query = text(
        """
        SELECT
            tc.table_schema,
            tc.table_name,
            kcu.column_name,
            tc.constraint_name
        FROM information_schema.table_constraints AS tc

        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema

        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema

        WHERE
            tc.constraint_type = 'FOREIGN KEY'
            AND ccu.table_name = 'skills'
            AND ccu.column_name = 'id'

        ORDER BY
            tc.table_schema,
            tc.table_name,
            kcu.column_name
        """
    )

    rows = db.execute(query).mappings().all()

    return [
        {
            "schema": row["table_schema"],
            "table": row["table_name"],
            "column": row["column_name"],
            "constraint": row["constraint_name"],
        }
        for row in rows
    ]


# ============================================================
# REFERENCE COUNTS
# ============================================================


def count_references(
    db,
    foreign_keys,
    skill_id,
):
    """
    Count how many rows across the database reference a Skill.
    """

    results = {}

    for fk in foreign_keys:

        schema = fk["schema"]
        table = fk["table"]
        column = fk["column"]

        # Table/column names originate from PostgreSQL metadata,
        # not user input.
        query = text(
            f'''
            SELECT COUNT(*)
            FROM "{schema}"."{table}"
            WHERE "{column}" = :skill_id
            '''
        )

        count = db.execute(
            query,
            {
                "skill_id": skill_id,
            },
        ).scalar_one()

        if count:
            results[
                f"{schema}.{table}.{column}"
            ] = count

    return results


# ============================================================
# NORMALIZED DUPLICATES
# ============================================================


def find_normalized_duplicates(skills):
    groups = defaultdict(list)

    for skill in skills:

        normalized = normalize_name(
            skill.name
        )

        groups[normalized].append(
            skill
        )

    return {
        normalized: group
        for normalized, group
        in groups.items()
        if len(group) > 1
    }


# ============================================================
# CANONICAL GROUPS
# ============================================================


def find_canonical_groups(skills):
    by_casefold = {
        skill.name.strip().casefold(): skill
        for skill in skills
    }

    results = []

    for (
        canonical_name,
        variants,
    ) in CANONICAL_GROUPS.items():

        existing = []

        for variant in variants:

            skill = by_casefold.get(
                variant.casefold()
            )

            if skill:
                existing.append(skill)

        if existing:

            results.append(
                {
                    "canonical_name": canonical_name,
                    "skills": existing,
                }
            )

    return results


# ============================================================
# SIMILARITY AUDIT
# ============================================================


def find_similar_skills(
    skills,
    threshold=0.86,
):
    """
    Find suspiciously similar names for HUMAN REVIEW.

    These are NOT automatically considered duplicates.
    """

    results = []

    for index, skill_a in enumerate(skills):

        name_a = normalize_name(
            skill_a.name
        )

        for skill_b in skills[
            index + 1:
        ]:

            name_b = normalize_name(
                skill_b.name
            )

            if not name_a or not name_b:
                continue

            score = SequenceMatcher(
                None,
                name_a,
                name_b,
            ).ratio()

            if score < threshold:
                continue

            results.append(
                (
                    score,
                    skill_a,
                    skill_b,
                )
            )

    results.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return results


# ============================================================
# PRINT HELPERS
# ============================================================


def print_separator():
    print(
        "\n"
        + "=" * 80
    )


def print_skill(
    skill,
    reference_counts=None,
):
    print(
        f"  NAME:     {skill.name}"
    )

    print(
        f"  ID:       {skill.id}"
    )

    print(
        f"  CATEGORY: {skill.category.value}"
    )

    if reference_counts is not None:

        total = sum(
            reference_counts.values()
        )

        print(
            f"  REFERENCES: {total}"
        )

        for (
            location,
            count,
        ) in reference_counts.items():

            print(
                f"      {location}: {count}"
            )


# ============================================================
# MAIN AUDIT
# ============================================================


def main():
    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # LOAD CATALOG
        # ----------------------------------------------------

        skills = list(
            db.scalars(
                select(Skill)
                .order_by(Skill.name)
            ).all()
        )

        print_separator()

        print(
            "COLLABVERSE SKILL CATALOG AUDIT"
        )

        print_separator()

        print(
            f"\nTOTAL SKILLS: {len(skills)}"
        )

        # ----------------------------------------------------
        # CATEGORY COUNTS
        # ----------------------------------------------------

        category_counts = defaultdict(int)

        for skill in skills:

            category_counts[
                skill.category.value
            ] += 1

        print(
            "\nSKILLS BY CATEGORY:"
        )

        for (
            category,
            count,
        ) in sorted(
            category_counts.items()
        ):

            print(
                f"  {category:20} {count}"
            )

        # ----------------------------------------------------
        # DISCOVER FOREIGN KEYS
        # ----------------------------------------------------

        foreign_keys = (
            discover_skill_foreign_keys(
                db
            )
        )

        print_separator()

        print(
            "DATABASE REFERENCES TO skills.id"
        )

        print_separator()

        print(
            f"\nFOREIGN KEYS FOUND: "
            f"{len(foreign_keys)}\n"
        )

        for fk in foreign_keys:

            print(
                "  "
                f"{fk['schema']}."
                f"{fk['table']}."
                f"{fk['column']}"
                "  "
                f"[{fk['constraint']}]"
            )

        # ----------------------------------------------------
        # NORMALIZED DUPLICATES
        # ----------------------------------------------------

        normalized_duplicates = (
            find_normalized_duplicates(
                skills
            )
        )

        print_separator()

        print(
            "EXACT NORMALIZED DUPLICATES"
        )

        print_separator()

        if not normalized_duplicates:

            print(
                "\nNone found."
            )

        else:

            for (
                normalized,
                group,
            ) in normalized_duplicates.items():

                print(
                    f"\nNORMALIZED: {normalized}"
                )

                for skill in group:

                    refs = count_references(
                        db,
                        foreign_keys,
                        skill.id,
                    )

                    print_skill(
                        skill,
                        refs,
                    )

                    print()

        # ----------------------------------------------------
        # KNOWN CANONICAL GROUPS
        # ----------------------------------------------------

        canonical_groups = (
            find_canonical_groups(
                skills
            )
        )

        print_separator()

        print(
            "KNOWN CANONICALIZATION GROUPS"
        )

        print_separator()

        for group in canonical_groups:

            canonical_name = (
                group["canonical_name"]
            )

            existing_skills = (
                group["skills"]
            )

            print(
                f"\nCANONICAL TARGET: "
                f"{canonical_name}"
            )

            print(
                f"EXISTING VARIANTS: "
                f"{len(existing_skills)}"
            )

            for skill in existing_skills:

                refs = count_references(
                    db,
                    foreign_keys,
                    skill.id,
                )

                print_skill(
                    skill,
                    refs,
                )

                print()

        # ----------------------------------------------------
        # HIGH SIMILARITY
        # ----------------------------------------------------

        similar = find_similar_skills(
            skills
        )

        print_separator()

        print(
            "SIMILAR SKILL NAMES - HUMAN REVIEW"
        )

        print_separator()

        print(
            "\nThese are NOT automatically duplicates.\n"
        )

        for (
            score,
            skill_a,
            skill_b,
        ) in similar:

            print(
                f"{score:.3f} | "
                f"{skill_a.name}"
                f"  <->  "
                f"{skill_b.name}"
            )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        print_separator()

        print(
            "AUDIT COMPLETE"
        )

        print_separator()

        print(
            "\nNO DATABASE CHANGES WERE MADE."
        )

        print(
            "\nNext step:"
        )

        print(
            "Review the canonical groups and similarity "
            "candidates before any merge operation."
        )

    finally:

        db.close()


if __name__ == "__main__":
    main()