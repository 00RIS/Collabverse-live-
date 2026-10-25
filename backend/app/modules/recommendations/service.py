from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user import User
from app.modules.recommendations.repositories import RecommendationRepository


class RecommendationService:

    # =========================================================
    # COMMON HELPERS
    # =========================================================

    def _repo(
        self,
        db: Session,
    ) -> RecommendationRepository:
        return RecommendationRepository(db)

    def _get_skill_names(
        self,
        repo: RecommendationRepository,
        skill_ids: set,
    ) -> list[str]:
        names = []

        for skill_id in skill_ids:
            skill = repo.get_skill(skill_id)

            if skill:
                names.append(skill.name)

        names.sort()
        return names

    def _utc_datetime(self, value):
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )

    # =========================================================
    # SKILL GRAPH
    # =========================================================

    def _build_skill_graph(
        self,
        repo: RecommendationRepository,
        skill_ids: set,
    ) -> dict:
        graph = {}

        for skill_id in skill_ids:
            skill = repo.get_skill(skill_id)

            if not skill:
                continue

            parent_id = getattr(
                skill,
                "parent_skill_id",
                None,
            )

            child_ids = {
                child.id
                for child in (
                    getattr(
                        skill,
                        "children",
                        [],
                    )
                    or []
                )
            }

            related_ids = {
                related.id
                for related in (
                    getattr(
                        skill,
                        "related_skills",
                        [],
                    )
                    or []
                )
            }

            graph[skill.id] = {
                "skill": skill,
                "parent_id": parent_id,
                "child_ids": child_ids,
                "related_ids": related_ids,
            }

        return graph

    def _semantic_skill_relation(
        self,
        user_skill_id,
        opportunity_skill_id,
        graph: dict,
    ) -> tuple[float, str | None]:

        # Exact skill
        if user_skill_id == opportunity_skill_id:
            return 1.0, "exact"

        user_node = graph.get(user_skill_id)
        opportunity_node = graph.get(
            opportunity_skill_id
        )

        if not user_node or not opportunity_node:
            return 0.0, None

        # Direct parent / child
        if (
            user_node["parent_id"]
            == opportunity_skill_id
            or opportunity_node["parent_id"]
            == user_skill_id
            or opportunity_skill_id
            in user_node["child_ids"]
            or user_skill_id
            in opportunity_node["child_ids"]
        ):
            return 0.80, "hierarchy"

        # Direct related skill
        if (
            opportunity_skill_id
            in user_node["related_ids"]
            or user_skill_id
            in opportunity_node["related_ids"]
        ):
            return 0.65, "related"

        return 0.0, None

    def _score_semantic_skills(
        self,
        user_skill_ids: set,
        opportunity_skill_ids: set,
        graph: dict,
        max_points: float,
    ) -> dict:

        if (
            not user_skill_ids
            or not opportunity_skill_ids
        ):
            return {
                "points": 0.0,
                "strength": 0.0,
                "exact": [],
                "hierarchy": [],
                "related": [],
            }

        exact_matches = []
        hierarchy_matches = []
        related_matches = []

        total_strength = 0.0

        # Each required opportunity skill is scored once.
        # We choose the strongest user-skill relationship.
        for opportunity_skill_id in opportunity_skill_ids:

            best_strength = 0.0
            best_relation = None
            best_user_skill_id = None

            for user_skill_id in user_skill_ids:

                strength, relation = (
                    self._semantic_skill_relation(
                        user_skill_id,
                        opportunity_skill_id,
                        graph,
                    )
                )

                if strength > best_strength:
                    best_strength = strength
                    best_relation = relation
                    best_user_skill_id = (
                        user_skill_id
                    )

                if best_strength == 1.0:
                    break

            if best_strength <= 0:
                continue

            total_strength += best_strength

            match = {
                "user_skill_id": best_user_skill_id,
                "opportunity_skill_id": (
                    opportunity_skill_id
                ),
                "strength": best_strength,
            }

            if best_relation == "exact":
                exact_matches.append(match)

            elif best_relation == "hierarchy":
                hierarchy_matches.append(match)

            elif best_relation == "related":
                related_matches.append(match)

        ratio = (
            total_strength
            / len(opportunity_skill_ids)
        )

        ratio = min(ratio, 1.0)

        points = ratio * max_points

        return {
            "points": round(points, 2),
            "strength": round(ratio, 4),
            "exact": exact_matches,
            "hierarchy": hierarchy_matches,
            "related": related_matches,
        }

    def _semantic_match_text(
        self,
        repo: RecommendationRepository,
        matches: list,
        relation_type: str,
        learning: bool = False,
    ) -> str | None:

        if not matches:
            return None

        labels = []

        for match in matches[:5]:

            user_skill = repo.get_skill(
                match["user_skill_id"]
            )

            opportunity_skill = repo.get_skill(
                match["opportunity_skill_id"]
            )

            if (
                not user_skill
                or not opportunity_skill
            ):
                continue

            if relation_type == "exact":
                labels.append(
                    opportunity_skill.name
                )

            elif relation_type == "hierarchy":
                labels.append(
                    f"{user_skill.name} → "
                    f"{opportunity_skill.name}"
                )

            elif relation_type == "related":
                labels.append(
                    f"{user_skill.name} ↔ "
                    f"{opportunity_skill.name}"
                )

        if not labels:
            return None

        joined = ", ".join(labels)

        if learning:

            if relation_type == "exact":
                return (
                    "Matches skills you are "
                    f"learning: {joined}"
                )

            if relation_type == "hierarchy":
                return (
                    "Connects your learning skills "
                    "through the skill hierarchy: "
                    f"{joined}"
                )

            return (
                "Connects to skills you are "
                f"learning: {joined}"
            )

        if relation_type == "exact":
            return (
                "Exact skill match: "
                + joined
            )

        if relation_type == "hierarchy":
            return (
                "Skill specialization match: "
                + joined
            )

        return (
            "Related skill match: "
            + joined
        )

    # =========================================================
    # PROJECT RECOMMENDATIONS
    # =========================================================

    def recommend_projects(
        self,
        db: Session,
        current_user: User,
        limit: int = 10,
    ) -> dict:

        repo = self._repo(db)

        student = repo.get_student_profile(
            current_user.id
        )

        current_skill_ids = set()
        learning_skill_ids = set()

        if student:
            student_skills = (
                repo.get_student_skills(
                    student
                )
            )

            current_skill_ids = {
                item.skill_id
                for item in student_skills
            }

        learning_skills = (
            repo.get_learning_skills(
                current_user.id
            )
        )

        learning_skill_ids = {
            item.skill_id
            for item in learning_skills
        }

        interests = repo.get_interests(
            current_user.id
        )

        interest_terms = set()

        for interest in interests:

            value = getattr(
                interest.category,
                "value",
                interest.category,
            )

            if value:
                interest_terms.add(
                    str(value)
                    .replace("_", " ")
                    .lower()
                    .strip()
                )

        goals = repo.get_goals(
            current_user.id
        )

        goal_terms = set()

        for goal in goals:

            text = getattr(
                goal,
                "title",
                None,
            )

            if text:
                goal_terms.add(
                    text.lower().strip()
                )

            goal_type = getattr(
                goal,
                "goal_type",
                None,
            )

            if goal_type is not None:

                value = getattr(
                    goal_type,
                    "value",
                    goal_type,
                )

                if value:
                    goal_terms.add(
                        str(value)
                        .replace("_", " ")
                        .lower()
                        .strip()
                    )

        projects = repo.get_open_projects(
            current_user.id
        )

        ranked = []

        for project in projects:

            score = 0.0
            reasons = []

            project_skill_ids = {
                item.skill_id
                for item in project.skills
            }

            # CURRENT SKILLS
            matched_current = (
                current_skill_ids
                & project_skill_ids
            )

            if matched_current:

                points = min(
                    40.0,
                    len(matched_current) * 15.0,
                )

                score += points

                skill_names = (
                    self._get_skill_names(
                        repo,
                        matched_current,
                    )
                )

                reasons.append(
                    {
                        "type": "skill_match",
                        "text": (
                            "Matches your skills: "
                            + ", ".join(
                                skill_names
                            )
                        ),
                        "points": points,
                    }
                )

            # LEARNING SKILLS
            matched_learning = (
                learning_skill_ids
                & project_skill_ids
            )

            if matched_learning:

                points = min(
                    25.0,
                    len(matched_learning) * 10.0,
                )

                score += points

                skill_names = (
                    self._get_skill_names(
                        repo,
                        matched_learning,
                    )
                )

                reasons.append(
                    {
                        "type": "learning_match",
                        "text": (
                            "Helps you practice: "
                            + ", ".join(
                                skill_names
                            )
                        ),
                        "points": points,
                    }
                )

            # INTEREST / DOMAIN
            domain = (
                project.domain or ""
            ).lower()

            for interest in interest_terms:

                if (
                    interest in domain
                    or domain in interest
                ):
                    score += 15.0

                    reasons.append(
                        {
                            "type": (
                                "interest_match"
                            ),
                            "text": (
                                "Matches your "
                                "interest in "
                                f"{project.domain}"
                            ),
                            "points": 15.0,
                        }
                    )

                    break

            # GOALS
            search_text = (
                (
                    project.title
                    + " "
                    + project.description
                    + " "
                    + (
                        project.domain
                        or ""
                    )
                )
                .lower()
            )

            for goal in goal_terms:

                if (
                    goal
                    and goal in search_text
                ):
                    score += 10.0

                    reasons.append(
                        {
                            "type": "goal_match",
                            "text": (
                                "Related to one "
                                "of your goals"
                            ),
                            "points": 10.0,
                        }
                    )

                    break

            # RECENCY
            if project.created_at:

                created_at = project.created_at

                if created_at.tzinfo is None:
                    created_at = (
                        created_at.replace(
                            tzinfo=timezone.utc
                        )
                    )

                age_days = (
                    datetime.now(
                        timezone.utc
                    )
                    - created_at
                ).days

                if age_days <= 3:

                    score += 10.0

                    reasons.append(
                        {
                            "type": "recency",
                            "text": (
                                "Recently posted"
                            ),
                            "points": 10.0,
                        }
                    )

                elif age_days <= 7:

                    score += 5.0

                    reasons.append(
                        {
                            "type": "recency",
                            "text": (
                                "Posted recently"
                            ),
                            "points": 5.0,
                        }
                    )

            score = min(
                round(score, 2),
                100.0,
            )

            ranked.append(
                {
                    "project_id": project.id,
                    "title": project.title,
                    "domain": project.domain,
                    "score": score,
                    "reasons": reasons,
                }
            )

        ranked.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        ranked = ranked[:limit]

        return {
            "total": len(ranked),
            "recommendations": ranked,
        }

    # =========================================================
    # INTERNSHIP RECOMMENDATIONS
    # =========================================================

    def recommend_internships(
        self,
        db: Session,
        current_user: User,
        limit: int = 10,
    ) -> dict:

        repo = self._repo(db)

        student = repo.get_student_profile(
            current_user.id
        )

        if student is None:
            return {
                "total": 0,
                "recommendations": [],
            }

        student_skills = (
            repo.get_student_skills(
                student
            )
        )

        student_skill_ids = {
            item.skill_id
            for item in student_skills
        }

        learning_skills = (
            repo.get_learning_skills(
                current_user.id
            )
        )

        learning_skill_ids = {
            item.skill_id
            for item in learning_skills
        }

        interests = repo.get_interests(
            current_user.id
        )

        interest_values = set()

        for interest in interests:

            value = getattr(
                interest.category,
                "value",
                interest.category,
            )

            if value:
                interest_values.add(
                    str(value)
                    .replace("_", " ")
                    .lower()
                    .strip()
                )

        goals = repo.get_goals(
            current_user.id
        )

        goal_values = set()

        for goal in goals:

            title = getattr(
                goal,
                "title",
                None,
            )

            if title:
                goal_values.add(
                    title.lower().strip()
                )

            goal_type = getattr(
                goal,
                "goal_type",
                None,
            )

            if goal_type is not None:

                value = getattr(
                    goal_type,
                    "value",
                    goal_type,
                )

                if value:
                    goal_values.add(
                        str(value)
                        .replace("_", " ")
                        .lower()
                        .strip()
                    )

        internships = (
            repo.get_open_internships(
                user_id=current_user.id,
                limit=100,
            )
        )

        ranked = []

        for internship in internships:

            score = 0.0
            reasons = []

            internship_skill_ids = {
                item.skill_id
                for item in internship.skills
            }

            # CURRENT SKILLS — 40
            if internship_skill_ids:

                matched_skills = (
                    student_skill_ids
                    & internship_skill_ids
                )

                skill_ratio = (
                    len(matched_skills)
                    / len(
                        internship_skill_ids
                    )
                )

                skill_score = (
                    skill_ratio * 40.0
                )

                score += skill_score

                if matched_skills:

                    skill_names = (
                        self._get_skill_names(
                            repo,
                            matched_skills,
                        )
                    )

                    reasons.append(
                        {
                            "type": "skill_match",
                            "text": (
                                "Matches your "
                                "skills: "
                                + ", ".join(
                                    skill_names
                                )
                            ),
                            "points": round(
                                skill_score,
                                2,
                            ),
                        }
                    )

            # LEARNING SKILLS — 20
            if internship_skill_ids:

                matched_learning = (
                    learning_skill_ids
                    & internship_skill_ids
                )

                learning_ratio = (
                    len(matched_learning)
                    / len(
                        internship_skill_ids
                    )
                )

                learning_score = (
                    learning_ratio * 20.0
                )

                score += learning_score

                if matched_learning:

                    skill_names = (
                        self._get_skill_names(
                            repo,
                            matched_learning,
                        )
                    )

                    reasons.append(
                        {
                            "type": (
                                "learning_match"
                            ),
                            "text": (
                                "Helps you practice: "
                                + ", ".join(
                                    skill_names
                                )
                            ),
                            "points": round(
                                learning_score,
                                2,
                            ),
                        }
                    )

            # INTEREST / DOMAIN — 15
            domain = (
                internship.domain or ""
            ).lower().strip()

            if domain:

                for interest in interest_values:

                    if (
                        interest in domain
                        or domain in interest
                    ):
                        score += 15.0

                        reasons.append(
                            {
                                "type": (
                                    "interest_match"
                                ),
                                "text": (
                                    "Matches your "
                                    "interest in "
                                    f"{internship.domain}"
                                ),
                                "points": 15.0,
                            }
                        )

                        break

            # CAREER GOAL — 10
            searchable_text = (
                (
                    internship.title
                    + " "
                    + (
                        internship.domain
                        or ""
                    )
                    + " "
                    + internship.description
                )
                .lower()
            )

            for goal in goal_values:

                if (
                    goal
                    and goal
                    in searchable_text
                ):
                    score += 10.0

                    reasons.append(
                        {
                            "type": "goal_match",
                            "text": (
                                "Relevant to your "
                                "career goals"
                            ),
                            "points": 10.0,
                        }
                    )

                    break

            # RECENCY — 10
            if internship.created_at:

                created_at = (
                    internship.created_at
                )

                if created_at.tzinfo is None:
                    created_at = (
                        created_at.replace(
                            tzinfo=timezone.utc
                        )
                    )

                age_days = (
                    datetime.now(
                        timezone.utc
                    )
                    - created_at
                ).days

                if age_days <= 3:

                    score += 10.0

                    reasons.append(
                        {
                            "type": "recency",
                            "text": (
                                "Recently posted"
                            ),
                            "points": 10.0,
                        }
                    )

                elif age_days <= 7:

                    score += 5.0

                    reasons.append(
                        {
                            "type": "recency",
                            "text": (
                                "Posted recently"
                            ),
                            "points": 5.0,
                        }
                    )

            # PAID — 5
            if internship.is_paid:

                score += 5.0

                reasons.append(
                    {
                        "type": "paid",
                        "text": (
                            "Paid internship"
                        ),
                        "points": 5.0,
                    }
                )

            score = min(
                round(score, 2),
                100.0,
            )

            ranked.append(
                {
                    "internship_id": (
                        internship.id
                    ),
                    "title": internship.title,
                    "domain": internship.domain,
                    "location": (
                        internship.location
                    ),
                    "work_mode": getattr(
                        internship.work_mode,
                        "value",
                        internship.work_mode,
                    ),
                    "internship_type": getattr(
                        internship.internship_type,
                        "value",
                        internship.internship_type,
                    ),
                    "experience_level": getattr(
                        internship.experience_level,
                        "value",
                        internship.experience_level,
                    ),
                    "is_paid": (
                        internship.is_paid
                    ),
                    "stipend": (
                        internship.stipend
                    ),
                    "duration_weeks": (
                        internship.duration_weeks
                    ),
                    "deadline": (
                        internship.deadline
                    ),
                    "score": score,
                    "reasons": reasons,
                }
            )

        ranked.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        ranked = ranked[:limit]

        return {
            "total": len(ranked),
            "recommendations": ranked,
        }

    # =========================================================
    # HACKATHON RECOMMENDATIONS — GRAPH AWARE
    # =========================================================

    def recommend_hackathons(
        self,
        db: Session,
        current_user: User,
        limit: int = 10,
    ) -> dict:

        repo = self._repo(db)

        # -----------------------------------------------------
        # STUDENT CURRENT SKILLS
        # -----------------------------------------------------

        student = repo.get_student_profile(
            current_user.id
        )

        current_skill_ids = set()

        if student:

            student_skills = (
                repo.get_student_skills(
                    student
                )
            )

            current_skill_ids = {
                item.skill_id
                for item in student_skills
            }

        # -----------------------------------------------------
        # LEARNING SKILLS
        # -----------------------------------------------------

        learning_skills = (
            repo.get_learning_skills(
                current_user.id
            )
        )

        learning_skill_ids = {
            item.skill_id
            for item in learning_skills
        }

        # -----------------------------------------------------
        # INTERESTS
        # -----------------------------------------------------

        interests = repo.get_interests(
            current_user.id
        )

        interest_terms = set()

        for interest in interests:

            value = getattr(
                interest.category,
                "value",
                interest.category,
            )

            if value:
                interest_terms.add(
                    str(value)
                    .replace("_", " ")
                    .lower()
                    .strip()
                )

        # -----------------------------------------------------
        # GOALS
        # -----------------------------------------------------

        goals = repo.get_goals(
            current_user.id
        )

        goal_terms = set()

        for goal in goals:

            title = getattr(
                goal,
                "title",
                None,
            )

            if title:
                goal_terms.add(
                    title.lower().strip()
                )

            goal_type = getattr(
                goal,
                "goal_type",
                None,
            )

            if goal_type is not None:

                value = getattr(
                    goal_type,
                    "value",
                    goal_type,
                )

                if value:
                    goal_terms.add(
                        str(value)
                        .replace("_", " ")
                        .lower()
                        .strip()
                    )

        # -----------------------------------------------------
        # OPEN HACKATHONS
        #
        # Repository already removes expired registrations.
        # Use a broad candidate pool before ranking.
        # -----------------------------------------------------

        hackathons = (
            repo.get_open_hackathons(
                limit=1000
            )
        )

        # -----------------------------------------------------
        # BUILD RELEVANT SKILL GRAPH
        # -----------------------------------------------------

        graph_skill_ids = (
            set(current_skill_ids)
            | set(learning_skill_ids)
        )

        for hackathon in hackathons:

            for item in (
                hackathon.skills or []
            ):
                graph_skill_ids.add(
                    item.skill_id
                )

        graph = self._build_skill_graph(
            repo,
            graph_skill_ids,
        )

        # Include direct neighbors so hierarchy/related
        # comparisons have all required graph nodes.
        expanded_skill_ids = set(
            graph_skill_ids
        )

        for node in graph.values():

            parent_id = node.get(
                "parent_id"
            )

            if parent_id:
                expanded_skill_ids.add(
                    parent_id
                )

            expanded_skill_ids.update(
                node.get(
                    "child_ids",
                    set(),
                )
            )

            expanded_skill_ids.update(
                node.get(
                    "related_ids",
                    set(),
                )
            )

        graph = self._build_skill_graph(
            repo,
            expanded_skill_ids,
        )

        ranked = []

        now = datetime.now(
            timezone.utc
        )

        # -----------------------------------------------------
        # SCORE EACH HACKATHON
        # -----------------------------------------------------

        for hackathon in hackathons:

            score = 0.0
            semantic_relevance = 0.0
            reasons = []

            hackathon_skill_ids = {
                item.skill_id
                for item in (
                    hackathon.skills or []
                )
            }

            # =================================================
            # 1. CURRENT SKILLS — MAX 40
            #
            # Exact     = 1.00
            # Hierarchy = 0.80
            # Related   = 0.65
            # =================================================

            current_result = (
                self._score_semantic_skills(
                    current_skill_ids,
                    hackathon_skill_ids,
                    graph,
                    40.0,
                )
            )

            current_points = (
                current_result["points"]
            )

            if current_points > 0:

                score += current_points
                semantic_relevance += (
                    current_points
                )

                total_strength = sum(
                    item["strength"]
                    for relation in (
                        "exact",
                        "hierarchy",
                        "related",
                    )
                    for item in current_result[
                        relation
                    ]
                )

                # EXACT
                exact_text = (
                    self._semantic_match_text(
                        repo,
                        current_result["exact"],
                        "exact",
                    )
                )

                if exact_text:

                    exact_strength = sum(
                        item["strength"]
                        for item in current_result[
                            "exact"
                        ]
                    )

                    exact_points = (
                        current_points
                        * (
                            exact_strength
                            / total_strength
                        )
                        if total_strength
                        else 0
                    )

                    reasons.append(
                        {
                            "type": (
                                "exact_skill_match"
                            ),
                            "text": exact_text,
                            "points": round(
                                exact_points,
                                2,
                            ),
                        }
                    )

                # HIERARCHY
                hierarchy_text = (
                    self._semantic_match_text(
                        repo,
                        current_result[
                            "hierarchy"
                        ],
                        "hierarchy",
                    )
                )

                if hierarchy_text:

                    hierarchy_strength = sum(
                        item["strength"]
                        for item in current_result[
                            "hierarchy"
                        ]
                    )

                    hierarchy_points = (
                        current_points
                        * (
                            hierarchy_strength
                            / total_strength
                        )
                        if total_strength
                        else 0
                    )

                    reasons.append(
                        {
                            "type": (
                                "hierarchy_skill_match"
                            ),
                            "text": (
                                hierarchy_text
                            ),
                            "points": round(
                                hierarchy_points,
                                2,
                            ),
                        }
                    )

                # RELATED
                related_text = (
                    self._semantic_match_text(
                        repo,
                        current_result[
                            "related"
                        ],
                        "related",
                    )
                )

                if related_text:

                    related_strength = sum(
                        item["strength"]
                        for item in current_result[
                            "related"
                        ]
                    )

                    related_points = (
                        current_points
                        * (
                            related_strength
                            / total_strength
                        )
                        if total_strength
                        else 0
                    )

                    reasons.append(
                        {
                            "type": (
                                "related_skill_match"
                            ),
                            "text": related_text,
                            "points": round(
                                related_points,
                                2,
                            ),
                        }
                    )

            # =================================================
            # 2. LEARNING SKILLS — MAX 20
            # =================================================

            learning_result = (
                self._score_semantic_skills(
                    learning_skill_ids,
                    hackathon_skill_ids,
                    graph,
                    20.0,
                )
            )

            learning_points = (
                learning_result["points"]
            )

            if learning_points > 0:

                score += learning_points
                semantic_relevance += (
                    learning_points
                )

                exact_text = (
                    self._semantic_match_text(
                        repo,
                        learning_result["exact"],
                        "exact",
                        learning=True,
                    )
                )

                hierarchy_text = (
                    self._semantic_match_text(
                        repo,
                        learning_result[
                            "hierarchy"
                        ],
                        "hierarchy",
                        learning=True,
                    )
                )

                related_text = (
                    self._semantic_match_text(
                        repo,
                        learning_result[
                            "related"
                        ],
                        "related",
                        learning=True,
                    )
                )

                labels = []

                if exact_text:
                    labels.append(exact_text)

                if hierarchy_text:
                    labels.append(
                        hierarchy_text
                    )

                if related_text:
                    labels.append(
                        related_text
                    )

                reasons.append(
                    {
                        "type": (
                            "learning_skill_match"
                        ),
                        "text": (
                            " | ".join(labels)
                            if labels
                            else (
                                "Relevant to skills "
                                "you are learning"
                            )
                        ),
                        "points": (
                            learning_points
                        ),
                    }
                )

            # =================================================
            # 3. INTEREST / DOMAIN — 15
            # =================================================

            domain = (
                hackathon.domain or ""
            ).lower().strip()

            interest_match = False

            if domain:

                for interest in interest_terms:

                    if (
                        interest
                        and (
                            interest in domain
                            or domain in interest
                        )
                    ):
                        interest_match = True
                        break

            if interest_match:

                score += 15.0
                semantic_relevance += 15.0

                reasons.append(
                    {
                        "type": (
                            "interest_match"
                        ),
                        "text": (
                            "Matches your "
                            "interest in "
                            f"{hackathon.domain}"
                        ),
                        "points": 15.0,
                    }
                )

            # =================================================
            # 4. GOAL MATCH — 10
            # =================================================

            searchable_text = (
                (
                    (
                        hackathon.title
                        or ""
                    )
                    + " "
                    + (
                        hackathon.description
                        or ""
                    )
                    + " "
                    + (
                        hackathon.domain
                        or ""
                    )
                )
                .lower()
            )

            goal_match = False

            for goal in goal_terms:

                if (
                    goal
                    and goal
                    in searchable_text
                ):
                    goal_match = True
                    break

            if goal_match:

                score += 10.0
                semantic_relevance += 10.0

                reasons.append(
                    {
                        "type": "goal_match",
                        "text": (
                            "Relevant to one "
                            "of your goals"
                        ),
                        "points": 10.0,
                    }
                )

            # =================================================
            # RELEVANCE GATE
            #
            # Deadline and quality are ranking signals,
            # NOT standalone relevance signals.
            # =================================================

            has_relevance = (
                semantic_relevance > 0
            )

            # =================================================
            # 5. DEADLINE — MAX 10
            # =================================================

            if has_relevance:

                deadline = (
                    self._utc_datetime(
                        hackathon
                        .registration_deadline
                    )
                )

                if deadline:

                    seconds_left = (
                        deadline - now
                    ).total_seconds()

                    if seconds_left > 0:

                        days_left = (
                            seconds_left / 86400
                        )

                        deadline_points = 0.0
                        deadline_text = None

                        if days_left <= 7:

                            deadline_points = 10.0
                            deadline_text = (
                                "Registration "
                                "closes within "
                                "7 days"
                            )

                        elif days_left <= 14:

                            deadline_points = 7.0
                            deadline_text = (
                                "Registration "
                                "closes within "
                                "2 weeks"
                            )

                        elif days_left <= 30:

                            deadline_points = 4.0
                            deadline_text = (
                                "Registration is "
                                "currently open"
                            )

                        if deadline_points:

                            score += (
                                deadline_points
                            )

                            reasons.append(
                                {
                                    "type": (
                                        "deadline"
                                    ),
                                    "text": (
                                        deadline_text
                                    ),
                                    "points": (
                                        deadline_points
                                    ),
                                }
                            )

            # =================================================
            # 6. QUALITY — MAX 5
            # =================================================

            if has_relevance:

                quality_points = 0.0
                quality_labels = []

                if hackathon.is_verified:

                    quality_points += 3.0
                    quality_labels.append(
                        "verified"
                    )

                if hackathon.is_featured:

                    quality_points += 2.0
                    quality_labels.append(
                        "featured"
                    )

                if quality_points:

                    score += quality_points

                    reasons.append(
                        {
                            "type": (
                                "quality_signal"
                            ),
                            "text": (
                                "Opportunity is "
                                + " and ".join(
                                    quality_labels
                                )
                            ),
                            "points": (
                                quality_points
                            ),
                        }
                    )

            # =================================================
            # FINAL SCORE
            # =================================================

            score = min(
                round(score, 2),
                100.0,
            )

            semantic_relevance = round(
                semantic_relevance,
                2,
            )

            ranked.append(
                {
                    "hackathon_id": (
                        hackathon.id
                    ),
                    "title": (
                        hackathon.title
                    ),
                    "domain": (
                        hackathon.domain
                    ),
                    "organizer_name": (
                        hackathon.organizer_name
                    ),
                    "mode": getattr(
                        hackathon.mode,
                        "value",
                        hackathon.mode,
                    ),
                    "difficulty": getattr(
                        hackathon.difficulty,
                        "value",
                        hackathon.difficulty,
                    ),
                    "location": (
                        hackathon.location
                    ),
                    "registration_deadline": (
                        hackathon
                        .registration_deadline
                    ),
                    "start_date": (
                        hackathon.start_date
                    ),
                    "end_date": (
                        hackathon.end_date
                    ),
                    "prize_details": (
                        hackathon.prize_details
                    ),
                    "registration_url": (
                        hackathon
                        .registration_url
                    ),
                    "source_type": getattr(
                        hackathon.source_type,
                        "value",
                        hackathon.source_type,
                    ),
                    "source_name": (
                        hackathon.source_name
                    ),
                    "score": score,

                    # Internal ranking information.
                    # If your response schema excludes this,
                    # it simply won't appear in API JSON.
                    "relevance_score": (
                        semantic_relevance
                    ),

                    "reasons": reasons,
                }
            )

        # =====================================================
        # FINAL RANKING
        #
        # FIX:
        # final score is the primary ranking signal.
        # semantic relevance only breaks equal-score ties.
        # =====================================================

        ranked.sort(
            key=lambda item: (
                item["score"],
                item["relevance_score"],
            ),
            reverse=True,
        )

        ranked = ranked[:limit]

        return {
            "total": len(ranked),
            "recommendations": ranked,
        }


recommendation_service = (
    RecommendationService()
)