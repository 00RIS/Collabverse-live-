from abc import ABC, abstractmethod

from app.modules.hackathons.schemas import ExternalHackathonCreate


class BaseHackathonCollector(ABC):
    """
    Base class for external hackathon collectors.

    Every source collector should:
    1. Fetch hackathons from its source.
    2. Normalize them into CollabVerse's ExternalHackathonCreate schema.
    """

    source_name: str

    @abstractmethod
    def fetch_hackathons(
        self,
        page: int = 1,
        per_page: int = 18,
    ) -> list[ExternalHackathonCreate]:
        raise NotImplementedError