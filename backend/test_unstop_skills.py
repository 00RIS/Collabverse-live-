from app.db.session import SessionLocal
from app.modules.hackathons.collectors.unstop import unstop_collector
from app.modules.hackathons.skill_resolver import skill_resolver


def main():
    db = SessionLocal()

    try:
        payload = unstop_collector.fetch_raw(
            page=1,
            per_page=18,
        )

        items = unstop_collector._extract_items(payload)

        print()
        print("=" * 80)
        print(f"HACKATHONS FETCHED: {len(items)}")
        print("=" * 80)

        for index, item in enumerate(items, start=1):

            title = item.get(
                "title",
                "Unknown",
            )

            skill_names = (
                unstop_collector.get_required_skill_names(
                    item
                )
            )

            print()
            print("-" * 80)
            print(f"{index}. {title}")
            print("-" * 80)

            if not skill_names:
                print("No required skills provided by Unstop.")
                continue

            print(
                "Unstop skills:",
                skill_names,
            )

            resolutions = (
                skill_resolver.resolve_many(
                    db,
                    skill_names,
                    allow_create=True,
                )
            )

            print()
            print("RESOLUTION:")

            for result in resolutions:

                if result.skill is None:
                    print(
                        f"  {result.source_name}"
                        f" -> UNRESOLVED"
                        f" [{result.match_type}]"
                        f" confidence={result.confidence}"
                    )

                    continue

                category = (
                    result.skill.category.value
                    if result.skill.category
                    else "None"
                )

                print(
                    f"  {result.source_name}"
                    f" -> {result.skill.name}"
                    f" [{result.match_type}]"
                    f" confidence={result.confidence}"
                    f" category={category}"
                )

    except Exception as exc:
        print()
        print("=" * 80)
        print("TEST FAILED")
        print("=" * 80)

        print(
            f"{type(exc).__name__}: {exc}"
        )

        raise

    finally:
        # IMPORTANT:
        # Any skills created by allow_create=True
        # during this test are rolled back.
        db.rollback()
        db.close()

        print()
        print("=" * 80)
        print(
            "TEST FINISHED - DATABASE ROLLED BACK"
        )
        print("=" * 80)


if __name__ == "__main__":
    main()