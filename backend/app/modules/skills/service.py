"""
app/modules/skills/service.py

Skill Knowledge Graph service.

This service manages relationships between skills in the centralized
Skill Catalog.

It supports:

1. Parent / child relationships
   Example:
       Artificial Intelligence
            -> Machine Learning
                -> Deep Learning

2. Related skill relationships
   Example:
       Machine Learning <-> Python
       FastAPI <-> REST API
       React <-> JavaScript

The service is intentionally conservative. Relationships should only
be created when we have a strong reason to believe two skills are
actually related.

This prevents incorrect relationships such as:
    Java <-> JavaScript
    SQL <-> NoSQL
simply because their names look similar.
"""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill import (
    Skill,
)


# ============================================================
# RESULT MODEL
# ============================================================


@dataclass
class SkillGraphBuildResult:

    parent_links_created: int = 0
    related_links_created: int = 0
    missing_skills: int = 0
    skipped_links: int = 0


# ============================================================
# NORMALIZATION
# ============================================================


def normalize_skill_name(
    value: str,
) -> str:

    value = value.lower().strip()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value


# ============================================================
# CANONICAL SKILL ALIASES
# ============================================================

# These aliases are ONLY used to find an existing skill.
#
# They do not create relationships themselves.


SKILL_ALIASES = {

    "ai": (
        "artificial intelligence",
        "artificial intelligence (ai)",
    ),

    "artificial intelligence": (
        "artificial intelligence",
        "artificial intelligence (ai)",
        "ai",
    ),

    "ml": (
        "machine learning",
        "machine learning (ml)",
    ),

    "machine learning": (
        "machine learning",
        "machine learning (ml)",
        "ml",
    ),

    "nlp": (
        "natural language processing",
        "natural language processing (nlp)",
        "nlp",
    ),

    "natural language processing": (
        "natural language processing",
        "natural language processing (nlp)",
        "nlp",
    ),

    "ui ux": (
        "ui/ux",
        "ui ux",
        "ui/ux design",
        "user interface design",
        "user experience design",
    ),

    "rest api": (
        "rest api",
        "rest api development",
        "api development (rest)",
        "api development",
    ),

    "backend development": (
        "backend development",
        "backend development skills",
        "backend",
    ),

    "frontend development": (
        "frontend development",
        "front end development",
        "frontend",
    ),

    "web development": (
        "web development",
        "web application development",
    ),

    "cybersecurity": (
        "cybersecurity",
        "cyber security",
    ),

    "data structures and algorithms": (
        "data structures and algorithms",
        "dsa",
    ),

    "c++": (
        "c++",
        "c++ programming language",
    ),

    "javascript": (
        "javascript",
        "javascript programming",
    ),

    "python": (
        "python",
        "python programming",
        "python programming language",
    ),
}


# ============================================================
# PARENT TAXONOMY
# ============================================================

# Format:
#
# child -> parent
#
# IMPORTANT:
# The service only creates the relationship if BOTH skills already
# exist in the catalog.
#
# We are NOT creating missing taxonomy skills automatically here.


PARENT_SKILL_MAP = {

    # --------------------------------------------------------
    # ARTIFICIAL INTELLIGENCE
    # --------------------------------------------------------

    "machine learning":
        "artificial intelligence",

    "deep learning":
        "machine learning",

    "natural language processing":
        "artificial intelligence",

    "computer vision":
        "artificial intelligence",

    "generative ai":
        "artificial intelligence",

    "reinforcement learning":
        "machine learning",

    "supervised learning":
        "machine learning",

    "unsupervised learning":
        "machine learning",

    # --------------------------------------------------------
    # DATA
    # --------------------------------------------------------

    "data analysis":
        "data science",

    "data visualization":
        "data analysis",

    "exploratory data analysis":
        "data analysis",

    "predictive analytics":
        "data science",

    "business analytics":
        "data analysis",

    # --------------------------------------------------------
    # WEB DEVELOPMENT
    # --------------------------------------------------------

    "frontend development":
        "web development",

    "backend development":
        "web development",

    "full stack development":
        "web development",

    "react":
        "frontend development",

    "angular":
        "frontend development",

    "vue":
        "frontend development",

    "html":
        "frontend development",

    "css":
        "frontend development",

    "fastapi":
        "backend development",

    "django":
        "backend development",

    "flask":
        "backend development",

    "node.js":
        "backend development",

    "express.js":
        "backend development",

    # --------------------------------------------------------
    # API DEVELOPMENT
    # --------------------------------------------------------

    "rest api":
        "api development",

    "graphql":
        "api development",

    # --------------------------------------------------------
    # DATABASES
    # --------------------------------------------------------

    "postgresql":
        "sql",

    "mysql":
        "sql",

    "sqlite":
        "sql",

    # --------------------------------------------------------
    # CYBERSECURITY
    # --------------------------------------------------------

    "ethical hacking":
        "cybersecurity",

    "web application security testing":
        "cybersecurity",

    "network security":
        "cybersecurity",

    "network security implementation":
        "cybersecurity",

    "vulnerability assessment":
        "cybersecurity",

    "digital forensics":
        "cybersecurity",

    "penetration testing":
        "cybersecurity",

    # --------------------------------------------------------
    # ROBOTICS
    # --------------------------------------------------------

    "robotics path planning":
        "robotics",

    "robotics kinematics":
        "robotics",

    "autonomous systems":
        "robotics",

    # --------------------------------------------------------
    # GAME DEVELOPMENT
    # --------------------------------------------------------

    "game design":
        "game development",

    "game testing":
        "game development",

    # --------------------------------------------------------
    # DESIGN
    # --------------------------------------------------------

    "ui design":
        "ui/ux",

    "ux design":
        "ui/ux",

    "ui/ux prototyping":
        "ui/ux",

    "presentation design":
        "design",

    # --------------------------------------------------------
    # SOFTWARE DEVELOPMENT
    # --------------------------------------------------------

    "software testing":
        "software development",

    "software engineering":
        "software development",
}


# ============================================================
# RELATED SKILL GRAPH
# ============================================================

# These are NOT parent-child relationships.
#
# They simply mean:
#
#   "Knowing one makes the other relevant."
#
# The service stores these relationships symmetrically.


RELATED_SKILL_PAIRS = [

    # --------------------------------------------------------
    # AI / ML
    # --------------------------------------------------------

    (
        "python",
        "machine learning",
    ),

    (
        "python",
        "data science",
    ),

    (
        "machine learning",
        "data science",
    ),

    (
        "machine learning",
        "natural language processing",
    ),

    (
        "machine learning",
        "computer vision",
    ),

    (
        "deep learning",
        "computer vision",
    ),

    (
        "deep learning",
        "natural language processing",
    ),

    (
        "generative ai",
        "natural language processing",
    ),

    # --------------------------------------------------------
    # DATA / ANALYTICS
    # --------------------------------------------------------

    (
        "python",
        "data analysis",
    ),

    (
        "sql",
        "data analysis",
    ),

    (
        "sql",
        "business analytics",
    ),

    (
        "python",
        "business analytics",
    ),

    (
        "power bi",
        "data visualization",
    ),

    (
        "tableau",
        "data visualization",
    ),

    (
        "pandas",
        "data analysis",
    ),

    (
        "numpy",
        "data analysis",
    ),

    # --------------------------------------------------------
    # BACKEND
    # --------------------------------------------------------

    (
        "python",
        "fastapi",
    ),

    (
        "python",
        "django",
    ),

    (
        "python",
        "flask",
    ),

    (
        "fastapi",
        "rest api",
    ),

    (
        "django",
        "rest api",
    ),

    (
        "flask",
        "rest api",
    ),

    (
        "backend development",
        "api development",
    ),

    (
        "backend development",
        "sql",
    ),

    (
        "backend development",
        "postgresql",
    ),

    # --------------------------------------------------------
    # FRONTEND
    # --------------------------------------------------------

    (
        "javascript",
        "react",
    ),

    (
        "javascript",
        "angular",
    ),

    (
        "javascript",
        "vue",
    ),

    (
        "html",
        "css",
    ),

    (
        "html",
        "javascript",
    ),

    (
        "css",
        "javascript",
    ),

    (
        "react",
        "frontend development",
    ),

    # --------------------------------------------------------
    # FULL STACK
    # --------------------------------------------------------

    (
        "frontend development",
        "backend development",
    ),

    (
        "full stack development",
        "frontend development",
    ),

    (
        "full stack development",
        "backend development",
    ),

    # --------------------------------------------------------
    # CYBERSECURITY
    # --------------------------------------------------------

    (
        "ethical hacking",
        "penetration testing",
    ),

    (
        "ethical hacking",
        "vulnerability assessment",
    ),

    (
        "penetration testing",
        "web application security testing",
    ),

    (
        "network security",
        "cybersecurity",
    ),

    (
        "digital forensics",
        "cybersecurity",
    ),

    # --------------------------------------------------------
    # SOFTWARE DEVELOPMENT
    # --------------------------------------------------------

    (
        "data structures and algorithms",
        "problem solving",
    ),

    (
        "data structures and algorithms",
        "c++",
    ),

    (
        "software development",
        "problem solving",
    ),

    (
        "software development",
        "technical skills",
    ),

    (
        "software development",
        "sdlc",
    ),

    # --------------------------------------------------------
    # ROBOTICS
    # --------------------------------------------------------

    (
        "robotics",
        "embedded systems",
    ),

    (
        "robotics",
        "sensor technology",
    ),

    (
        "robotics",
        "autonomous systems",
    ),

    # --------------------------------------------------------
    # PRODUCT / INNOVATION
    # --------------------------------------------------------

    (
        "innovation management",
        "ideation",
    ),

    (
        "innovation management",
        "creative thinking",
    ),

    (
        "project management",
        "teamwork and collaboration",
    ),

    (
        "technical communication",
        "public speaking and presentation skills",
    ),
]


# ============================================================
# SERVICE
# ============================================================


class SkillGraphService:

    # ========================================================
    # GET CATALOG
    # ========================================================

    def get_catalog(
        self,
        db: Session,
    ) -> list[Skill]:

        return list(
            db.scalars(
                select(Skill)
            ).all()
        )

    # ========================================================
    # BUILD LOOKUP
    # ========================================================

    def build_lookup(
        self,
        skills: list[Skill],
    ) -> dict[str, Skill]:

        lookup = {}

        for skill in skills:

            normalized = (
                normalize_skill_name(
                    skill.name
                )
            )

            lookup[normalized] = skill

        return lookup

    # ========================================================
    # FIND SKILL
    # ========================================================

    def find_skill(
        self,
        lookup: dict[str, Skill],
        name: str,
    ) -> Skill | None:

        normalized = (
            normalize_skill_name(
                name
            )
        )

        # ----------------------------------------------------
        # EXACT NORMALIZED MATCH
        # ----------------------------------------------------

        skill = lookup.get(
            normalized
        )

        if skill:
            return skill

        # ----------------------------------------------------
        # ALIAS MATCH
        # ----------------------------------------------------

        for canonical, aliases in (
            SKILL_ALIASES.items()
        ):

            normalized_aliases = {
                normalize_skill_name(
                    alias
                )
                for alias in aliases
            }

            normalized_aliases.add(
                normalize_skill_name(
                    canonical
                )
            )

            if normalized in normalized_aliases:

                # Try canonical first.

                canonical_skill = (
                    lookup.get(
                        normalize_skill_name(
                            canonical
                        )
                    )
                )

                if canonical_skill:

                    return canonical_skill

                # Otherwise find any alias
                # that actually exists.

                for alias in aliases:

                    existing = lookup.get(
                        normalize_skill_name(
                            alias
                        )
                    )

                    if existing:

                        return existing

        return None

    # ========================================================
    # PARENT LINK
    # ========================================================

    def connect_parent(
        self,
        child: Skill,
        parent: Skill,
    ) -> bool:

        # Never point a skill to itself.

        if child.id == parent.id:
            return False

        # Already correct.

        if (
            child.parent_skill_id
            == parent.id
        ):

            return False

        # IMPORTANT:
        #
        # Do not silently replace an existing parent.
        #
        # A skill is allowed only one parent. If some other
        # parent already exists, we leave it alone rather than
        # corrupting manually curated data.

        if child.parent_skill_id is not None:
            return False

        child.parent = parent

        return True

    # ========================================================
    # RELATED LINK
    # ========================================================

    def connect_related(
        self,
        first: Skill,
        second: Skill,
    ) -> int:

        if first.id == second.id:
            return 0

        created = 0

        # ----------------------------------------------------
        # FIRST -> SECOND
        # ----------------------------------------------------

        if all(
            existing.id != second.id
            for existing
            in first.related_skills
        ):

            first.related_skills.append(
                second
            )

            created += 1

        # ----------------------------------------------------
        # SECOND -> FIRST
        # ----------------------------------------------------

        if all(
            existing.id != first.id
            for existing
            in second.related_skills
        ):

            second.related_skills.append(
                first
            )

            created += 1

        return created

    # ========================================================
    # BUILD GRAPH
    # ========================================================

    def build_graph(
        self,
        db: Session,
    ) -> SkillGraphBuildResult:

        result = SkillGraphBuildResult()

        skills = self.get_catalog(
            db
        )

        lookup = self.build_lookup(
            skills
        )

        # ====================================================
        # PARENT RELATIONSHIPS
        # ====================================================

        for (
            child_name,
            parent_name,
        ) in PARENT_SKILL_MAP.items():

            child = self.find_skill(
                lookup,
                child_name,
            )

            parent = self.find_skill(
                lookup,
                parent_name,
            )

            if (
                child is None
                or parent is None
            ):

                result.missing_skills += 1
                continue

            created = (
                self.connect_parent(
                    child,
                    parent,
                )
            )

            if created:

                result.parent_links_created += 1

            else:

                result.skipped_links += 1

        # ====================================================
        # RELATED RELATIONSHIPS
        # ====================================================

        for (
            first_name,
            second_name,
        ) in RELATED_SKILL_PAIRS:

            first = self.find_skill(
                lookup,
                first_name,
            )

            second = self.find_skill(
                lookup,
                second_name,
            )

            if (
                first is None
                or second is None
            ):

                result.missing_skills += 1
                continue

            created_count = (
                self.connect_related(
                    first,
                    second,
                )
            )

            if created_count:

                result.related_links_created += (
                    created_count
                )

            else:

                result.skipped_links += 1

        db.commit()

        return result

    # ========================================================
    # GET DIRECT GRAPH NEIGHBORS
    # ========================================================

    def get_neighbors(
        self,
        skill: Skill,
    ) -> set[Skill]:

        neighbors = set()

        # Parent

        if skill.parent:

            neighbors.add(
                skill.parent
            )

        # Children

        for child in skill.children:

            neighbors.add(
                child
            )

        # Related

        for related in (
            skill.related_skills
        ):

            neighbors.add(
                related
            )

        return neighbors

    # ========================================================
    # GET RELATED SKILL IDS
    # ========================================================

    def get_neighbor_ids(
        self,
        skill: Skill,
    ) -> set:

        return {
            item.id
            for item
            in self.get_neighbors(
                skill
            )
        }

    # ========================================================
    # EXPLAIN RELATIONSHIP
    # ========================================================

    def relationship_type(
        self,
        first: Skill,
        second: Skill,
    ) -> str | None:

        if first.id == second.id:

            return "exact"

        if (
            first.parent_skill_id
            == second.id
        ):

            return "parent"

        if (
            second.parent_skill_id
            == first.id
        ):

            return "child"

        if any(
            related.id == second.id
            for related
            in first.related_skills
        ):

            return "related"

        if any(
            related.id == first.id
            for related
            in second.related_skills
        ):

            return "related"

        return None


skill_graph_service = (
    SkillGraphService()
)