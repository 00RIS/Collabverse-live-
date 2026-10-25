import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.hackathons.models import (
    Hackathon,
    HackathonParticipant,
    HackathonParticipantStatus,
    HackathonSourceType,
    HackathonStatus,
)


class HackathonRepository:
    def __init__(self, db: Session):
        self.db = db

    # =====================================================
    # BASIC HACKATHON OPERATIONS
    # =====================================================

    def create(
        self,
        hackathon: Hackathon,
    ) -> Hackathon:
        self.db.add(hackathon)
        self.db.commit()
        self.db.refresh(hackathon)

        return self.get_by_id(hackathon.id)

    def get_by_id(
        self,
        hackathon_id: uuid.UUID,
    ) -> Hackathon | None:
        return self.db.scalar(
            select(Hackathon)
            .options(
                selectinload(Hackathon.skills),
                selectinload(
                    Hackathon.participants
                ),
            )
            .where(
                Hackathon.id == hackathon_id
            )
        )

    def save(
        self,
        hackathon: Hackathon,
    ) -> Hackathon:
        self.db.add(hackathon)
        self.db.commit()
        self.db.refresh(hackathon)

        return self.get_by_id(hackathon.id)

    def delete(
        self,
        hackathon: Hackathon,
    ) -> None:
        self.db.delete(hackathon)
        self.db.commit()

    # =====================================================
    # LIST / DISCOVERY
    # =====================================================

    def list_hackathons(
        self,
        limit: int = 20,
        offset: int = 0,
        active_only: bool = True,
        status: HackathonStatus | None = None,
        domain: str | None = None,
        source_type: (
            HackathonSourceType | None
        ) = None,
    ) -> list[Hackathon]:

        query = (
            select(Hackathon)
            .options(
                selectinload(Hackathon.skills)
            )
        )

        if active_only:
            query = query.where(
                Hackathon.is_active.is_(True)
            )

        if status is not None:
            query = query.where(
                Hackathon.status == status
            )

        if domain:
            query = query.where(
                Hackathon.domain.ilike(
                    f"%{domain}%"
                )
            )

        if source_type is not None:
            query = query.where(
                Hackathon.source_type
                == source_type
            )

        query = (
            query
            .order_by(
                Hackathon.is_featured.desc(),
                Hackathon.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        return list(
            self.db.scalars(query).all()
        )

    def count_hackathons(
        self,
        active_only: bool = True,
        status: HackathonStatus | None = None,
        domain: str | None = None,
        source_type: (
            HackathonSourceType | None
        ) = None,
    ) -> int:

        query = select(
            func.count(Hackathon.id)
        )

        if active_only:
            query = query.where(
                Hackathon.is_active.is_(True)
            )

        if status is not None:
            query = query.where(
                Hackathon.status == status
            )

        if domain:
            query = query.where(
                Hackathon.domain.ilike(
                    f"%{domain}%"
                )
            )

        if source_type is not None:
            query = query.where(
                Hackathon.source_type
                == source_type
            )

        return int(
            self.db.scalar(query) or 0
        )

    # =====================================================
    # OPEN / RECOMMENDABLE HACKATHONS
    # =====================================================

    def get_open_hackathons(
        self,
        limit: int = 100,
    ) -> list[Hackathon]:

        return list(
            self.db.scalars(
                select(Hackathon)
                .options(
                    selectinload(
                        Hackathon.skills
                    )
                )
                .where(
                    Hackathon.is_active.is_(
                        True
                    ),
                    Hackathon.status
                    == HackathonStatus
                    .REGISTRATION_OPEN,
                )
                .order_by(
                    Hackathon
                    .registration_deadline
                    .asc()
                    .nullslast(),
                    Hackathon
                    .created_at
                    .desc(),
                )
                .limit(limit)
            ).all()
        )

    # =====================================================
    # SEARCH
    # =====================================================

    def search(
        self,
        query_text: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Hackathon]:

        search_term = (
            f"%{query_text.strip()}%"
        )

        return list(
            self.db.scalars(
                select(Hackathon)
                .options(
                    selectinload(
                        Hackathon.skills
                    )
                )
                .where(
                    Hackathon.is_active.is_(
                        True
                    ),
                    or_(
                        Hackathon.title.ilike(
                            search_term
                        ),
                        Hackathon.description.ilike(
                            search_term
                        ),
                        Hackathon.domain.ilike(
                            search_term
                        ),
                        Hackathon
                        .organizer_name
                        .ilike(search_term),
                    ),
                )
                .order_by(
                    Hackathon
                    .is_featured
                    .desc(),
                    Hackathon
                    .created_at
                    .desc(),
                )
                .offset(offset)
                .limit(limit)
            ).all()
        )

    # =====================================================
    # EXTERNAL SOURCE LOOKUPS
    # =====================================================

    def get_by_external_id(
        self,
        source_name: str,
        external_id: str,
    ) -> Hackathon | None:

        return self.db.scalar(
            select(Hackathon)
            .options(
                selectinload(
                    Hackathon.skills
                )
            )
            .where(
                Hackathon.source_type
                == HackathonSourceType
                .EXTERNAL,
                func.lower(
                    Hackathon.source_name
                )
                == source_name.lower(),
                Hackathon.external_id
                == external_id,
            )
        )

    def get_by_source_url(
        self,
        source_url: str,
    ) -> Hackathon | None:

        return self.db.scalar(
            select(Hackathon)
            .options(
                selectinload(
                    Hackathon.skills
                )
            )
            .where(
                Hackathon.source_type
                == HackathonSourceType
                .EXTERNAL,
                Hackathon.source_url
                == source_url,
            )
        )

    def find_existing_external(
        self,
        source_name: str,
        source_url: str,
        external_id: str | None = None,
    ) -> Hackathon | None:
        """
        Main deduplication method used by
        the future aggregator.

        Priority:

        1. source_name + external_id
        2. source_url
        """

        if external_id:
            existing = (
                self.get_by_external_id(
                    source_name=source_name,
                    external_id=external_id,
                )
            )

            if existing:
                return existing

        return self.get_by_source_url(
            source_url
        )

    # =====================================================
    # PARTICIPANTS
    # =====================================================

    def get_participant(
        self,
        hackathon_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> HackathonParticipant | None:

        return self.db.scalar(
            select(HackathonParticipant)
            .where(
                HackathonParticipant
                .hackathon_id
                == hackathon_id,
                HackathonParticipant
                .user_id
                == user_id,
            )
        )

    def add_participant(
        self,
        participant: HackathonParticipant,
    ) -> HackathonParticipant:

        self.db.add(participant)
        self.db.commit()
        self.db.refresh(participant)

        return participant

    def save_participant(
        self,
        participant: HackathonParticipant,
    ) -> HackathonParticipant:

        self.db.add(participant)
        self.db.commit()
        self.db.refresh(participant)

        return participant

    def list_participants(
        self,
        hackathon_id: uuid.UUID,
    ) -> list[HackathonParticipant]:

        return list(
            self.db.scalars(
                select(
                    HackathonParticipant
                )
                .where(
                    HackathonParticipant
                    .hackathon_id
                    == hackathon_id,
                    HackathonParticipant
                    .status
                    != HackathonParticipantStatus
                    .WITHDRAWN,
                )
                .order_by(
                    HackathonParticipant
                    .registered_at
                    .asc()
                )
            ).all()
        )