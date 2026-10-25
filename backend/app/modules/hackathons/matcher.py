import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill import Skill


class HackathonSkillMatcher:
    """
    Maps skill names received from external hackathon sources
    such as Unstop to skills that already exist in the
    CollabVerse Skill catalog.

    IMPORTANT:
    - Does NOT create new skills.
    - Does NOT invent skill UUIDs.
    - Does NOT scan full hackathon descriptions.
    - Exact catalog matches are preferred.
    - Known aliases can map external terminology to an
      existing CollabVerse skill.
    """

    # =====================================================
    # EXTERNAL SKILL NAME -> COLLABVERSE SKILL NAME
    # =====================================================

    SKILL_ALIASES = {
        # -------------------------
        # AI / ML / DATA
        # -------------------------

        "machine learning": "Machine Learning",
        "ml": "Machine Learning",

        "deep learning": "Deep Learning",
        "neural network": "Deep Learning",
        "neural networks": "Deep Learning",

        # Our current catalog does not contain a separate
        # Artificial Intelligence skill, so AI-related
        # external labels can fall back to Machine Learning.
        "artificial intelligence": "Machine Learning",
        "artificial intelligence ai": "Machine Learning",
        "ai": "Machine Learning",

        "data analysis": "Data Analysis",
        "data analytics": "Data Analysis",
        "data science": "Data Analysis",

        "business analytics": "Business Analytics",

        "statistics": "Statistics",
        "statistical analysis": "Statistics",

        # -------------------------
        # PROGRAMMING / TOOLS
        # -------------------------

        "python": "Python",
        "python programming": "Python",
        "python programming language": "Python",

        "sql": "SQL",
        "structured query language": "SQL",

        "react": "React",
        "reactjs": "React",
        "react js": "React",

        "fastapi": "FastAPI",

        "git": "Git",
        "version control": "Git",

        "cloud computing": "Cloud Computing",
        "cloud technologies": "Cloud Computing",

        # -------------------------
        # DSA / REASONING
        # -------------------------

        "data structures and algorithms": (
            "Data Structures and Algorithms"
        ),

        "data structure and algorithms": (
            "Data Structures and Algorithms"
        ),

        "data structures algorithms": (
            "Data Structures and Algorithms"
        ),

        "dsa": "Data Structures and Algorithms",

        "problem solving": "Problem Solving",
        "problem solving skills": "Problem Solving",
        "logical reasoning": "Problem Solving",

        "critical thinking": "Critical Thinking",

        "decision making": "Decision Making",

        # -------------------------
        # CYBERSECURITY
        # -------------------------

        "cybersecurity": "Cybersecurity",
        "cyber security": "Cybersecurity",

        "ethical hacking": "Cybersecurity",

        "penetration testing": "Cybersecurity",

        "web application security testing": (
            "Cybersecurity"
        ),

        "application security": "Cybersecurity",

        "network security": "Cybersecurity",

        "network security implementation": (
            "Cybersecurity"
        ),

        "vulnerability assessment": (
            "Cybersecurity"
        ),

        "digital forensics": "Cybersecurity",

        "cryptography": "Cybersecurity",

        # -------------------------
        # UI / UX / DESIGN
        # -------------------------

        "ui design": "UI Design",

        "user interface design": (
            "UI Design"
        ),

        "user interface ui design": (
            "UI Design"
        ),

        "ux design": "UX Design",

        "user experience design": (
            "UX Design"
        ),

        "user experience ux design": (
            "UX Design"
        ),

        "ui ux design": "UX Design",

        "ui ux prototyping": "UX Design",

        "graphic design": "Graphic Design",

        "presentation design": (
            "Presentation Skills"
        ),

        # -------------------------
        # COMMUNICATION
        # -------------------------

        "communication": "Communication",

        "communication skills": (
            "Communication"
        ),

        "technical communication": (
            "Communication"
        ),

        "written communication": (
            "Business Writing"
        ),

        "business writing": "Business Writing",

        "content writing": "Business Writing",

        "public speaking": (
            "Presentation Skills"
        ),

        "presentation skills": (
            "Presentation Skills"
        ),

        "public speaking and presentation skills": (
            "Presentation Skills"
        ),

        # -------------------------
        # TEAMWORK / LEADERSHIP
        # -------------------------

        "collaboration": "Collaboration",

        "teamwork": "Collaboration",

        "teamwork and collaboration": (
            "Collaboration"
        ),

        "leadership": "Leadership",

        "team leadership": "Leadership",

        "team management": "Team Management",

        "time management": "Time Management",

        "adaptability": "Adaptability",

        # -------------------------
        # BUSINESS
        # -------------------------

        "entrepreneurship": "Entrepreneurship",

        "innovation management": (
            "Entrepreneurship"
        ),

        "ideation": "Entrepreneurship",

        "business strategy": "Business Strategy",

        "strategic planning": "Business Strategy",

        "marketing": "Marketing",

        "digital marketing": "Marketing",

        "social media marketing": "Marketing",

        "market research": "Market Research",

        "product management": "Product Management",

        # Project Management does not currently exist
        # in our catalog. Product Management is the
        # closest existing controlled skill.
        "project management": "Product Management",

        "operations management": (
            "Operations Management"
        ),

        "finance": "Finance",

        "financial analysis": (
            "Financial Analysis"
        ),

        "economics": "Economics",

        # -------------------------
        # RESEARCH
        # -------------------------

        "research": "Research",

        "research methodology": "Research",

        "information gathering": "Research",

        "feasibility studies": "Research",

        "legal research": "Legal Research",

        # -------------------------
        # ANALYTICS TOOLS
        # -------------------------

        "excel": "Excel",

        "microsoft excel": "Excel",

        "power bi": "Power BI",

        "powerbi": "Power BI",

        "tableau": "Tableau",

        # -------------------------
        # DOMAIN
        # -------------------------

        "healthcare analytics": (
            "Healthcare Analytics"
        ),
    }

    # =====================================================
    # NORMALIZATION
    # =====================================================

    def _normalize(
        self,
        value: str | None,
    ) -> str:
        """
        Normalize external and CollabVerse skill names.

        Example:

        User Interface (UI) Design

        becomes:

        user interface ui design
        """

        if not value:
            return ""

        value = value.lower().strip()

        # Keep text inside brackets but remove
        # the bracket characters themselves.
        value = re.sub(
            r"[()\[\]{}]",
            " ",
            value,
        )

        value = value.replace(
            "&",
            " and ",
        )

        value = re.sub(
            r"[/_,]",
            " ",
            value,
        )

        value = re.sub(
            r"-",
            " ",
            value,
        )

        value = re.sub(
            r"[^a-z0-9+#.\s]",
            " ",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    # =====================================================
    # LOAD COLLABVERSE SKILL CATALOG
    # =====================================================

    def get_all_skills(
        self,
        db: Session,
    ) -> list[Skill]:
        statement = (
            select(Skill)
            .order_by(
                Skill.name.asc()
            )
        )

        return list(
            db.scalars(
                statement
            ).all()
        )

    def _build_catalog(
        self,
        skills: list[Skill],
    ) -> dict[str, Skill]:
        """
        Build:

        normalized skill name -> Skill object
        """

        return {
            self._normalize(
                skill.name
            ): skill
            for skill in skills
        }

    # =====================================================
    # MATCH ONE SKILL
    # =====================================================

    def _match_from_catalog(
        self,
        external_name: str,
        catalog: dict[str, Skill],
    ) -> Skill | None:
        normalized = self._normalize(
            external_name
        )

        if not normalized:
            return None

        # ---------------------------------------------
        # 1. EXACT MATCH
        # ---------------------------------------------

        exact_match = catalog.get(
            normalized
        )

        if exact_match:
            return exact_match

        # ---------------------------------------------
        # 2. ALIAS MATCH
        # ---------------------------------------------

        alias_target = (
            self.SKILL_ALIASES.get(
                normalized
            )
        )

        if not alias_target:
            return None

        normalized_target = self._normalize(
            alias_target
        )

        return catalog.get(
            normalized_target
        )

    def match_skill_name(
        self,
        db: Session,
        external_name: str,
    ) -> Skill | None:
        """
        Match one external skill name against
        the existing CollabVerse Skill table.
        """

        skills = self.get_all_skills(
            db
        )

        catalog = self._build_catalog(
            skills
        )

        return self._match_from_catalog(
            external_name=external_name,
            catalog=catalog,
        )

    # =====================================================
    # MATCH MANY SKILLS
    # =====================================================

    def match_skill_names(
        self,
        db: Session,
        external_names: list[str],
    ) -> list[Skill]:
        """
        Match multiple external skill names.

        Duplicate CollabVerse skills are automatically
        removed.

        Example:

        Ethical Hacking
        Network Security
        Digital Forensics

        may all map to:

        Cybersecurity

        but Cybersecurity is returned only once.
        """

        if not external_names:
            return []

        skills = self.get_all_skills(
            db
        )

        catalog = self._build_catalog(
            skills
        )

        matched: dict[str, Skill] = {}

        for external_name in external_names:
            skill = self._match_from_catalog(
                external_name=external_name,
                catalog=catalog,
            )

            if skill is None:
                continue

            matched[
                str(skill.id)
            ] = skill

        return list(
            matched.values()
        )

    # =====================================================
    # DEBUG / TESTING
    # =====================================================

    def explain_matches(
        self,
        db: Session,
        external_names: list[str],
    ) -> list[dict]:
        """
        Useful while developing the importer.

        Shows:
        external skill
        -> CollabVerse skill
        -> UUID

        Does NOT modify the database.
        """

        if not external_names:
            return []

        skills = self.get_all_skills(
            db
        )

        catalog = self._build_catalog(
            skills
        )

        results: list[dict] = []

        for external_name in external_names:
            matched = self._match_from_catalog(
                external_name=external_name,
                catalog=catalog,
            )

            results.append(
                {
                    "external_skill": (
                        external_name
                    ),
                    "matched": (
                        matched.name
                        if matched
                        else None
                    ),
                    "skill_id": (
                        str(matched.id)
                        if matched
                        else None
                    ),
                }
            )

        return results


hackathon_skill_matcher = (
    HackathonSkillMatcher()
)