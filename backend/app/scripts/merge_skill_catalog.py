"""
COLLABVERSE - Safe Skill Catalog Cleanup

Purpose
-------
Safely canonicalize known duplicate/legacy skills while preserving
all references throughout the database.

DEFAULT BEHAVIOR:
    DRY RUN

Nothing is committed unless --apply is explicitly supplied.

Usage
-----
Dry run:
    python -m app.scripts.merge_skill_catalog

Apply:
    python -m app.scripts.merge_skill_catalog --apply

The script currently performs:

RENAMES
-------
Artificial Intelligence (AI) -> Artificial Intelligence
Natural Language Processing (NLP) -> Natural Language Processing

MERGES
------
Communication Skills -> Communication
Collaboration Skills -> Collaboration
Git Version Control -> Git
User Interface (UI) Design -> UI Design
User Experience (UX) Design -> UX Design
Time Management Techniques -> Time Management
"""

from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.skill import Skill


# =============================================================================
# CONFIGURATION
# =============================================================================


RENAMES: dict[str, str] = {
    "Artificial Intelligence (AI)": "Artificial Intelligence",
    "Natural Language Processing (NLP)": "Natural Language Processing",
}


MERGES: dict[str, str] = {
    "Communication Skills": "Communication",
    "Collaboration Skills": "Collaboration",
    "Git Version Control": "Git",
    "User Interface (UI) Design": "UI Design",
    "User Experience (UX) Design": "UX Design",
    "Time Management Techniques": "Time Management",
}


# Tables that need special handling.
SPECIAL_TABLES = {
    "skill_relations",
    "skills",
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class ForeignKeyReference:
    schema: str
    table: str
    column: str
    constraint_name: str


@dataclass
class MergeStats:
    source_name: str
    target_name: str

    source_id: uuid.UUID | None = None
    target_id: uuid.UUID | None = None

    references_found: int = 0
    references_updated: int = 0
    collisions_removed: int = 0

    relations_updated: int = 0
    relations_removed: int = 0

    children_reparented: int = 0

    source_deleted: bool = False


# =============================================================================
# DISPLAY HELPERS
# =============================================================================


def separator(title: str | None = None) -> None:
    print()
    print("=" * 88)

    if title:
        print(title)
        print("=" * 88)


def print_mode(apply_changes: bool) -> None:
    separator("COLLABVERSE SKILL CATALOG SAFE MERGE")

    if apply_changes:
        print("MODE: APPLY")
        print()
        print("WARNING: Changes will be committed if all checks pass.")
    else:
        print("MODE: DRY RUN")
        print()
        print("No database changes will be committed.")


# =============================================================================
# DATABASE INTROSPECTION
# =============================================================================


def discover_skill_foreign_keys(db: Session) -> list[ForeignKeyReference]:
    """
    Discover every FK in PostgreSQL referencing skills.id.

    This avoids hardcoding all dependent tables.
    """

    sql = text(
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

    rows = db.execute(sql).mappings().all()

    return [
        ForeignKeyReference(
            schema=row["table_schema"],
            table=row["table_name"],
            column=row["column_name"],
            constraint_name=row["constraint_name"],
        )
        for row in rows
    ]


def get_primary_key_columns(
    db: Session,
    schema: str,
    table: str,
) -> list[str]:
    """
    Get primary-key columns for a table.
    """

    inspector = inspect(db.bind)

    pk = inspector.get_pk_constraint(
        table_name=table,
        schema=schema,
    )

    return list(pk.get("constrained_columns") or [])


def get_unique_constraints(
    db: Session,
    schema: str,
    table: str,
) -> list[list[str]]:
    """
    Return UNIQUE constraints/indexes for a table.

    PostgreSQL/SQLAlchemy can expose uniqueness either through explicit
    constraints or unique indexes, so we inspect both.
    """

    inspector = inspect(db.bind)

    unique_sets: list[list[str]] = []

    for constraint in inspector.get_unique_constraints(
        table_name=table,
        schema=schema,
    ):
        columns = constraint.get("column_names") or []

        if columns:
            unique_sets.append(list(columns))

    for index in inspector.get_indexes(
        table_name=table,
        schema=schema,
    ):
        if not index.get("unique"):
            continue

        columns = index.get("column_names") or []

        if columns and list(columns) not in unique_sets:
            unique_sets.append(list(columns))

    return unique_sets


def quote_identifier(name: str) -> str:
    """
    Quote PostgreSQL identifiers safely.

    Names come from database metadata, not user input.
    """

    return '"' + name.replace('"', '""') + '"'


def qualified_table(schema: str, table: str) -> str:
    return f"{quote_identifier(schema)}.{quote_identifier(table)}"


# =============================================================================
# SKILL LOOKUPS
# =============================================================================


def get_skill(db: Session, name: str) -> Skill | None:
    return (
        db.query(Skill)
        .filter(Skill.name == name)
        .one_or_none()
    )


def count_skills(db: Session) -> int:
    return db.query(Skill).count()


def count_references(
    db: Session,
    fk: ForeignKeyReference,
    skill_id: uuid.UUID,
) -> int:
    table_name = qualified_table(fk.schema, fk.table)
    column_name = quote_identifier(fk.column)

    sql = text(
        f"""
        SELECT COUNT(*)
        FROM {table_name}
        WHERE {column_name} = :skill_id
        """
    )

    return int(
        db.execute(
            sql,
            {"skill_id": skill_id},
        ).scalar_one()
    )


# =============================================================================
# GENERIC ASSOCIATION MERGE
# =============================================================================


def find_relevant_unique_sets(
    db: Session,
    fk: ForeignKeyReference,
) -> list[list[str]]:
    """
    Find UNIQUE/PK column groups containing the skill FK.

    Example:

        hackathon_skills
        UNIQUE(hackathon_id, skill_id)

    Updating:

        duplicate_skill -> canonical_skill

    may collide if the hackathon already has canonical_skill.

    This function tells us which uniqueness groups must be checked.
    """

    unique_sets = get_unique_constraints(
        db,
        fk.schema,
        fk.table,
    )

    pk_columns = get_primary_key_columns(
        db,
        fk.schema,
        fk.table,
    )

    if pk_columns and pk_columns not in unique_sets:
        unique_sets.append(pk_columns)

    return [
        columns
        for columns in unique_sets
        if fk.column in columns and len(columns) > 1
    ]


def find_collision_row_ids(
    db: Session,
    fk: ForeignKeyReference,
    source_id: uuid.UUID,
    target_id: uuid.UUID,
) -> list[Any]:
    """
    Find source rows that would violate a UNIQUE constraint after
    changing source_id -> target_id.

    We return PostgreSQL ctid values for source rows.

    ctid is used only inside this transaction to identify exact rows.
    """

    table_name = qualified_table(fk.schema, fk.table)
    skill_column = quote_identifier(fk.column)

    relevant_unique_sets = find_relevant_unique_sets(db, fk)

    collision_ctids: set[Any] = set()

    for unique_columns in relevant_unique_sets:
        other_columns = [
            column
            for column in unique_columns
            if column != fk.column
        ]

        if not other_columns:
            continue

        equality_conditions = []

        for column in other_columns:
            qcol = quote_identifier(column)

            # IS NOT DISTINCT FROM safely handles NULL equality.
            equality_conditions.append(
                f"target.{qcol} IS NOT DISTINCT FROM source.{qcol}"
            )

        conditions = "\nAND ".join(equality_conditions)

        sql = text(
            f"""
            SELECT source.ctid::text
            FROM {table_name} AS source
            WHERE source.{skill_column} = :source_id
              AND EXISTS (
                    SELECT 1
                    FROM {table_name} AS target
                    WHERE target.{skill_column} = :target_id
                      AND {conditions}
              )
            """
        )

        rows = db.execute(
            sql,
            {
                "source_id": source_id,
                "target_id": target_id,
            },
        ).scalars().all()

        collision_ctids.update(rows)

    return list(collision_ctids)


def delete_rows_by_ctid(
    db: Session,
    schema: str,
    table: str,
    ctids: list[Any],
) -> int:
    """
    Delete exact rows identified by PostgreSQL ctid.
    """

    if not ctids:
        return 0

    table_name = qualified_table(schema, table)

    deleted = 0

    for row_ctid in ctids:
        sql = text(
            f"""
            DELETE FROM {table_name}
            WHERE ctid = CAST(:row_ctid AS tid)
            """
        )

        result = db.execute(
            sql,
            {"row_ctid": row_ctid},
        )

        deleted += result.rowcount or 0

    return deleted


def merge_generic_fk(
    db: Session,
    fk: ForeignKeyReference,
    source_id: uuid.UUID,
    target_id: uuid.UUID,
    stats: MergeStats,
) -> None:
    """
    Safely transfer references from source skill to target skill.

    If updating would cause a UNIQUE collision:
        duplicate association row is deleted first.

    Remaining rows are then updated.
    """

    table_name = qualified_table(fk.schema, fk.table)
    column_name = quote_identifier(fk.column)

    source_count = count_references(
        db,
        fk,
        source_id,
    )

    if source_count == 0:
        return

    stats.references_found += source_count

    print(
        f"    {fk.schema}.{fk.table}.{fk.column}: "
        f"{source_count} reference(s)"
    )

    collision_ctids = find_collision_row_ids(
        db,
        fk,
        source_id,
        target_id,
    )

    if collision_ctids:
        removed = delete_rows_by_ctid(
            db,
            fk.schema,
            fk.table,
            collision_ctids,
        )

        stats.collisions_removed += removed

        print(
            f"      collision rows removed: {removed}"
        )

    sql = text(
        f"""
        UPDATE {table_name}
        SET {column_name} = :target_id
        WHERE {column_name} = :source_id
        """
    )

    result = db.execute(
        sql,
        {
            "source_id": source_id,
            "target_id": target_id,
        },
    )

    updated = result.rowcount or 0

    stats.references_updated += updated

    print(
        f"      references updated: {updated}"
    )


# =============================================================================
# PARENT / CHILD HANDLING
# =============================================================================


def handle_skill_parent_references(
    db: Session,
    source_id: uuid.UUID,
    target_id: uuid.UUID,
    stats: MergeStats,
) -> None:
    """
    Reparent children of the duplicate skill to the canonical skill.

    Prevent:
        target -> source -> target
        target -> target
    """

    # If canonical target currently points to the duplicate source,
    # clear it before reparenting.
    sql = text(
        """
        UPDATE skills
        SET parent_skill_id = NULL
        WHERE id = :target_id
          AND parent_skill_id = :source_id
        """
    )

    result = db.execute(
        sql,
        {
            "target_id": target_id,
            "source_id": source_id,
        },
    )

    if result.rowcount:
        print(
            "    Cleared canonical skill parent because it pointed "
            "to the duplicate."
        )

    # Reparent children, except target itself.
    sql = text(
        """
        UPDATE skills
        SET parent_skill_id = :target_id
        WHERE parent_skill_id = :source_id
          AND id <> :target_id
        """
    )

    result = db.execute(
        sql,
        {
            "target_id": target_id,
            "source_id": source_id,
        },
    )

    changed = result.rowcount or 0

    stats.children_reparented += changed

    if changed:
        print(
            f"    Child skills reparented: {changed}"
        )

    # Absolute safety: canonical cannot parent itself.
    db.execute(
        text(
            """
            UPDATE skills
            SET parent_skill_id = NULL
            WHERE id = :target_id
              AND parent_skill_id = :target_id
            """
        ),
        {"target_id": target_id},
    )


# =============================================================================
# SKILL RELATIONS
# =============================================================================


def fetch_skill_relations(
    db: Session,
    skill_id: uuid.UUID,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    rows = db.execute(
        text(
            """
            SELECT skill_id, related_skill_id
            FROM skill_relations
            WHERE skill_id = :skill_id
               OR related_skill_id = :skill_id
            """
        ),
        {"skill_id": skill_id},
    ).all()

    return [
        (row[0], row[1])
        for row in rows
    ]


def relation_exists(
    db: Session,
    skill_id: uuid.UUID,
    related_skill_id: uuid.UUID,
) -> bool:
    return (
        db.execute(
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
        is not None
    )


def handle_skill_relations(
    db: Session,
    source_id: uuid.UUID,
    target_id: uuid.UUID,
    stats: MergeStats,
) -> None:
    """
    Preserve all useful relation edges belonging to source.

    Example:

        source -> Python

    becomes:

        target -> Python

    Likewise:

        Python -> source

    becomes:

        Python -> target

    Duplicate edges are ignored.

    Self edges are never created.
    """

    relations = fetch_skill_relations(
        db,
        source_id,
    )

    if not relations:
        return

    print(
        f"    skill_relations touching duplicate: {len(relations)}"
    )

    desired_relations: set[tuple[uuid.UUID, uuid.UUID]] = set()

    for left_id, right_id in relations:
        new_left = (
            target_id
            if left_id == source_id
            else left_id
        )

        new_right = (
            target_id
            if right_id == source_id
            else right_id
        )

        # Never create self relation.
        if new_left == new_right:
            stats.relations_removed += 1
            continue

        desired_relations.add(
            (new_left, new_right)
        )

    # Remove all old source relations first.
    result = db.execute(
        text(
            """
            DELETE FROM skill_relations
            WHERE skill_id = :source_id
               OR related_skill_id = :source_id
            """
        ),
        {"source_id": source_id},
    )

    removed = result.rowcount or 0

    stats.relations_removed += removed

    # Recreate transformed relations where they do not already exist.
    inserted = 0

    for left_id, right_id in desired_relations:
        if relation_exists(
            db,
            left_id,
            right_id,
        ):
            continue

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
                "skill_id": left_id,
                "related_skill_id": right_id,
            },
        )

        inserted += 1

    stats.relations_updated += inserted

    print(
        f"      old relation rows removed: {removed}"
    )

    print(
        f"      transformed relation rows inserted: {inserted}"
    )


# =============================================================================
# VALIDATION
# =============================================================================


def count_all_references_to_skill(
    db: Session,
    skill_id: uuid.UUID,
    foreign_keys: list[ForeignKeyReference],
) -> dict[str, int]:
    result: dict[str, int] = {}

    for fk in foreign_keys:
        count = count_references(
            db,
            fk,
            skill_id,
        )

        if count:
            key = (
                f"{fk.schema}."
                f"{fk.table}."
                f"{fk.column}"
            )

            result[key] = count

    return result


def verify_no_source_references(
    db: Session,
    source_id: uuid.UUID,
    foreign_keys: list[ForeignKeyReference],
) -> None:
    remaining = count_all_references_to_skill(
        db,
        source_id,
        foreign_keys,
    )

    if remaining:
        lines = [
            "References still point to duplicate skill:"
        ]

        for location, count in remaining.items():
            lines.append(
                f"  {location}: {count}"
            )

        raise RuntimeError(
            "\n".join(lines)
        )


def verify_no_self_relations(db: Session) -> None:
    count = int(
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

    if count:
        raise RuntimeError(
            f"{count} self-referencing skill relation(s) exist."
        )


def verify_no_self_parent(db: Session) -> None:
    count = int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM skills
                WHERE id = parent_skill_id
                """
            )
        ).scalar_one()
    )

    if count:
        raise RuntimeError(
            f"{count} self-parenting skill(s) exist."
        )


# =============================================================================
# RENAMES
# =============================================================================


def perform_renames(db: Session) -> None:
    separator("CANONICAL RENAMES")

    for old_name, new_name in RENAMES.items():
        old_skill = get_skill(
            db,
            old_name,
        )

        new_skill = get_skill(
            db,
            new_name,
        )

        if old_skill is None:
            print(
                f"SKIP: '{old_name}' does not exist."
            )
            continue

        if new_skill is not None:
            raise RuntimeError(
                f"Cannot rename '{old_name}' -> '{new_name}' "
                f"because '{new_name}' already exists. "
                f"This now requires a merge instead."
            )

        print(
            f"RENAME: {old_name}"
        )
        print(
            f"     -> {new_name}"
        )
        print(
            f"     ID preserved: {old_skill.id}"
        )

        old_skill.name = new_name

        db.flush()


# =============================================================================
# MERGES
# =============================================================================


def perform_merge(
    db: Session,
    source_name: str,
    target_name: str,
    foreign_keys: list[ForeignKeyReference],
) -> MergeStats:
    source = get_skill(
        db,
        source_name,
    )

    target = get_skill(
        db,
        target_name,
    )

    stats = MergeStats(
        source_name=source_name,
        target_name=target_name,
    )

    if source is None:
        print(
            f"SKIP: duplicate '{source_name}' does not exist."
        )
        return stats

    if target is None:
        raise RuntimeError(
            f"Canonical skill '{target_name}' does not exist. "
            f"Cannot merge '{source_name}'."
        )

    if source.id == target.id:
        raise RuntimeError(
            f"Source and target have the same UUID for "
            f"'{source_name}' -> '{target_name}'."
        )

    stats.source_id = source.id
    stats.target_id = target.id

    print()
    print(
        f"MERGE: {source.name}"
    )
    print(
        f"   ->  {target.name}"
    )
    print(
        f"Source ID: {source.id}"
    )
    print(
        f"Target ID: {target.id}"
    )

    # -------------------------------------------------------------------------
    # 1. Skill hierarchy
    # -------------------------------------------------------------------------

    handle_skill_parent_references(
        db,
        source.id,
        target.id,
        stats,
    )

    # -------------------------------------------------------------------------
    # 2. Related-skill graph
    # -------------------------------------------------------------------------

    handle_skill_relations(
        db,
        source.id,
        target.id,
        stats,
    )

    # -------------------------------------------------------------------------
    # 3. Every other FK reference
    # -------------------------------------------------------------------------

    for fk in foreign_keys:
        if fk.table == "skill_relations":
            continue

        if (
            fk.table == "skills"
            and fk.column == "parent_skill_id"
        ):
            continue

        merge_generic_fk(
            db,
            fk,
            source.id,
            target.id,
            stats,
        )

    db.flush()

    # -------------------------------------------------------------------------
    # 4. Verify source is no longer referenced
    # -------------------------------------------------------------------------

    verify_no_source_references(
        db,
        source.id,
        foreign_keys,
    )

    # -------------------------------------------------------------------------
    # 5. Delete duplicate skill
    # -------------------------------------------------------------------------

    db.delete(source)

    db.flush()

    stats.source_deleted = True

    print(
        f"    Duplicate skill deleted: {source_name}"
    )

    return stats


# =============================================================================
# REPORTING
# =============================================================================


def print_fk_report(
    foreign_keys: list[ForeignKeyReference],
) -> None:
    separator("DISCOVERED DATABASE REFERENCES")

    print(
        f"Foreign keys referencing skills.id: "
        f"{len(foreign_keys)}"
    )

    print()

    for fk in foreign_keys:
        print(
            f"  {fk.schema}.{fk.table}.{fk.column}"
            f" [{fk.constraint_name}]"
        )


def print_merge_summary(
    stats_list: list[MergeStats],
) -> None:
    separator("MERGE SUMMARY")

    for stats in stats_list:
        print(
            f"{stats.source_name} -> {stats.target_name}"
        )

        if stats.source_id is None:
            print("  skipped")
            print()
            continue

        print(
            f"  source ID:            {stats.source_id}"
        )
        print(
            f"  target ID:            {stats.target_id}"
        )
        print(
            f"  references found:     {stats.references_found}"
        )
        print(
            f"  references updated:   {stats.references_updated}"
        )
        print(
            f"  collisions removed:   {stats.collisions_removed}"
        )
        print(
            f"  children reparented:  {stats.children_reparented}"
        )
        print(
            f"  relations inserted:   {stats.relations_updated}"
        )
        print(
            f"  relation rows removed:{stats.relations_removed}"
        )
        print(
            f"  source deleted:       {stats.source_deleted}"
        )
        print()


# =============================================================================
# MAIN CLEANUP
# =============================================================================


def run_cleanup(
    db: Session,
    apply_changes: bool,
) -> None:
    print_mode(apply_changes)

    before_count = count_skills(db)

    print()
    print(
        f"Skills before cleanup: {before_count}"
    )

    foreign_keys = discover_skill_foreign_keys(db)

    print_fk_report(
        foreign_keys
    )

    # We expect the audit to have found 12.
    # Do not hard-fail if the schema legitimately changes,
    # but make the difference very visible.
    if len(foreign_keys) != 12:
        print()
        print(
            "WARNING:"
        )
        print(
            f"Audit previously found 12 skill FK references, "
            f"but the database currently reports {len(foreign_keys)}."
        )
        print(
            "Review the discovered reference list carefully."
        )

    # -------------------------------------------------------------------------
    # Renames
    # -------------------------------------------------------------------------

    perform_renames(db)

    # -------------------------------------------------------------------------
    # Merges
    # -------------------------------------------------------------------------

    separator("SAFE DUPLICATE MERGES")

    stats_list: list[MergeStats] = []

    for source_name, target_name in MERGES.items():
        stats = perform_merge(
            db,
            source_name,
            target_name,
            foreign_keys,
        )

        stats_list.append(stats)

    # -------------------------------------------------------------------------
    # Global validation
    # -------------------------------------------------------------------------

    separator("VALIDATION")

    verify_no_self_relations(db)
    print(
        "PASS: no self-referencing skill relations."
    )

    verify_no_self_parent(db)
    print(
        "PASS: no self-parenting skills."
    )

    # Ensure removed source names are absent.
    for source_name in MERGES:
        remaining = get_skill(
            db,
            source_name,
        )

        if remaining is not None:
            raise RuntimeError(
                f"Duplicate skill still exists: {source_name}"
            )

    print(
        "PASS: merged duplicate skill names are gone."
    )

    # Ensure rename sources are absent and targets exist.
    for old_name, new_name in RENAMES.items():
        old_skill = get_skill(
            db,
            old_name,
        )

        new_skill = get_skill(
            db,
            new_name,
        )

        if old_skill is not None:
            raise RuntimeError(
                f"Old renamed skill still exists: {old_name}"
            )

        if new_skill is None:
            raise RuntimeError(
                f"Canonical renamed skill missing: {new_name}"
            )

    print(
        "PASS: canonical renames are valid."
    )

    after_count = count_skills(db)

    expected_removed = sum(
        1
        for stats in stats_list
        if stats.source_deleted
    )

    expected_after = (
        before_count
        - expected_removed
    )

    print()
    print(
        f"Skills before:   {before_count}"
    )
    print(
        f"Skills after:    {after_count}"
    )
    print(
        f"Expected after:  {expected_after}"
    )

    if after_count != expected_after:
        raise RuntimeError(
            "Unexpected skill count after cleanup."
        )

    print(
        "PASS: skill count is correct."
    )

    print_merge_summary(
        stats_list
    )

    # -------------------------------------------------------------------------
    # Commit / rollback
    # -------------------------------------------------------------------------

    if apply_changes:
        separator("COMMIT")

        db.commit()

        print(
            "SUCCESS: skill catalog cleanup committed."
        )

        print()
        print(
            f"Final skill count: {after_count}"
        )

    else:
        separator("DRY RUN COMPLETE")

        db.rollback()

        print(
            "SUCCESS: all cleanup operations and validations "
            "completed inside the transaction."
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
            "If this output looks correct, run:"
        )
        print()
        print(
            "python -m app.scripts.merge_skill_catalog --apply"
        )


# =============================================================================
# ENTRY POINT
# =============================================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Safely canonicalize the COLLABVERSE skill catalog."
        )
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Commit cleanup changes. "
            "Without this flag the script performs a dry run."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    db = SessionLocal()

    try:
        run_cleanup(
            db=db,
            apply_changes=args.apply,
        )

    except (SQLAlchemyError, RuntimeError, ValueError) as exc:
        db.rollback()

        separator("CLEANUP FAILED")

        print(
            "The transaction was rolled back."
        )
        print(
            "NO PARTIAL CLEANUP WAS COMMITTED."
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
            "NO PARTIAL CLEANUP WAS COMMITTED."
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