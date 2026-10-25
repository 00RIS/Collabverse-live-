from datetime import datetime
from html import unescape
import re
from typing import Any

import requests

from app.modules.hackathons.collectors.base import BaseHackathonCollector
from app.modules.hackathons.models import (
    HackathonDifficulty,
    HackathonMode,
    HackathonStatus,
)
from app.modules.hackathons.schemas import ExternalHackathonCreate


class UnstopCollector(BaseHackathonCollector):
    """
    Collector responsible for fetching and normalizing
    hackathons from Unstop.

    Important:
    - This collector extracts Unstop skill names.
    - It does NOT create CollabVerse Skill rows.
    - Skill resolution will be handled by SkillResolver.
    """

    source_name = "Unstop"

    BASE_URL = (
        "https://unstop.com/api/public/opportunity/search-result"
    )

    # =========================================================
    # TEMPORARY DOMAIN DETECTION
    # =========================================================
    #
    # We will eventually replace this with our dynamic
    # skill/domain intelligence system.
    #
    # For now this keeps the existing hackathon pipeline
    # working while SkillResolver is being built.
    # =========================================================

    DOMAIN_KEYWORDS = {
        "Artificial Intelligence": [
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "generative ai",
            "genai",
            "computer vision",
            "natural language processing",
            "agentic ai",
        ],

        "Cybersecurity": [
            "cybersecurity",
            "cyber security",
            "ctf",
            "capture the flag",
            "ethical hacking",
            "penetration testing",
            "cryptography",
            "web security",
            "application security",
            "network security",
            "vulnerability assessment",
            "digital forensics",
        ],

        "Web Development": [
            "web development",
            "web application",
            "frontend",
            "front end",
            "backend development",
            "back end development",
            "full stack",
            "full-stack",
            "react",
            "javascript",
            "node.js",
            "nodejs",
            "api development",
        ],

        "Software Development": [
            "software development",
            "software engineering",
            "data structures and algorithms",
            "c++ programming",
            "java programming",
            "python programming",
            "coding",
            "debugging",
            "software development life cycle",
            "sdlc",
        ],

        "Data Science": [
            "data science",
            "data analytics",
            "data analysis",
            "big data",
            "business analytics",
            "data visualization",
            "data mining",
        ],

        "Blockchain": [
            "blockchain",
            "web3",
            "smart contract",
            "ethereum",
            "solidity",
            "decentralized",
            "dapp",
        ],

        "Cloud Computing": [
            "cloud computing",
            "aws",
            "azure",
            "google cloud",
            "gcp",
            "devops",
            "kubernetes",
            "docker",
        ],

        "IoT": [
            "internet of things",
            "iot",
            "embedded systems",
            "embedded system",
            "sensor technology",
            "sensor network",
        ],

        "Robotics": [
            "robotics",
            "robotics engineer",
            "robotics path planning",
            "robotics kinematics",
            "autonomous systems",
            "robot",
        ],

        "Mobile Development": [
            "android development",
            "ios development",
            "mobile development",
            "mobile application",
            "flutter",
            "react native",
        ],

        "Quantum Computing": [
            "quantum computing",
            "qiskit",
            "quantum programming",
        ],

        "Game Development": [
            "game development",
            "game design",
            "game testing",
            "game developer",
            "gaming",
            "esports",
            "online gaming",
        ],

        "Marketing": [
            "digital marketing",
            "social media marketing",
            "marketing",
            "search engine optimization",
            "branding",
        ],

        "Entrepreneurship": [
            "entrepreneurship",
            "startup",
            "business idea",
            "business model",
            "innovation challenge",
            "innovation management",
            "ideation",
        ],
    }

    # =========================================================
    # DATETIME
    # =========================================================

    def _parse_datetime(
        self,
        value: str | None,
    ) -> datetime | None:
        if not value:
            return None

        try:
            return datetime.fromisoformat(
                str(value).replace(
                    "Z",
                    "+00:00",
                )
            )

        except (ValueError, TypeError):
            return None

    # =========================================================
    # HTML CLEANING
    # =========================================================

    def _clean_html(
        self,
        value: str | None,
    ) -> str:
        if not value:
            return "No description provided."

        text = re.sub(
            r"<[^>]+>",
            " ",
            str(value),
        )

        text = unescape(text)

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # =========================================================
    # SAFE TEXT NORMALIZATION
    # =========================================================

    def _normalize_text(
        self,
        value: Any,
    ) -> str:
        """
        Only normalize real text.

        Do NOT recursively stringify dictionaries.

        Unstop dictionaries contain metadata such as:

            ai_generated=True

        and that metadata previously caused false AI domain
        classifications.
        """

        if value is None:
            return ""

        if isinstance(value, str):
            return self._clean_html(
                value
            ).lower()

        if isinstance(
            value,
            (int, float),
        ):
            return str(value).lower()

        if isinstance(value, list):
            values = []

            for item in value:
                if isinstance(
                    item,
                    (str, int, float),
                ):
                    values.append(
                        self._normalize_text(
                            item
                        )
                    )

            return " ".join(values)

        return ""

    # =========================================================
    # REQUIRED SKILLS
    # =========================================================

    def _get_required_skill_names(
        self,
        item: dict[str, Any],
    ) -> list[str]:
        """
        Extract actual required skill names from Unstop.

        Example:

        [
            {
                "skill_name": "Python",
                "pivot": {
                    "ai_generated": True
                }
            }
        ]

        becomes:

        ["Python"]

        Metadata such as ai_generated is ignored.
        """

        required_skills = item.get(
            "required_skills"
        )

        if not isinstance(
            required_skills,
            list,
        ):
            return []

        results: list[str] = []
        seen: set[str] = set()

        for skill in required_skills:
            name = None

            if isinstance(
                skill,
                dict,
            ):
                raw_name = (
                    skill.get("skill_name")
                    or skill.get("skill")
                    or skill.get("name")
                )

                if isinstance(
                    raw_name,
                    str,
                ):
                    name = raw_name.strip()

            elif isinstance(
                skill,
                str,
            ):
                name = skill.strip()

            if not name:
                continue

            normalized_name = (
                name.casefold()
            )

            if normalized_name in seen:
                continue

            seen.add(
                normalized_name
            )

            results.append(
                name
            )

        return results

    def get_required_skill_names(
        self,
        item: dict[str, Any],
    ) -> list[str]:
        """
        Public wrapper used by the synchronization layer.
        """

        return self._get_required_skill_names(
            item
        )

    # =========================================================
    # WORK FUNCTIONS
    # =========================================================

    def _get_workfunction_names(
        self,
        item: dict[str, Any],
    ) -> list[str]:
        workfunctions = item.get(
            "workfunction"
        )

        if not isinstance(
            workfunctions,
            list,
        ):
            return []

        results: list[str] = []
        seen: set[str] = set()

        for workfunction in workfunctions:
            name = None

            if isinstance(
                workfunction,
                dict,
            ):
                raw_name = (
                    workfunction.get(
                        "name"
                    )
                )

                if isinstance(
                    raw_name,
                    str,
                ):
                    name = raw_name.strip()

            elif isinstance(
                workfunction,
                str,
            ):
                name = workfunction.strip()

            if not name:
                continue

            normalized_name = (
                name.casefold()
            )

            if normalized_name in seen:
                continue

            seen.add(
                normalized_name
            )

            results.append(
                name
            )

        return results

    # =========================================================
    # ORGANIZER
    # =========================================================

    def _get_organizer(
        self,
        item: dict[str, Any],
    ) -> str:
        organisation = item.get(
            "organisation"
        )

        if isinstance(
            organisation,
            dict,
        ):
            name = organisation.get(
                "name"
            )

            if (
                isinstance(name, str)
                and name.strip()
            ):
                return name.strip()[:255]

        return "Unknown Organizer"

    # =========================================================
    # LOCATION
    # =========================================================

    def _get_location(
        self,
        item: dict[str, Any],
    ) -> str | None:
        address_data = item.get(
            "address_with_country_logo"
        )

        if not isinstance(
            address_data,
            dict,
        ):
            return None

        parts: list[str] = []

        for key in (
            "address",
            "city",
            "state",
        ):
            value = address_data.get(
                key
            )

            if not isinstance(
                value,
                str,
            ):
                continue

            value = value.strip()

            if (
                value
                and value not in parts
            ):
                parts.append(
                    value
                )

        if not parts:
            return None

        return ", ".join(
            parts
        )[:255]

    # =========================================================
    # MODE
    # =========================================================

    def _get_mode(
        self,
        item: dict[str, Any],
    ) -> HackathonMode:
        region = str(
            item.get("region")
            or ""
        ).lower().strip()

        if region == "offline":
            return HackathonMode.OFFLINE

        if region == "hybrid":
            return HackathonMode.HYBRID

        return HackathonMode.ONLINE

    # =========================================================
    # REGISTRATION DATA
    # =========================================================

    def _get_registration_data(
        self,
        item: dict[str, Any],
    ) -> tuple[
        datetime | None,
        int,
        int,
    ]:
        requirements = item.get(
            "regnRequirements"
        )

        if not isinstance(
            requirements,
            dict,
        ):
            return (
                None,
                1,
                4,
            )

        registration_deadline = (
            self._parse_datetime(
                requirements.get(
                    "end_regn_dt"
                )
            )
        )

        min_team_size = (
            requirements.get(
                "min_team_size"
            )
            or 1
        )

        max_team_size = (
            requirements.get(
                "max_team_size"
            )
            or min_team_size
        )

        try:
            min_team_size = int(
                min_team_size
            )

        except (
            TypeError,
            ValueError,
        ):
            min_team_size = 1

        try:
            max_team_size = int(
                max_team_size
            )

        except (
            TypeError,
            ValueError,
        ):
            max_team_size = (
                min_team_size
            )

        min_team_size = max(
            1,
            min_team_size,
        )

        max_team_size = max(
            min_team_size,
            max_team_size,
        )

        return (
            registration_deadline,
            min_team_size,
            max_team_size,
        )

    # =========================================================
    # DOMAIN DETECTION
    # =========================================================

    def _get_domain(
        self,
        item: dict[str, Any],
    ) -> str | None:
        """
        Temporary domain classifier.

        Strong evidence:
        - title
        - required skills
        - work functions

        Weak evidence:
        - description

        Later this can be replaced by the dynamic skill/domain
        resolver.
        """

        title = str(
            item.get("title")
            or ""
        ).lower()

        skill_names = (
            self._get_required_skill_names(
                item
            )
        )

        workfunction_names = (
            self._get_workfunction_names(
                item
            )
        )

        structured_text = " ".join(
            [
                title,
                *[
                    skill.lower()
                    for skill
                    in skill_names
                ],
                *[
                    workfunction.lower()
                    for workfunction
                    in workfunction_names
                ],
            ]
        )

        description_text = (
            self._normalize_text(
                item.get(
                    "details"
                )
            )
        )

        scores: dict[
            str,
            int,
        ] = {}

        for (
            domain,
            keywords,
        ) in self.DOMAIN_KEYWORDS.items():
            score = 0

            for keyword in keywords:
                keyword = (
                    keyword
                    .lower()
                    .strip()
                )

                if not keyword:
                    continue

                # Structured fields are strong evidence.
                if (
                    keyword
                    in structured_text
                ):
                    score += 5

                # Description is weak evidence.
                #
                # We intentionally avoid short keywords
                # here because terms such as AI can cause
                # accidental matches.
                if (
                    len(keyword) >= 8
                    and keyword
                    in description_text
                ):
                    score += 1

            if score > 0:
                scores[
                    domain
                ] = score

        if not scores:
            return None

        return max(
            scores,
            key=scores.get,
        )

    # =========================================================
    # SOURCE URL
    # =========================================================

    def _get_source_url(
        self,
        item: dict[str, Any],
    ) -> str | None:
        source_url = (
            item.get("seo_url")
            or item.get("short_url")
        )

        if not source_url:
            public_url = item.get(
                "public_url"
            )

            if public_url:
                source_url = str(
                    public_url
                )

        if not source_url:
            return None

        source_url = str(
            source_url
        ).strip()

        # Some Unstop fields may contain a relative URL.
        if source_url.startswith("/"):
            source_url = (
                "https://unstop.com"
                + source_url
            )

        elif not source_url.startswith(
            (
                "http://",
                "https://",
            )
        ):
            source_url = (
                "https://unstop.com/"
                + source_url.lstrip("/")
            )

        return source_url

    # =========================================================
    # NORMALIZE ONE HACKATHON
    # =========================================================

    def _normalize(
        self,
        item: dict[str, Any],
    ) -> ExternalHackathonCreate | None:
        external_id = item.get(
            "id"
        )

        title = item.get(
            "title"
        )

        if (
            not external_id
            or not title
        ):
            return None

        (
            registration_deadline,
            min_team_size,
            max_team_size,
        ) = self._get_registration_data(
            item
        )

        source_url = (
            self._get_source_url(
                item
            )
        )

        if not source_url:
            return None

        description = (
            self._clean_html(
                item.get(
                    "details"
                )
            )
        )

        end_date = (
            self._parse_datetime(
                item.get(
                    "end_date"
                )
            )
        )

        prizes = item.get(
            "prizes"
        )

        if isinstance(
            prizes,
            str,
        ):
            prizes = (
                prizes.strip()
                or None
            )
        else:
            prizes = None

        banner_url = (
            item.get("logoUrl2")
            or item.get("thumb")
        )

        if not isinstance(
            banner_url,
            str,
        ):
            banner_url = None

        domain = (
            self._get_domain(
                item
            )
        )

        return ExternalHackathonCreate(
            title=(
                str(title)
                .strip()[:255]
            ),

            description=description,

            domain=domain,

            organizer_name=(
                self._get_organizer(
                    item
                )
            ),

            mode=(
                self._get_mode(
                    item
                )
            ),

            difficulty=(
                HackathonDifficulty.OPEN
            ),

            status=(
                HackathonStatus
                .REGISTRATION_OPEN
            ),

            location=(
                self._get_location(
                    item
                )
            ),

            min_team_size=(
                min_team_size
            ),

            max_team_size=(
                max_team_size
            ),

            registration_deadline=(
                registration_deadline
            ),

            # Search-result data does not always
            # provide a trustworthy start date.
            start_date=None,

            end_date=end_date,

            prize_details=prizes,

            registration_url=(
                source_url
            ),

            banner_url=(
                banner_url
            ),

            is_featured=False,

            # IMPORTANT:
            #
            # These are intentionally empty here.
            #
            # Unstop's own skill IDs are NOT our
            # CollabVerse Skill UUIDs.
            #
            # SkillResolver will resolve the names
            # and populate HackathonSkillCreate later.
            skills=[],

            source_name=(
                self.source_name
            ),

            source_url=(
                source_url
            ),

            external_id=(
                str(external_id)
            ),
        )

    # =========================================================
    # FETCH RAW DATA
    # =========================================================

    def fetch_raw(
        self,
        page: int = 1,
        per_page: int = 18,
    ) -> dict[str, Any]:
        params = {
            "opportunity": "hackathons",
            "page": page,
            "per_page": per_page,
            "oppstatus": "open",
            "sortBy": "",
            "orderBy": "",
            "filter_condition": "",
        }

        headers = {
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0 "
                "Safari/537.36"
            ),
        }

        response = requests.get(
            self.BASE_URL,
            params=params,
            headers=headers,
            timeout=20,
        )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "Unexpected Unstop response format"
            )

        return payload

    # =========================================================
    # EXTRACT ITEMS
    # =========================================================

    def _extract_items(
        self,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]]:
        data = payload.get(
            "data"
        )

        # Possible format:
        #
        # {
        #     "data": [...]
        # }

        if isinstance(
            data,
            list,
        ):
            return [
                item
                for item in data
                if isinstance(
                    item,
                    dict,
                )
            ]

        # Common paginated format:
        #
        # {
        #     "data": {
        #         "data": [...]
        #     }
        # }

        if isinstance(
            data,
            dict,
        ):
            nested_data = data.get(
                "data"
            )

            if isinstance(
                nested_data,
                list,
            ):
                return [
                    item
                    for item
                    in nested_data
                    if isinstance(
                        item,
                        dict,
                    )
                ]

        return []

    # =========================================================
    # FETCH NORMALIZED HACKATHONS
    # =========================================================

    def fetch_hackathons(
        self,
        page: int = 1,
        per_page: int = 18,
    ) -> list[
        ExternalHackathonCreate
    ]:
        payload = self.fetch_raw(
            page=page,
            per_page=per_page,
        )

        items = (
            self._extract_items(
                payload
            )
        )

        results: list[
            ExternalHackathonCreate
        ] = []

        for item in items:
            try:
                normalized = (
                    self._normalize(
                        item
                    )
                )

                if (
                    normalized
                    is not None
                ):
                    results.append(
                        normalized
                    )

            except Exception as exc:
                print(
                    "Failed to normalize "
                    "Unstop hackathon "
                    f"{item.get('id')}: "
                    f"{exc}"
                )

        return results


# =============================================================
# SINGLE SHARED COLLECTOR INSTANCE
# =============================================================
#
# IMPORTANT:
# This is OUTSIDE the UnstopCollector class.
# =============================================================

unstop_collector = UnstopCollector()