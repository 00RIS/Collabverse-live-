import uuid

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User

from app.modules.hackathons.models import (
    Hackathon,
    HackathonParticipant,
    HackathonParticipantStatus,
    HackathonSkill,
    HackathonSourceType,
)

from app.modules.hackathons.repositories import (
    HackathonRepository,
)

from app.modules.hackathons.schemas import (
    ExternalHackathonCreate,
    HackathonCreate,
    HackathonParticipantCreate,
    HackathonSkillCreate,
    HackathonUpdate,
)

from app.modules.hackathons.collectors.unstop import (
    unstop_collector,
)

from app.modules.hackathons.skill_resolver import (
    skill_resolver,
)


class HackathonService:

    # =====================================================
    # RESOLVE EXTERNAL SKILLS
    # =====================================================

    def _resolve_external_skills(
        self,
        db: Session,
        skill_names: list[str],
    ) -> list[HackathonSkillCreate]:
        """
        Convert external skill names into CollabVerse
        Skill UUID relationships.

        Flow:

        external skill name
            ->
        SkillResolver
            ->
        existing / safely-created Skill
            ->
        HackathonSkillCreate

        Unresolved skills are intentionally skipped.
        We prefer skipping an ambiguous skill over
        creating an incorrect taxonomy entry.
        """

        if not skill_names:
            return []

        resolutions = skill_resolver.resolve_many(
            db,
            skill_names,
            allow_create=True,
        )

        hackathon_skills: list[
            HackathonSkillCreate
        ] = []

        seen_skill_ids: set[uuid.UUID] = set()

        for resolution in resolutions:

            skill = resolution.skill

            if skill is None:
                continue

            if skill.id in seen_skill_ids:
                continue

            seen_skill_ids.add(skill.id)

            hackathon_skills.append(
                HackathonSkillCreate(
                    skill_id=skill.id,
                    required_level=None,
                    priority=1,
                    mandatory=False,
                )
            )

        return hackathon_skills

    # =====================================================
    # SYNC UNSTOP HACKATHONS
    # =====================================================

    def sync_unstop_hackathons(
        self,
        db: Session,
        max_pages: int | None = None,
        per_page: int = 18,
    ) -> dict:
        """
        Fetch open hackathons from Unstop and synchronize
        them into CollabVerse.

        The synchronization pipeline is:

        Unstop raw data
            ->
        normalize hackathon
            ->
        extract required skill names
            ->
        SkillResolver
            ->
        CollabVerse Skill UUIDs
            ->
        HackathonSkill relationships
            ->
        external hackathon upsert

        max_pages:
            None = fetch all available pages
            1 = first page only
            2 = first two pages
            etc.
        """

        created_count = 0
        updated_count = 0
        failed_count = 0
        fetched_count = 0
        pages_processed = 0

        resolved_skill_count = 0
        unresolved_skill_count = 0

        errors: list[dict] = []

        # -------------------------------------------------
        # Fetch first page
        # -------------------------------------------------

        try:
            first_payload = unstop_collector.fetch_raw(
                page=1,
                per_page=per_page,
            )

        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Failed to fetch hackathons "
                    f"from Unstop: {exc}"
                ),
            )

        # -------------------------------------------------
        # Discover total number of pages
        # -------------------------------------------------

        data = first_payload.get("data")

        total_pages = 1

        if isinstance(data, dict):

            try:
                total_pages = int(
                    data.get("last_page") or 1
                )

            except (TypeError, ValueError):
                total_pages = 1

        if max_pages is not None:
            total_pages = min(
                total_pages,
                max_pages,
            )

        # -------------------------------------------------
        # Process pages
        # -------------------------------------------------

        for page in range(
            1,
            total_pages + 1,
        ):

            try:

                if page == 1:
                    payload = first_payload

                else:
                    payload = (
                        unstop_collector.fetch_raw(
                            page=page,
                            per_page=per_page,
                        )
                    )

                raw_items = (
                    unstop_collector._extract_items(
                        payload
                    )
                )

                pages_processed += 1

            except Exception as exc:

                errors.append(
                    {
                        "page": page,
                        "error": (
                            "Failed to fetch page: "
                            f"{exc}"
                        ),
                    }
                )

                continue

            # -------------------------------------------------
            # Normalize + resolve skills + save
            # -------------------------------------------------

            for raw_item in raw_items:

                try:

                    # -----------------------------------------
                    # Normalize hackathon
                    # -----------------------------------------

                    hackathon_data = (
                        unstop_collector._normalize(
                            raw_item
                        )
                    )

                    if hackathon_data is None:

                        failed_count += 1

                        errors.append(
                            {
                                "page": page,
                                "external_id": (
                                    raw_item.get("id")
                                ),
                                "title": (
                                    raw_item.get(
                                        "title"
                                    )
                                ),
                                "error": (
                                    "Could not normalize "
                                    "hackathon"
                                ),
                            }
                        )

                        continue

                    fetched_count += 1

                    # -----------------------------------------
                    # Extract real Unstop skill names
                    # -----------------------------------------

                    external_skill_names = (
                        unstop_collector
                        .get_required_skill_names(
                            raw_item
                        )
                    )

                    # -----------------------------------------
                    # Resolve into CollabVerse skills
                    # -----------------------------------------

                    resolved_skills = (
                        self._resolve_external_skills(
                            db=db,
                            skill_names=(
                                external_skill_names
                            ),
                        )
                    )

                    resolved_skill_count += len(
                        resolved_skills
                    )

                    unresolved_skill_count += max(
                        0,
                        len(external_skill_names)
                        - len(resolved_skills),
                    )

                    # -----------------------------------------
                    # Attach resolved skills to schema
                    # -----------------------------------------

                    hackathon_data = (
                        hackathon_data.model_copy(
                            update={
                                "skills": (
                                    resolved_skills
                                )
                            }
                        )
                    )

                    # -----------------------------------------
                    # Create/update hackathon
                    # -----------------------------------------

                    _, created = (
                        self.upsert_external_hackathon(
                            db=db,
                            data=hackathon_data,
                        )
                    )

                    if created:
                        created_count += 1

                    else:
                        updated_count += 1

                except Exception as exc:

                    # Important:
                    # SkillResolver can flush newly-created
                    # skills before the hackathon itself is
                    # saved. Reset the transaction if this
                    # individual import fails.
                    db.rollback()

                    failed_count += 1

                    errors.append(
                        {
                            "page": page,
                            "external_id": (
                                raw_item.get("id")
                            ),
                            "title": (
                                raw_item.get("title")
                            ),
                            "error": str(exc),
                        }
                    )

        # -------------------------------------------------
        # Final sync summary
        # -------------------------------------------------

        return {
            "source": "Unstop",
            "pages_processed": pages_processed,
            "fetched": fetched_count,
            "created": created_count,
            "updated": updated_count,
            "resolved_skills": (
                resolved_skill_count
            ),
            "unresolved_skills": (
                unresolved_skill_count
            ),
            "failed": failed_count,
            "errors": errors,
        }

    # =====================================================
    # CREATE COLLABVERSE HACKATHON
    # =====================================================

    def create_hackathon(
        self,
        db: Session,
        current_user: User,
        data: HackathonCreate,
    ) -> Hackathon:

        repository = HackathonRepository(db)

        hackathon = Hackathon(
            title=data.title,
            description=data.description,
            domain=data.domain,
            organizer_name=data.organizer_name,
            created_by=current_user.id,

            source_type=(
                HackathonSourceType.COLLABVERSE
            ),

            source_name="CollabVerse",

            mode=data.mode,
            difficulty=data.difficulty,
            status=data.status,
            location=data.location,

            min_team_size=data.min_team_size,
            max_team_size=data.max_team_size,

            registration_deadline=(
                data.registration_deadline
            ),

            start_date=data.start_date,
            end_date=data.end_date,

            prize_details=data.prize_details,

            registration_url=(
                str(data.registration_url)
                if data.registration_url
                else None
            ),

            banner_url=(
                str(data.banner_url)
                if data.banner_url
                else None
            ),

            is_featured=data.is_featured,
            is_verified=False,
            is_active=True,
        )

        for skill_data in data.skills:

            hackathon.skills.append(
                HackathonSkill(
                    skill_id=skill_data.skill_id,
                    required_level=(
                        skill_data.required_level
                    ),
                    priority=skill_data.priority,
                    mandatory=skill_data.mandatory,
                )
            )

        return repository.create(
            hackathon
        )

    # =====================================================
    # GET HACKATHON
    # =====================================================

    def get_hackathon(
        self,
        db: Session,
        hackathon_id: uuid.UUID,
    ) -> Hackathon:

        repository = HackathonRepository(db)

        hackathon = repository.get_by_id(
            hackathon_id
        )

        if not hackathon:

            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Hackathon not found",
            )

        return hackathon

    # =====================================================
    # LIST HACKATHONS
    # =====================================================

    def list_hackathons(
        self,
        db: Session,
        limit: int = 20,
        offset: int = 0,
        domain: str | None = None,
    ) -> dict:

        repository = HackathonRepository(db)

        hackathons = (
            repository.list_hackathons(
                limit=limit,
                offset=offset,
                domain=domain,
            )
        )

        total = repository.count_hackathons(
            domain=domain
        )

        return {
            "total": total,
            "hackathons": hackathons,
        }

    # =====================================================
    # SEARCH HACKATHONS
    # =====================================================

    def search_hackathons(
        self,
        db: Session,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:

        repository = HackathonRepository(db)

        hackathons = repository.search(
            query_text=query,
            limit=limit,
            offset=offset,
        )

        return {
            "total": len(hackathons),
            "hackathons": hackathons,
        }

    # =====================================================
    # UPDATE COLLABVERSE HACKATHON
    # =====================================================

    def update_hackathon(
        self,
        db: Session,
        current_user: User,
        hackathon_id: uuid.UUID,
        data: HackathonUpdate,
    ) -> Hackathon:

        repository = HackathonRepository(db)

        hackathon = repository.get_by_id(
            hackathon_id
        )

        if not hackathon:

            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Hackathon not found",
            )

        # -------------------------------------------------
        # External hackathons must only be updated through
        # the synchronization system.
        # -------------------------------------------------

        if (
            hackathon.source_type
            == HackathonSourceType.EXTERNAL
        ):

            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail=(
                    "External hackathons are updated "
                    "through the sync system"
                ),
            )

        # -------------------------------------------------
        # Only creator can update CollabVerse hackathon
        # -------------------------------------------------

        if (
            hackathon.created_by
            != current_user.id
        ):

            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail=(
                    "You cannot update this hackathon"
                ),
            )

        update_data = data.model_dump(
            exclude_unset=True
        )

        # -------------------------------------------------
        # Skills require relationship handling rather than
        # setattr().
        # -------------------------------------------------

        skills_data = update_data.pop(
            "skills",
            None,
        )

        for field, value in (
            update_data.items()
        ):

            if field in {
                "registration_url",
                "banner_url",
            }:

                value = (
                    str(value)
                    if value is not None
                    else None
                )

            setattr(
                hackathon,
                field,
                value,
            )

        if skills_data is not None:

            hackathon.skills.clear()

            for skill_data in skills_data:

                # model_dump() converts nested Pydantic
                # objects to dictionaries.
                if isinstance(
                    skill_data,
                    dict,
                ):

                    hackathon.skills.append(
                        HackathonSkill(
                            skill_id=(
                                skill_data[
                                    "skill_id"
                                ]
                            ),
                            required_level=(
                                skill_data.get(
                                    "required_level"
                                )
                            ),
                            priority=(
                                skill_data.get(
                                    "priority",
                                    1,
                                )
                            ),
                            mandatory=(
                                skill_data.get(
                                    "mandatory",
                                    False,
                                )
                            ),
                        )
                    )

                else:

                    hackathon.skills.append(
                        HackathonSkill(
                            skill_id=(
                                skill_data.skill_id
                            ),
                            required_level=(
                                skill_data
                                .required_level
                            ),
                            priority=(
                                skill_data.priority
                            ),
                            mandatory=(
                                skill_data.mandatory
                            ),
                        )
                    )

        return repository.save(
            hackathon
        )

    # =====================================================
    # DELETE / DEACTIVATE
    # =====================================================

    def deactivate_hackathon(
        self,
        db: Session,
        current_user: User,
        hackathon_id: uuid.UUID,
    ) -> Hackathon:

        repository = HackathonRepository(db)

        hackathon = repository.get_by_id(
            hackathon_id
        )

        if not hackathon:

            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Hackathon not found",
            )

        # -------------------------------------------------
        # IMPORTANT SECURITY FIX
        #
        # External hackathons have created_by=None.
        # Previously this allowed them to pass the creator
        # ownership check and be deactivated manually.
        # -------------------------------------------------

        if (
            hackathon.source_type
            == HackathonSourceType.EXTERNAL
        ):

            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail=(
                    "External hackathons are managed "
                    "through the sync system"
                ),
            )

        # -------------------------------------------------
        # CollabVerse hackathon ownership
        # -------------------------------------------------

        if (
            hackathon.created_by
            != current_user.id
        ):

            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail=(
                    "You cannot deactivate "
                    "this hackathon"
                ),
            )

        hackathon.is_active = False

        return repository.save(
            hackathon
        )

    # =====================================================
    # EXTERNAL HACKATHON UPSERT
    # =====================================================

    def upsert_external_hackathon(
        self,
        db: Session,
        data: ExternalHackathonCreate,
    ) -> tuple[Hackathon, bool]:
        """
        Used by external collectors.

        Returns:

        (hackathon, created)

        created=True:
            New hackathon inserted.

        created=False:
            Existing hackathon updated.
        """

        repository = HackathonRepository(db)

        source_url = str(
            data.source_url
        )

        existing = (
            repository.find_existing_external(
                source_name=data.source_name,
                source_url=source_url,
                external_id=data.external_id,
            )
        )

        # =================================================
        # UPDATE EXISTING EXTERNAL HACKATHON
        # =================================================

        if existing:

            existing.title = data.title

            existing.description = (
                data.description
            )

            existing.domain = data.domain

            existing.organizer_name = (
                data.organizer_name
            )

            existing.mode = data.mode

            existing.difficulty = (
                data.difficulty
            )

            existing.status = data.status

            existing.location = (
                data.location
            )

            existing.min_team_size = (
                data.min_team_size
            )

            existing.max_team_size = (
                data.max_team_size
            )

            existing.registration_deadline = (
                data.registration_deadline
            )

            existing.start_date = (
                data.start_date
            )

            existing.end_date = (
                data.end_date
            )

            existing.prize_details = (
                data.prize_details
            )

            existing.registration_url = (
                str(data.registration_url)
                if data.registration_url
                else None
            )

            existing.banner_url = (
                str(data.banner_url)
                if data.banner_url
                else None
            )

            existing.source_name = (
                data.source_name
            )

            existing.source_url = (
                source_url
            )

            existing.external_id = (
                data.external_id
            )

            existing.source_type = (
                HackathonSourceType.EXTERNAL
            )

            existing.last_synced_at = (
                datetime.now(
                    timezone.utc
                )
            )

            existing.is_active = True

            # ---------------------------------------------
            # Replace imported skill relationships
            # ---------------------------------------------

            existing.skills.clear()

            for skill_data in data.skills:

                existing.skills.append(
                    HackathonSkill(
                        skill_id=(
                            skill_data.skill_id
                        ),
                        required_level=(
                            skill_data.required_level
                        ),
                        priority=(
                            skill_data.priority
                        ),
                        mandatory=(
                            skill_data.mandatory
                        ),
                    )
                )

            updated = repository.save(
                existing
            )

            return updated, False

        # =================================================
        # CREATE NEW EXTERNAL HACKATHON
        # =================================================

        hackathon = Hackathon(
            title=data.title,
            description=data.description,
            domain=data.domain,

            organizer_name=(
                data.organizer_name
            ),

            created_by=None,

            source_type=(
                HackathonSourceType.EXTERNAL
            ),

            source_name=data.source_name,
            source_url=source_url,
            external_id=data.external_id,

            last_synced_at=(
                datetime.now(
                    timezone.utc
                )
            ),

            mode=data.mode,
            difficulty=data.difficulty,
            status=data.status,

            location=data.location,

            min_team_size=(
                data.min_team_size
            ),

            max_team_size=(
                data.max_team_size
            ),

            registration_deadline=(
                data.registration_deadline
            ),

            start_date=data.start_date,
            end_date=data.end_date,

            prize_details=(
                data.prize_details
            ),

            registration_url=(
                str(data.registration_url)
                if data.registration_url
                else None
            ),

            banner_url=(
                str(data.banner_url)
                if data.banner_url
                else None
            ),

            is_verified=False,
            is_featured=data.is_featured,
            is_active=True,
        )

        for skill_data in data.skills:

            hackathon.skills.append(
                HackathonSkill(
                    skill_id=skill_data.skill_id,
                    required_level=(
                        skill_data.required_level
                    ),
                    priority=(
                        skill_data.priority
                    ),
                    mandatory=(
                        skill_data.mandatory
                    ),
                )
            )

        created = repository.create(
            hackathon
        )

        return created, True

    # =====================================================
    # REGISTER FOR COLLABVERSE HACKATHON
    # =====================================================

    def register_participant(
        self,
        db: Session,
        current_user: User,
        hackathon_id: uuid.UUID,
        data: HackathonParticipantCreate,
    ) -> HackathonParticipant:

        repository = HackathonRepository(db)

        hackathon = repository.get_by_id(
            hackathon_id
        )

        if not hackathon:

            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Hackathon not found",
            )

        if not hackathon.is_active:

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "Hackathon is not active"
                ),
            )

        # -------------------------------------------------
        # External hackathons use original registration URL
        # -------------------------------------------------

        if (
            hackathon.source_type
            == HackathonSourceType.EXTERNAL
        ):

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "This is an external hackathon. "
                    "Use its registration URL."
                ),
            )

        existing = (
            repository.get_participant(
                hackathon_id=hackathon_id,
                user_id=current_user.id,
            )
        )

        if existing:

            if (
                existing.status
                != HackathonParticipantStatus
                .WITHDRAWN
            ):

                raise HTTPException(
                    status_code=(
                        status.HTTP_409_CONFLICT
                    ),
                    detail=(
                        "You are already registered"
                    ),
                )

            existing.status = (
                HackathonParticipantStatus
                .REGISTERED
            )

            existing.team_name = (
                data.team_name
            )

            return (
                repository.save_participant(
                    existing
                )
            )

        participant = HackathonParticipant(
            hackathon_id=hackathon_id,
            user_id=current_user.id,
            team_name=data.team_name,
            status=(
                HackathonParticipantStatus
                .REGISTERED
            ),
        )

        return repository.add_participant(
            participant
        )

    # =====================================================
    # WITHDRAW
    # =====================================================

    def withdraw_participant(
        self,
        db: Session,
        current_user: User,
        hackathon_id: uuid.UUID,
    ) -> HackathonParticipant:

        repository = HackathonRepository(db)

        participant = (
            repository.get_participant(
                hackathon_id=hackathon_id,
                user_id=current_user.id,
            )
        )

        if not participant:

            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail=(
                    "Hackathon registration "
                    "not found"
                ),
            )

        participant.status = (
            HackathonParticipantStatus
            .WITHDRAWN
        )

        return repository.save_participant(
            participant
        )


hackathon_service = HackathonService()