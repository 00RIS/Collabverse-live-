"""
app/modules/hackathons/skill_resolver.py

Dynamic Skill Resolver for CollabVerse.

PURPOSE
-------
External opportunity sources such as Unstop provide free-text skill
names. Those names cannot be trusted as canonical Skill records because
the same concept may appear in several forms:

    AI
    Artificial Intelligence
    Artificial Intelligence (AI)

    Git
    Git Version Control

    Communication
    Communication Skills

This resolver maps external skill names into the centralized CollabVerse
Skill Catalog.

RESOLUTION ORDER
----------------
1. Exact database match
2. Normalized database match
3. Canonical alias match
4. Conservative fuzzy match
5. Safe automatic creation
6. Otherwise unresolved

IMPORTANT DESIGN RULES
----------------------
- CollabVerse is domain-neutral.
- Skills are NOT limited to Computer Science.
- Finance, mathematics, statistics, business, economics, design,
  engineering, sciences, communication and professional skills are
  first-class citizens.
- Category hints classify genuinely new skills. They are NOT a fixed
  skill catalog.
- Similar-looking skills are NOT automatically considered equivalent.
- Unknown or ambiguous skills remain unresolved instead of polluting
  the canonical catalog.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill import Skill, SkillCategory


# ============================================================
# RESULT
# ============================================================


@dataclass
class SkillResolution:
    """
    Result of resolving one external/free-text skill.

    skill:
        Canonical CollabVerse Skill object.

        None means that the resolver intentionally refused to create
        the skill because classification was not reliable enough.

    match_type:
        exact
        normalized
        alias
        fuzzy
        created
        existing
        unresolved
    """

    source_name: str
    skill: Skill | None
    match_type: str | None
    confidence: float


# ============================================================
# RESOLVER
# ============================================================


class SkillResolver:
    """
    Resolve external skill names into canonical CollabVerse Skill rows.

    This resolver intentionally prefers false negatives over false
    positives.

    It is better to leave an unfamiliar skill unresolved than to merge
    it into the wrong concept or create it under the wrong category.
    """

    # ========================================================
    # CANONICAL ALIASES
    # ========================================================
    #
    # KEY:
    #     normalized external representation
    #
    # VALUE:
    #     preferred canonical CollabVerse skill name
    #
    # IMPORTANT:
    # These should represent genuine synonyms / abbreviations.
    #
    # Do NOT use this table for merely related concepts.
    #
    # Example:
    #
    #     "ml" -> "Machine Learning"                 GOOD
    #
    #     "python development" -> "Python"           BAD
    #
    # Python Development may represent a more specific applied skill.
    # ========================================================

    ALIASES = {
        # ----------------------------------------------------
        # ARTIFICIAL INTELLIGENCE / ML
        # ----------------------------------------------------

        "ai": "Artificial Intelligence",
        "artificial intelligence ai": "Artificial Intelligence",

        "ml": "Machine Learning",
        "machine learning ml": "Machine Learning",

        "nlp": "Natural Language Processing",
        "natural language processing nlp": (
            "Natural Language Processing"
        ),

        "dl": "Deep Learning",

        # ----------------------------------------------------
        # DATA STRUCTURES / PROGRAMMING
        # ----------------------------------------------------

        "dsa": "Data Structures and Algorithms",
        "data structures algorithms": (
            "Data Structures and Algorithms"
        ),
        "data structures and algorithm": (
            "Data Structures and Algorithms"
        ),

        "cpp": "C++ Programming Language",
        "c plus plus": "C++ Programming Language",
        "c++": "C++ Programming Language",

        "c sharp": "C# Programming Language",
        "csharp": "C# Programming Language",

        "js": "JavaScript",

        # ----------------------------------------------------
        # CYBERSECURITY
        # ----------------------------------------------------

        "cyber security": "Cybersecurity",
        "cybersecurity": "Cybersecurity",

        "osint": "Open Source Intelligence (OSINT)",
        "open source intelligence": (
            "Open Source Intelligence (OSINT)"
        ),

        # ----------------------------------------------------
        # ANALYTICS
        # ----------------------------------------------------

        "data analytics": "Data Analysis",
        "data analysis": "Data Analysis",

        "powerbi": "Power BI",
        "power bi": "Power BI",

        "ms excel": "Excel",
        "microsoft excel": "Excel",

        "structured query language": "SQL",

        # ----------------------------------------------------
        # UI / UX
        # ----------------------------------------------------

        "user interface design": "UI Design",
        "ui design": "UI Design",

        "user experience design": "UX Design",
        "ux design": "UX Design",

        "user experience ux design": "UX Design",

        # ----------------------------------------------------
        # COMMUNICATION
        # ----------------------------------------------------

        "communication skills": "Communication",

        "public speaking presentation skills": (
            "Presentation Skills"
        ),
        "public speaking and presentation skills": (
            "Presentation Skills"
        ),
        "presentation skill": "Presentation Skills",

        # ----------------------------------------------------
        # COLLABORATION / TEAMWORK
        # ----------------------------------------------------

        "collaboration skills": "Collaboration",

        "teamwork collaboration": "Collaboration",
        "teamwork and collaboration": "Collaboration",
        "team collaboration": "Collaboration",

        # ----------------------------------------------------
        # REASONING
        # ----------------------------------------------------

        "problem solving skills": "Problem Solving",
        "critical thinking skills": "Critical Thinking",

        # ----------------------------------------------------
        # VERSION CONTROL
        # ----------------------------------------------------

        "git version control": "Git",

        # NOTE:
        # We intentionally do NOT map
        #
        # Version Control Systems (Git, SVN)
        #
        # to Git because the former is broader.

        # ----------------------------------------------------
        # BUSINESS
        # ----------------------------------------------------

        "business analytics": "Business Analytics",

        # ----------------------------------------------------
        # TIME MANAGEMENT
        # ----------------------------------------------------

        "time management techniques": "Time Management",

        # Time Management and Organization remains separate because
        # it explicitly includes an organizational competency.

        # ----------------------------------------------------
        # INTERNET OF THINGS
        # ----------------------------------------------------

        "iot": "Internet of Things (IoT)",
        "internet of things": "Internet of Things (IoT)",
        "internet of things iot": "Internet of Things (IoT)",

        # ----------------------------------------------------
        # CLOUD
        # ----------------------------------------------------

        "aws": "AWS (Amazon Web Services)",
        "amazon web services": "AWS (Amazon Web Services)",
        "amazon web services aws": "AWS (Amazon Web Services)",

        "azure": "Microsoft Azure",

        # ----------------------------------------------------
        # DATABASES
        # ----------------------------------------------------

        "dbms": "Database Management Systems (DBMS)",
        "database management systems": (
            "Database Management Systems (DBMS)"
        ),
        "database management system": (
            "Database Management Systems (DBMS)"
        ),

        # ----------------------------------------------------
        # SOFTWARE DEVELOPMENT LIFECYCLE
        # ----------------------------------------------------

        "sdlc": "Software Development Life Cycle (SDLC)",
        "software development lifecycle": (
            "Software Development Life Cycle (SDLC)"
        ),

        "stlc": "Software Testing Life Cycle (STLC)",
        "software testing lifecycle": (
            "Software Testing Life Cycle (STLC)"
        ),

        # ----------------------------------------------------
        # QUALITY ASSURANCE
        # ----------------------------------------------------

        "qa": "Quality Assurance (QA)",

        # Do NOT alias Software Quality Assurance to generic QA.
        # They are related but not necessarily identical.

        # ----------------------------------------------------
        # AUGMENTED / VIRTUAL REALITY
        # ----------------------------------------------------

        "ar": "Augmented Reality (AR) Development",
        "augmented reality": (
            "Augmented Reality (AR) Development"
        ),

        "vr": "Virtual Reality (VR) Development",
        "virtual reality": (
            "Virtual Reality (VR) Development"
        ),

        # ----------------------------------------------------
        # PROJECT / PRODUCT
        # ----------------------------------------------------

        "pm project management": "Project Management",

        # Never alias "PM" alone because it could mean:
        # Product Manager / Project Manager.

        # ----------------------------------------------------
        # FINANCE
        # ----------------------------------------------------

        "ma analysis": "M&A Analysis",
        "mergers acquisitions analysis": "M&A Analysis",
        "mergers and acquisitions analysis": "M&A Analysis",

        # ----------------------------------------------------
        # ROOT CAUSE ANALYSIS
        # ----------------------------------------------------

        "rca": "Root Cause Analysis (RCA)",
        "root cause analysis": "Root Cause Analysis (RCA)",

        # ----------------------------------------------------
        # USER ACCEPTANCE TESTING
        # ----------------------------------------------------

        "uat": "User Acceptance Testing (UAT)",
        "user acceptance testing": (
            "User Acceptance Testing (UAT)"
        ),
    }

    # ========================================================
    # CANONICAL TARGET FALLBACKS
    # ========================================================
    #
    # Your existing database currently contains some older canonical
    # variants such as:
    #
    #     Artificial Intelligence (AI)
    #     Natural Language Processing (NLP)
    #
    # We do NOT automatically rename database rows here.
    #
    # Instead, if the preferred new canonical name is absent, we allow
    # the resolver to reuse a known legacy equivalent.
    #
    # This lets future ingestion become cleaner WITHOUT breaking
    # existing foreign keys.
    # ========================================================

    CANONICAL_FALLBACKS = {
        "Artificial Intelligence": (
            "Artificial Intelligence (AI)",
        ),

        "Natural Language Processing": (
            "Natural Language Processing (NLP)",
        ),

        "UI Design": (
            "User Interface (UI) Design",
        ),

        "UX Design": (
            "User Experience (UX) Design",
            "User Experience (UX)",
        ),

        "Communication": (
            "Communication Skills",
        ),

        "Collaboration": (
            "Collaboration Skills",
        ),

        "Git": (
            "Git Version Control",
        ),

        "Time Management": (
            "Time Management Techniques",
        ),
    }

    # ========================================================
    # CATEGORY HINTS
    # ========================================================
    #
    # IMPORTANT:
    #
    # These are NOT the CollabVerse skill catalog.
    #
    # They are evidence used only when a genuinely new external skill
    # needs a broad SkillCategory.
    #
    # CollabVerse is intentionally multidisciplinary.
    # ========================================================

    CATEGORY_HINTS = {
        # ====================================================
        # TECHNICAL
        # ====================================================

        SkillCategory.TECHNICAL: [
            # Programming
            "python",
            "java",
            "javascript",
            "typescript",
            "c++",
            "c#",
            "programming",
            "coding",

            # Software development
            "development",
            "developer",
            "software",
            "software engineering",
            "sdlc",
            "stlc",
            "debugging",

            # Web
            "web",
            "frontend",
            "backend",
            "full stack",
            "fullstack",
            "react",
            "angular",
            "vue",
            "node",
            "node.js",

            # APIs
            "api",
            "rest api",
            "graphql",
            "fastapi",
            "django",
            "flask",

            # Databases
            "database",
            "dbms",
            "sql",
            "postgresql",
            "mysql",
            "mongodb",

            # Cloud / DevOps
            "cloud",
            "aws",
            "azure",
            "gcp",
            "docker",
            "kubernetes",
            "devops",
            "ci cd",

            # Version control
            "git",
            "version control",

            # Artificial Intelligence
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "natural language processing",
            "nlp",
            "computer vision",
            "generative ai",
            "reinforcement learning",
            "neural network",

            # AI frameworks
            "tensorflow",
            "pytorch",
            "scikit learn",

            # Cybersecurity
            "cybersecurity",
            "cyber security",
            "ethical hacking",
            "penetration testing",
            "vulnerability",
            "network security",
            "application security",
            "web application security",
            "digital forensics",
            "reverse engineering",
            "osint",
            "open source intelligence",
            "wireshark",

            # Blockchain
            "blockchain",
            "smart contract",
            "ethereum",
            "consensus mechanism",

            # IoT
            "internet of things",
            "iot",
            "iot security",
            "iot sensor",
            "iot platform",

            # Embedded / electronics
            "embedded",
            "microcontroller",
            "arduino",
            "fpga",
            "sensor integration",

            # Robotics
            "robotics",
            "robot operating system",
            "ros",
            "robotics kinematics",
            "robotics path planning",
            "robotics control",

            # Quantum
            "quantum computing",
            "quantum control",
            "qiskit",

            # Mobile
            "mobile application development",
            "android development",
            "ios development",
            "flutter",
            "react native",

            # AR / VR
            "augmented reality",
            "virtual reality",
            "ar development",
            "vr development",

            # Testing / QA
            "software testing",
            "system testing",
            "performance testing",
            "manual testing",
            "usability testing",
            "quality assurance",
            "user acceptance testing",

            # General technical
            "technical skills",
        ],

        # ====================================================
        # ANALYTICAL / MATHEMATICS / STATISTICS
        # ====================================================

        SkillCategory.ANALYTICAL: [
            # General analysis
            "analysis",
            "analytics",
            "analytical",

            # Mathematics
            "mathematics",
            "mathematical",
            "algebra",
            "linear algebra",
            "calculus",
            "geometry",
            "trigonometry",
            "discrete mathematics",
            "numerical methods",
            "operations research",

            # Probability / statistics
            "statistics",
            "statistical",
            "probability",
            "regression analysis",
            "hypothesis testing",
            "statistical modeling",
            "statistical modelling",
            "inferential statistics",
            "descriptive statistics",

            # Quantitative
            "quantitative analysis",
            "quantitative methods",
            "quantitative research",

            # Data analysis
            "data analysis",
            "data analytics",
            "data wrangling",
            "data extraction",
            "data visualization",
            "exploratory data analysis",
            "eda",

            # Predictive
            "predictive analytics",
            "predictive modeling",
            "predictive modelling",
            "forecasting",
            "time series",
            "time series analysis",

            # Optimization
            "optimization",
            "portfolio optimization",

            # Research
            "research methods",
            "research skills",
            "information gathering",
            "online research",

            # Reasoning
            "problem solving",
            "logical reasoning",
            "critical thinking",

            # Business / requirements analysis
            "requirements analysis",
            "root cause analysis",
            "feasibility studies",

            # Financial analysis
            "financial analysis",
            "fundamental analysis",
            "risk analysis",
            "m&a analysis",
            "valuation analysis",

            # Specialized analytics
            "sentiment analysis",
            "text analytics",
            "image analysis",
            "threat analysis",

            # Engineering analysis
            "finite element analysis",
            "computational modeling",
            "computational modelling",

            # Analytics tools
            "excel",
            "power bi",
            "tableau",
        ],

        # ====================================================
        # BUSINESS / FINANCE / ECONOMICS / MANAGEMENT
        # ====================================================

        SkillCategory.BUSINESS: [
            # General business
            "business",
            "business acumen",
            "business planning",
            "business process",
            "business strategy",

            # Finance
            "finance",
            "financial",
            "corporate finance",
            "financial modeling",
            "financial modelling",
            "financial markets",
            "investment",
            "investment analysis",
            "investment banking",
            "portfolio management",
            "asset management",
            "wealth management",
            "derivatives",
            "risk management",
            "valuation",
            "banking",
            "accounting",
            "audit",
            "taxation",

            # Economics
            "economics",
            "microeconomics",
            "macroeconomics",
            "econometrics",
            "economic research",

            # Marketing
            "marketing",
            "digital marketing",
            "social media marketing",
            "market research",
            "brand management",
            "branding",
            "advertising",
            "consumer behavior",
            "consumer behaviour",

            # Sales
            "sales",
            "sales management",
            "business development",
            "customer acquisition",

            # Strategy
            "strategy",
            "corporate strategy",
            "go to market",
            "go-to-market",

            # Product
            "product management",
            "product strategy",
            "product development",

            # Operations
            "operations",
            "operations management",
            "supply chain",
            "supply chain management",
            "logistics",
            "procurement",

            # Entrepreneurship / innovation
            "entrepreneurship",
            "innovation management",
            "startup",
            "venture capital",

            # Consulting
            "consulting",
            "management consulting",
            "financial consulting",

            # Human resources
            "human resources",
            "hr management",
            "talent management",
            "recruitment",
        ],

        # ====================================================
        # COMMUNICATION
        # ====================================================

        SkillCategory.COMMUNICATION: [
            "communication",
            "communication skills",
            "business communication",
            "team communication",
            "technical communication",
            "wireless communication",

            "presentation",
            "presentation skills",
            "public speaking",
            "technical presentations",

            "writing",
            "written communication",
            "business writing",
            "technical writing",
            "content writing",
            "copywriting",

            "storytelling",
            "visual storytelling",

            "nonverbal communication",
            "verbal communication",
        ],

        # ====================================================
        # LEADERSHIP / MANAGEMENT
        # ====================================================

        SkillCategory.LEADERSHIP: [
            "leadership",
            "team leadership",
            "team management",
            "people management",

            "decision making",
            "data driven decision making",
            "data-driven decision making",

            "project management",
            "program management",

            "strategic leadership",
            "change management",

            "delegation",
            "conflict management",
        ],

        # ====================================================
        # DESIGN / CREATIVE
        # ====================================================

        SkillCategory.DESIGN: [
            # General
            "design",
            "design thinking",

            # UI / UX
            "ui",
            "ux",
            "ui design",
            "ux design",
            "ui ux",
            "user interface",
            "user experience",
            "prototyping",
            "prototype",
            "figma",
            "design systems",
            "inclusive design",

            # Graphic / visual
            "graphic design",
            "visual design",
            "layout design",
            "illustration",
            "typography",

            # Media
            "animation",
            "motion graphics",
            "video editing",
            "photography",

            # Product / industrial
            "product design",
            "industrial design",

            # Game
            "game design",

            # Engineering design
            "aircraft design",
            "circuit design",
            "machine design",
            "mechanical design",
            "computer aided design",
            "cad",

            # Assessment / solution
            "assessment design",
            "solution design",
            "test case design",
        ],

        # ====================================================
        # DOMAIN KNOWLEDGE
        # ====================================================

        SkillCategory.DOMAIN_KNOWLEDGE: [
            # Science
            "physics",
            "chemistry",
            "biology",
            "biotechnology",
            "environmental science",
            "materials science",

            # Healthcare
            "healthcare",
            "healthcare systems",
            "medicine",
            "medical",
            "clinical",
            "pharmaceutical",
            "pharma",

            # Legal
            "legal",
            "law",
            "legal research",
            "intellectual property",

            # Agriculture
            "agriculture",
            "agricultural",
            "agritech",

            # Aerospace / aviation
            "aerospace",
            "aviation",
            "aerospace industry",

            # Urban
            "urban planning",
            "smart city",
            "smart city technologies",

            # Fintech
            #
            # Fintech is treated as domain knowledge rather than
            # generic business because it represents an industry
            # domain connecting finance and technology.
            "fintech",

            # Energy
            "energy",
            "renewable energy",
            "sustainability",

            # Manufacturing
            "manufacturing",
            "automotive",
            "automobile",

            # Domain research
            "domain research",
            "industry knowledge",
        ],

        # ====================================================
        # SOFT SKILLS
        # ====================================================

        SkillCategory.SOFT_SKILLS: [
            "adaptability",

            "teamwork",
            "collaboration",
            "collaboration skills",

            "creativity",
            "creative thinking",
            "ideation",

            "time management",
            "organization",
            "organisation",

            "interpersonal",
            "interpersonal skills",

            "negotiation",

            "emotional intelligence",

            "attention to detail",

            "work ethic",

            "resilience",
        ],
    }

    # ========================================================
    # NORMALIZATION
    # ========================================================

    def normalize_name(
        self,
        name: str,
    ) -> str:
        """
        Normalize a skill name for comparison.

        Examples:

            Data Structures & Algorithms
                ->
            data structures and algorithms

            Artificial Intelligence (AI)
                ->
            artificial intelligence ai

            Go-to-Market Strategy
                ->
            go to market strategy

        Normalization is intentionally syntactic.

        It does NOT decide that two semantically related skills are
        equivalent.
        """

        if not name:
            return ""

        value = name.strip().casefold()

        value = value.replace(
            "&",
            " and ",
        )

        # Convert "+" into words only when isolated enough to avoid
        # destroying C++.
        value = re.sub(
            r"(?<!\+)\+(?!\+)",
            " plus ",
            value,
        )

        # Preserve C++ and C# before punctuation cleanup.
        value = value.replace(
            "c++",
            " cpp ",
        )

        value = value.replace(
            "c#",
            " csharp ",
        )

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
            r"[.!?]+",
            " ",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        value = value.strip()

        # Restore canonical comparison tokens.
        value = re.sub(
            r"\bcpp\b",
            "c++",
            value,
        )

        value = re.sub(
            r"\bcsharp\b",
            "c#",
            value,
        )

        return value.strip()

    # ========================================================
    # DISPLAY NAME
    # ========================================================

    def clean_display_name(
        self,
        name: str,
    ) -> str:
        """
        Clean an external skill name before storage.

        We intentionally do NOT remove generic words such as
        "Skill" or "Skills".

        Examples:

            Technical Skills

        remains:

            Technical Skills

        Genuine synonyms are handled by canonical alias resolution.
        """

        if not name:
            return ""

        value = re.sub(
            r"\s+",
            " ",
            name,
        ).strip()

        return value[:150]

    # ========================================================
    # DATABASE CATALOG
    # ========================================================

    def get_catalog(
        self,
        db: Session,
    ) -> list[Skill]:
        """
        Return the current canonical skill catalog.
        """

        statement = (
            select(Skill)
            .order_by(Skill.name)
        )

        return list(
            db.scalars(
                statement
            ).all()
        )

    # ========================================================
    # EXACT MATCH
    # ========================================================

    def find_exact(
        self,
        catalog: list[Skill],
        external_name: str,
    ) -> Skill | None:

        target = (
            external_name
            .strip()
            .casefold()
        )

        for skill in catalog:

            existing = (
                skill.name
                .strip()
                .casefold()
            )

            if existing == target:
                return skill

        return None

    # ========================================================
    # NORMALIZED MATCH
    # ========================================================

    def find_normalized(
        self,
        catalog: list[Skill],
        external_name: str,
    ) -> Skill | None:

        target = self.normalize_name(
            external_name
        )

        if not target:
            return None

        for skill in catalog:

            existing = self.normalize_name(
                skill.name
            )

            if existing == target:
                return skill

        return None

    # ========================================================
    # FIND CANONICAL TARGET
    # ========================================================

    def find_canonical_target(
        self,
        catalog: list[Skill],
        canonical_name: str,
    ) -> Skill | None:
        """
        Find the preferred canonical skill.

        If the preferred canonical row does not exist yet, known legacy
        database representations may be reused.

        This prevents new duplicates while avoiding destructive database
        changes during ingestion.
        """

        exact = self.find_exact(
            catalog,
            canonical_name,
        )

        if exact:
            return exact

        normalized = self.find_normalized(
            catalog,
            canonical_name,
        )

        if normalized:
            return normalized

        fallbacks = (
            self.CANONICAL_FALLBACKS.get(
                canonical_name,
                (),
            )
        )

        for fallback_name in fallbacks:

            exact_fallback = self.find_exact(
                catalog,
                fallback_name,
            )

            if exact_fallback:
                return exact_fallback

            normalized_fallback = (
                self.find_normalized(
                    catalog,
                    fallback_name,
                )
            )

            if normalized_fallback:
                return normalized_fallback

        return None

    # ========================================================
    # ALIAS MATCH
    # ========================================================

    def find_alias(
        self,
        catalog: list[Skill],
        external_name: str,
    ) -> Skill | None:

        normalized = self.normalize_name(
            external_name
        )

        canonical_name = self.ALIASES.get(
            normalized
        )

        if not canonical_name:
            return None

        return self.find_canonical_target(
            catalog,
            canonical_name,
        )

    # ========================================================
    # CANONICAL NAME FOR CREATION
    # ========================================================

    def canonical_name_for_creation(
        self,
        external_name: str,
    ) -> str:
        """
        Return the preferred name to use if a genuinely new Skill must
        be created.

        Example:

            AI
                ->
            Artificial Intelligence

        This happens before INSERT, preventing aliases from becoming
        separate catalog rows.
        """

        normalized = self.normalize_name(
            external_name
        )

        canonical = self.ALIASES.get(
            normalized
        )

        if canonical:
            return canonical

        return self.clean_display_name(
            external_name
        )

    # ========================================================
    # FUZZY MATCH SAFETY
    # ========================================================

    def fuzzy_candidate_is_safe(
        self,
        target: str,
        candidate: str,
    ) -> bool:
        """
        Additional safety checks for fuzzy matching.

        SequenceMatcher alone can produce dangerous matches such as:

            Java
            JavaScript

        or:

            Product Management
            Project Management

        We therefore reject several structurally suspicious cases.
        """

        if not target or not candidate:
            return False

        target_words = target.split()
        candidate_words = candidate.split()

        # Very short one-token names are risky.
        if (
            len(target_words) == 1
            and len(candidate_words) == 1
            and (
                len(target) <= 4
                or len(candidate) <= 4
            )
        ):
            return False

        # Do not fuzzy-match a short skill merely because it is a
        # substring of a much larger skill.
        if (
            target in candidate
            or candidate in target
        ):
            shorter = min(
                len(target),
                len(candidate),
            )

            longer = max(
                len(target),
                len(candidate),
            )

            if (
                shorter > 0
                and longer / shorter >= 1.6
            ):
                return False

        # Product Management vs Project Management is a classic
        # high-similarity false positive. More generally, if both
        # names contain "management" but their leading concept differs,
        # require exact leading concepts.
        if (
            "management" in target_words
            and "management" in candidate_words
            and target_words
            and candidate_words
            and target_words[0] != candidate_words[0]
        ):
            return False

        return True

    # ========================================================
    # FUZZY MATCH
    # ========================================================

    def find_fuzzy(
        self,
        catalog: list[Skill],
        external_name: str,
        threshold: float = 0.95,
    ) -> tuple[Skill | None, float]:
        """
        Very conservative fuzzy matching.

        Fuzzy matching exists mainly for punctuation, spacing and small
        spelling variations that normalization did not already solve.

        It is NOT semantic matching.

        Semantic relationships belong in the Skill Knowledge Graph.
        """

        target = self.normalize_name(
            external_name
        )

        if not target:
            return None, 0.0

        best_skill = None
        best_score = 0.0

        for skill in catalog:

            existing = self.normalize_name(
                skill.name
            )

            if not existing:
                continue

            if not self.fuzzy_candidate_is_safe(
                target,
                existing,
            ):
                continue

            score = SequenceMatcher(
                None,
                target,
                existing,
            ).ratio()

            if score > best_score:
                best_score = score
                best_skill = skill

        if best_score >= threshold:
            return best_skill, best_score

        return None, best_score

    # ========================================================
    # CATEGORY KEYWORD MATCHING
    # ========================================================

    def category_keyword_matches(
        self,
        normalized_name: str,
        normalized_keyword: str,
    ) -> bool:
        """
        Determine whether a category hint actually occurs in a skill.

        Single-word hints use token matching.

        Multi-word hints use phrase matching.

        This prevents short hints such as:

            ui
            ux
            git
            ar

        from accidentally matching unrelated words.
        """

        if not normalized_name:
            return False

        if not normalized_keyword:
            return False

        keyword_words = (
            normalized_keyword.split()
        )

        if len(keyword_words) == 1:

            name_words = set(
                normalized_name.split()
            )

            return (
                normalized_keyword
                in name_words
            )

        return (
            normalized_keyword
            in normalized_name
        )

    # ========================================================
    # CATEGORY SCORING
    # ========================================================

    def category_scores(
        self,
        name: str,
    ) -> dict[SkillCategory, int]:
        """
        Return raw category evidence scores.

        Longer phrases receive more weight because they carry more
        semantic information.

        Example:

            "financial modeling"

        is stronger evidence than merely seeing:

            "modeling"
        """

        normalized = self.normalize_name(
            name
        )

        if not normalized:
            return {}

        scores: dict[
            SkillCategory,
            int,
        ] = {}

        for (
            category,
            keywords,
        ) in self.CATEGORY_HINTS.items():

            score = 0
            matched_keywords = set()

            for keyword in keywords:

                normalized_keyword = (
                    self.normalize_name(
                        keyword
                    )
                )

                if not normalized_keyword:
                    continue

                if normalized_keyword in matched_keywords:
                    continue

                matched = (
                    self.category_keyword_matches(
                        normalized,
                        normalized_keyword,
                    )
                )

                if not matched:
                    continue

                matched_keywords.add(
                    normalized_keyword
                )

                keyword_words = (
                    normalized_keyword.split()
                )

                if len(keyword_words) >= 3:
                    score += 5

                elif len(keyword_words) == 2:
                    score += 3

                else:
                    score += 1

            if score > 0:
                scores[category] = score

        return scores

    # ========================================================
    # CATEGORY INFERENCE
    # ========================================================

    def infer_category(
        self,
        name: str,
    ) -> SkillCategory | None:
        """
        Infer the broad category of a genuinely new skill.

        Safety rules:

        - no evidence -> unresolved
        - exact tie -> unresolved
        - weak competing evidence -> unresolved
        - no automatic TECHNICAL fallback
        """

        scores = self.category_scores(
            name
        )

        if not scores:
            return None

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        highest_category = ranked[0][0]
        highest_score = ranked[0][1]

        # Exact tie between top categories.
        winners = [
            category
            for category, score
            in ranked
            if score == highest_score
        ]

        if len(winners) != 1:
            return None

        # If two categories have meaningful competing evidence and
        # their scores are too close, refuse automatic classification.
        if len(ranked) >= 2:

            second_score = ranked[1][1]

            if (
                second_score >= 3
                and highest_score - second_score <= 1
            ):
                return None

        return highest_category

    # ========================================================
    # FINAL DUPLICATE CHECK
    # ========================================================

    def find_existing_before_create(
        self,
        db: Session,
        display_name: str,
    ) -> Skill | None:
        """
        Final duplicate guard immediately before INSERT.

        Pending Skill rows are flushed first so skills created earlier
        in the same sync are visible.
        """

        db.flush()

        catalog = self.get_catalog(
            db
        )

        exact = self.find_exact(
            catalog,
            display_name,
        )

        if exact:
            return exact

        normalized = self.find_normalized(
            catalog,
            display_name,
        )

        if normalized:
            return normalized

        alias = self.find_alias(
            catalog,
            display_name,
        )

        if alias:
            return alias

        return None

    # ========================================================
    # CREATE SKILL
    # ========================================================

    def create_skill(
        self,
        db: Session,
        external_name: str,
    ) -> tuple[Skill | None, bool]:
        """
        Create a genuinely new skill.

        Returns:

            (Skill, True)
                newly created

            (Skill, False)
                duplicate/canonical skill discovered before creation

            (None, False)
                category could not safely be determined
        """

        display_name = (
            self.canonical_name_for_creation(
                external_name
            )
        )

        if not display_name:
            return None, False

        # ----------------------------------------------------
        # DUPLICATE / CANONICAL GUARD
        # ----------------------------------------------------

        existing = (
            self.find_existing_before_create(
                db,
                display_name,
            )
        )

        if existing:
            return existing, False

        # ----------------------------------------------------
        # CATEGORY
        # ----------------------------------------------------

        category = self.infer_category(
            display_name
        )

        if category is None:
            return None, False

        # ----------------------------------------------------
        # CREATE
        # ----------------------------------------------------

        skill = Skill(
            name=display_name,
            category=category,
            description=(
                "Automatically discovered from "
                "an external opportunity source."
            ),
        )

        db.add(
            skill
        )

        # Assign UUID / INSERT without committing the outer
        # transaction.
        db.flush()

        return skill, True

    # ========================================================
    # RESOLVE ONE
    # ========================================================

    def resolve(
        self,
        db: Session,
        external_name: str,
        *,
        allow_create: bool = True,
    ) -> SkillResolution | None:
        """
        Resolve one external skill name.
        """

        if not external_name:
            return None

        external_name = (
            external_name.strip()
        )

        if not external_name:
            return None

        # Make pending skills visible.
        db.flush()

        catalog = self.get_catalog(
            db
        )

        # ----------------------------------------------------
        # 1. EXACT
        # ----------------------------------------------------

        exact = self.find_exact(
            catalog,
            external_name,
        )

        if exact:

            return SkillResolution(
                source_name=external_name,
                skill=exact,
                match_type="exact",
                confidence=1.0,
            )

        # ----------------------------------------------------
        # 2. NORMALIZED
        # ----------------------------------------------------

        normalized = self.find_normalized(
            catalog,
            external_name,
        )

        if normalized:

            return SkillResolution(
                source_name=external_name,
                skill=normalized,
                match_type="normalized",
                confidence=0.99,
            )

        # ----------------------------------------------------
        # 3. CANONICAL ALIAS
        # ----------------------------------------------------

        alias = self.find_alias(
            catalog,
            external_name,
        )

        if alias:

            return SkillResolution(
                source_name=external_name,
                skill=alias,
                match_type="alias",
                confidence=0.99,
            )

        # ----------------------------------------------------
        # 4. FUZZY
        # ----------------------------------------------------

        (
            fuzzy_skill,
            fuzzy_score,
        ) = self.find_fuzzy(
            catalog,
            external_name,
        )

        if fuzzy_skill:

            return SkillResolution(
                source_name=external_name,
                skill=fuzzy_skill,
                match_type="fuzzy",
                confidence=fuzzy_score,
            )

        # ----------------------------------------------------
        # CREATION DISABLED
        # ----------------------------------------------------

        if not allow_create:
            return None

        # ----------------------------------------------------
        # 5. SAFE AUTOMATIC CREATION
        # ----------------------------------------------------

        (
            new_skill,
            created,
        ) = self.create_skill(
            db,
            external_name,
        )

        if new_skill is None:

            return SkillResolution(
                source_name=external_name,
                skill=None,
                match_type="unresolved",
                confidence=0.0,
            )

        if created:

            return SkillResolution(
                source_name=external_name,
                skill=new_skill,
                match_type="created",
                confidence=1.0,
            )

        return SkillResolution(
            source_name=external_name,
            skill=new_skill,
            match_type="existing",
            confidence=1.0,
        )

    # ========================================================
    # RESOLVE MANY
    # ========================================================

    def resolve_many(
        self,
        db: Session,
        external_names: list[str],
        *,
        allow_create: bool = True,
    ) -> list[SkillResolution]:
        """
        Resolve multiple external skill names.

        Duplicate canonical skills are returned only once.
        """

        results: list[
            SkillResolution
        ] = []

        seen_skill_ids = set()
        seen_unresolved = set()

        for external_name in external_names:

            if not external_name:
                continue

            result = self.resolve(
                db,
                external_name,
                allow_create=allow_create,
            )

            if result is None:
                continue

            # ------------------------------------------------
            # UNRESOLVED
            # ------------------------------------------------

            if result.skill is None:

                normalized_source = (
                    self.normalize_name(
                        result.source_name
                    )
                )

                if (
                    normalized_source
                    in seen_unresolved
                ):
                    continue

                seen_unresolved.add(
                    normalized_source
                )

                results.append(
                    result
                )

                continue

            # ------------------------------------------------
            # RESOLVED
            # ------------------------------------------------

            skill_id = result.skill.id

            if skill_id in seen_skill_ids:
                continue

            seen_skill_ids.add(
                skill_id
            )

            results.append(
                result
            )

        return results

    # ========================================================
    # EXPLAIN / DEBUG
    # ========================================================

    def explain(
        self,
        db: Session,
        external_names: list[str],
        *,
        allow_create: bool = False,
    ) -> list[dict]:
        """
        Human-readable resolver output useful for testing.

        No database writes occur when allow_create=False.
        """

        results = []

        for name in external_names:

            result = self.resolve(
                db,
                name,
                allow_create=allow_create,
            )

            if (
                result is None
                or result.skill is None
            ):

                results.append(
                    {
                        "source": name,
                        "resolved": None,
                        "skill_id": None,
                        "category": None,
                        "match_type": (
                            result.match_type
                            if result
                            else None
                        ),
                        "confidence": (
                            round(
                                result.confidence,
                                3,
                            )
                            if result
                            else 0.0
                        ),
                    }
                )

                continue

            results.append(
                {
                    "source": (
                        result.source_name
                    ),
                    "resolved": (
                        result.skill.name
                    ),
                    "skill_id": str(
                        result.skill.id
                    ),
                    "category": (
                        result.skill
                        .category
                        .value
                    ),
                    "match_type": (
                        result.match_type
                    ),
                    "confidence": round(
                        result.confidence,
                        3,
                    ),
                }
            )

        return results


skill_resolver = SkillResolver()