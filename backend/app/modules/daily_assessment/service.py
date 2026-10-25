import uuid
from collections import defaultdict
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User

from app.modules.daily_assessment.generator import (
    daily_assessment_generator,
)

from app.modules.daily_assessment.repositories import (
    DailyAssessmentRepository,
)

from app.modules.daily_assessment.schemas import (
    AnswerCreate,
)


class DailyAssessmentService:

    def _repo(
        self,
        db: Session,
    ) -> DailyAssessmentRepository:
        return DailyAssessmentRepository(db)

    # =========================================================
    # STUDENT CHECK
    # =========================================================

    def _student_or_403(
        self,
        db: Session,
        current_user: User,
    ):
        repo = self._repo(db)

        student = repo.get_student_profile(
            current_user.id
        )

        if not student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Daily assessments are currently "
                    "available only to students."
                ),
            )

        return student

    # =========================================================
    # TODAY STATUS - READ ONLY
    # =========================================================

    def get_today_status(
        self,
        db: Session,
        current_user: User,
    ) -> dict:
        """
        Lightweight Daily Task status for the Home page.

        IMPORTANT:
        This method does not generate questions,
        call Gemini, create attempts, or write anything
        to the database.
        """

        repo = self._repo(db)

        student = repo.get_student_profile(
            current_user.id
        )

        # Daily Assessment is currently student-only.
        if not student:
            return {
                "available": False,
                "generated": False,
                "completed": False,
                "question_count": 0,
                "answered_count": 0,
                "attempt_id": None,
                "score": None,
            }

        today = date.today()

        daily = repo.get_daily(
            student.id,
            today,
        )

        # Today's assessment has not been generated yet.
        if not daily:

            preferences = repo.get_preferences(
                current_user.id
            )

            question_count = 5

            if (
                preferences
                and preferences.daily_assessment_question_count
                is not None
            ):
                question_count = (
                    preferences.daily_assessment_question_count
                )

            question_count = max(
                5,
                min(question_count, 10),
            )

            return {
                "available": True,
                "generated": False,
                "completed": False,
                "question_count": question_count,
                "answered_count": 0,
                "attempt_id": None,
                "score": None,
            }

        # Today's assessment already exists.
        answered_ids = (
            repo.get_answered_question_ids(
                daily.attempt_id
            )
        )

        score = None

        if daily.attempt:
            score = daily.attempt.total_score

        return {
            "available": True,
            "generated": True,
            "completed": daily.completed,
            "question_count": daily.question_count,
            "answered_count": len(answered_ids),
            "attempt_id": daily.attempt_id,
            "score": score,
        }

    # =========================================================
    # TODAY
    # =========================================================

    def get_today(
        self,
        db: Session,
        current_user: User,
    ):
        repo = self._repo(db)

        student = self._student_or_403(
            db,
            current_user,
        )

        today = date.today()

        # -----------------------------------------------------
        # Already generated today?
        # -----------------------------------------------------

        existing = repo.get_daily(
            student.id,
            today,
        )

        if existing:
            questions = repo.get_daily_questions(
                existing.id
            )

            answered_ids = (
                repo.get_answered_question_ids(
                    existing.attempt_id
                )
            )

            return self._serialize_daily(
                repo,
                existing,
                questions,
                len(answered_ids),
            )

        # -----------------------------------------------------
        # Question count
        # -----------------------------------------------------

        preferences = repo.get_preferences(
            current_user.id
        )

        question_count = 5

        if (
            preferences
            and preferences.daily_assessment_question_count
            is not None
        ):
            question_count = (
                preferences.daily_assessment_question_count
            )

        question_count = max(
            5,
            min(question_count, 10),
        )

        # -----------------------------------------------------
        # Build skill profile
        # -----------------------------------------------------

        learning_skills = repo.get_learning_skills(
            current_user.id
        )

        student_skills = repo.get_student_skills(
            student.id
        )

        latest_scores = repo.get_latest_skill_scores(
            student.id
        )

        skill_profiles = {}

        # Learning skills get priority.
        for learning in learning_skills:
            skill = learning.skill

            if not skill:
                continue

            skill_profiles[skill.id] = {
                "skill": skill,
                "base_level": (
                    learning.target_level or 1
                ),
                "learning_priority": True,
            }

        # Add existing skills that aren't already included.
        for student_skill in student_skills:
            skill = repo.get_skill(
                student_skill.skill_id
            )

            if not skill:
                continue

            if skill.id in skill_profiles:
                continue

            level = self._extract_level(
                student_skill.proficiency_level
            )

            skill_profiles[skill.id] = {
                "skill": skill,
                "base_level": level,
                "learning_priority": False,
            }

        if not skill_profiles:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Add at least one current skill or "
                    "skill you want to learn before "
                    "starting the daily assessment."
                ),
            )

        # -----------------------------------------------------
        # Pick max 3 skills
        # -----------------------------------------------------

        selected_profiles = list(
            skill_profiles.values()
        )[:3]

        # -----------------------------------------------------
        # Distribute questions
        # -----------------------------------------------------

        counts = self._distribute_questions(
            total=question_count,
            skills_count=len(
                selected_profiles
            ),
        )

        skill_requests = []
        skill_map = {}

        for profile, count in zip(
            selected_profiles,
            counts,
        ):
            skill = profile["skill"]

            previous_score = latest_scores.get(
                skill.id
            )

            difficulty = (
                self._calculate_difficulty(
                    base_level=profile[
                        "base_level"
                    ],
                    previous_score=previous_score,
                )
            )

            skill_requests.append(
                {
                    "skill_name": skill.name,
                    "difficulty": difficulty,
                    "question_count": count,
                }
            )

            skill_map[
                skill.name
            ] = skill

        # -----------------------------------------------------
        # GEMINI GENERATES QUESTIONS
        # -----------------------------------------------------

        generated_questions = (
            daily_assessment_generator
            .generate_questions(
                skill_requests
            )
        )

        # -----------------------------------------------------
        # Save AI-generated questions
        # -----------------------------------------------------

        assessment = (
            repo
            .get_or_create_daily_assessment_definition()
        )

        questions = (
            repo.create_generated_questions(
                assessment_id=assessment.id,
                generated_questions=generated_questions,
                skill_map=skill_map,
            )
        )

        # -----------------------------------------------------
        # Create attempt
        # -----------------------------------------------------

        attempt = repo.create_attempt(
            student_id=student.id,
            assessment_id=assessment.id,
        )

        # -----------------------------------------------------
        # Create today's record
        # -----------------------------------------------------

        daily = repo.create_daily(
            student_id=student.id,
            attempt_id=attempt.id,
            assessment_date=today,
            question_count=len(
                questions
            ),
        )

        # -----------------------------------------------------
        # Freeze today's exact questions
        # -----------------------------------------------------

        repo.attach_questions(
            daily.id,
            questions,
        )

        return self._serialize_daily(
            repo,
            daily,
            questions,
            0,
        )

    # =========================================================
    # DIFFICULTY
    # =========================================================

    def _calculate_difficulty(
        self,
        base_level: int,
        previous_score: float | None,
    ) -> str:
        """
        Base levels:

        1 = Beginner
        2 = Intermediate
        3 = Advanced / Pro
        4 = Expert

        Assessment history then adjusts difficulty.
        """

        if base_level <= 1:
            difficulty_value = 1

        elif base_level == 2:
            difficulty_value = 2

        else:
            difficulty_value = 3

        # Adaptive rule
        if previous_score is not None:

            if previous_score < 50:
                difficulty_value -= 1

            elif previous_score > 75:
                difficulty_value += 1

        difficulty_value = max(
            1,
            min(difficulty_value, 3),
        )

        return {
            1: "easy",
            2: "medium",
            3: "hard",
        }[difficulty_value]

    # =========================================================
    # ENUM / INTEGER LEVEL
    # =========================================================

    def _extract_level(
        self,
        level,
    ) -> int:

        if level is None:
            return 1

        if isinstance(
            level,
            int,
        ):
            return level

        value = getattr(
            level,
            "value",
            level,
        )

        if isinstance(
            value,
            int,
        ):
            return value

        name = str(
            getattr(
                level,
                "name",
                value,
            )
        ).upper()

        mapping = {
            "BEGINNER": 1,
            "INTERMEDIATE": 2,
            "ADVANCED": 3,
            "PRO": 3,
            "EXPERT": 4,
        }

        return mapping.get(
            name,
            1,
        )

    # =========================================================
    # QUESTION DISTRIBUTION
    # =========================================================

    def _distribute_questions(
        self,
        total: int,
        skills_count: int,
    ) -> list[int]:

        if skills_count <= 0:
            return []

        base = total // skills_count
        remainder = total % skills_count

        result = []

        for index in range(
            skills_count
        ):
            count = base

            if index < remainder:
                count += 1

            result.append(
                count
            )

        return result

    # =========================================================
    # ANSWER
    # =========================================================

    def answer(
        self,
        db: Session,
        current_user: User,
        attempt_id: uuid.UUID,
        payload: AnswerCreate,
    ):
        repo = self._repo(db)

        student = self._student_or_403(
            db,
            current_user,
        )

        daily = repo.get_daily_by_attempt(
            attempt_id,
            student.id,
        )

        if not daily:
            raise HTTPException(
                status_code=404,
                detail="Assessment attempt not found.",
            )

        if daily.completed:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Assessment is already completed."
                ),
            )

        questions = repo.get_daily_questions(
            daily.id
        )

        valid_question_ids = {
            question.id
            for question in questions
        }

        if (
            payload.question_id
            not in valid_question_ids
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "This question does not belong "
                    "to this assessment."
                ),
            )

        question = repo.get_question(
            payload.question_id
        )

        option = repo.get_option(
            payload.selected_option_id
        )

        if not question or not option:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Question or option not found."
                ),
            )

        if option.question_id != question.id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Selected option does not belong "
                    "to this question."
                ),
            )

        repo.save_answer(
            attempt_id,
            question.id,
            option,
        )

        # Never reveal correctness here.
        return {
            "question_id": question.id,
            "answered": True,
        }

    # =========================================================
    # SUBMIT
    # =========================================================

    def submit(
        self,
        db: Session,
        current_user: User,
        attempt_id: uuid.UUID,
    ):
        repo = self._repo(db)

        student = self._student_or_403(
            db,
            current_user,
        )

        daily = repo.get_daily_by_attempt(
            attempt_id,
            student.id,
        )

        if not daily:
            raise HTTPException(
                status_code=404,
                detail="Assessment attempt not found.",
            )

        if daily.completed:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Assessment already submitted."
                ),
            )

        questions = repo.get_daily_questions(
            daily.id
        )

        answers = repo.get_answers(
            attempt_id
        )

        if len(answers) != len(questions):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Answer all questions before "
                    f"submitting. Answered "
                    f"{len(answers)} of "
                    f"{len(questions)}."
                ),
            )

        answer_map = {
            answer.question_id: answer
            for answer in answers
        }

        correct = sum(
            1
            for answer in answers
            if answer.is_correct
        )

        total = len(
            questions
        )

        score = round(
            (
                correct
                / total
            )
            * 100,
            2,
        )

        # -----------------------------------------------------
        # Per-skill results
        # -----------------------------------------------------

        per_skill = defaultdict(
            lambda: {
                "correct": 0,
                "total": 0,
            }
        )

        for question in questions:

            if not question.skill_id:
                continue

            per_skill[
                question.skill_id
            ]["total"] += 1

            answer = answer_map.get(
                question.id
            )

            if (
                answer
                and answer.is_correct
            ):
                per_skill[
                    question.skill_id
                ]["correct"] += 1

        skill_results = []

        for skill_id, values in (
            per_skill.items()
        ):
            skill_score = round(
                (
                    values["correct"]
                    / values["total"]
                )
                * 100,
                2,
            )

            repo.save_skill_result(
                attempt_id=attempt_id,
                skill_id=skill_id,
                score=skill_score,
            )

            skill = repo.get_skill(
                skill_id
            )

            skill_results.append(
                {
                    "skill_id": skill_id,
                    "skill_name": (
                        skill.name
                        if skill
                        else None
                    ),
                    "correct": (
                        values["correct"]
                    ),
                    "total": (
                        values["total"]
                    ),
                    "score": skill_score,
                }
            )

        attempt = repo.complete_attempt(
            daily,
            score,
        )

        return {
            "attempt_id": attempt.id,
            "score": score,
            "correct_answers": correct,
            "total_questions": total,
            "completed_at": (
                attempt.completed_at
            ),
            "skill_results": skill_results,
        }

    # =========================================================
    # HISTORY
    # =========================================================

    def history(
        self,
        db: Session,
        current_user: User,
    ):
        repo = self._repo(db)

        student = self._student_or_403(
            db,
            current_user,
        )

        rows = repo.list_history(
            student.id
        )

        return [
            {
                "daily_assessment_id": row.id,
                "attempt_id": row.attempt_id,
                "assessment_date": (
                    row.assessment_date
                ),
                "completed": row.completed,
                "score": (
                    row.attempt.total_score
                ),
                "question_count": (
                    row.question_count
                ),
            }
            for row in rows
        ]

    # =========================================================
    # PROGRESS
    # =========================================================

    def progress(
        self,
        db: Session,
        current_user: User,
    ):
        history = self.history(
            db,
            current_user,
        )

        completed = [
            item
            for item in history
            if (
                item["completed"]
                and item["score"] is not None
            )
        ]

        scores = [
            item["score"]
            for item in completed
        ]

        return {
            "total_completed": len(
                scores
            ),
            "average_score": (
                round(
                    sum(scores)
                    / len(scores),
                    2,
                )
                if scores
                else 0.0
            ),
            "latest_score": (
                scores[0]
                if scores
                else None
            ),
            "best_score": (
                max(scores)
                if scores
                else None
            ),
        }

    # =========================================================
    # SAFE RESPONSE
    # =========================================================

    def _serialize_daily(
        self,
        repo,
        daily,
        questions,
        answered_count,
    ):
        serialized_questions = []

        for question in questions:

            skill = (
                repo.get_skill(
                    question.skill_id
                )
                if question.skill_id
                else None
            )

            serialized_questions.append(
                {
                    "id": question.id,
                    "skill_id": (
                        question.skill_id
                    ),
                    "skill_name": (
                        skill.name
                        if skill
                        else None
                    ),
                    "question_text": (
                        question.question_text
                    ),
                    "difficulty": (
                        question
                        .difficulty
                        .value
                    ),
                    "points": (
                        question.points
                    ),
                    "options": [
                        {
                            "id": option.id,
                            "option_text": (
                                option.option_text
                            ),
                        }
                        for option
                        in question.options
                    ],
                }
            )

        return {
            "id": daily.id,
            "attempt_id": (
                daily.attempt_id
            ),
            "assessment_date": (
                daily.assessment_date
            ),
            "question_count": (
                daily.question_count
            ),
            "completed": (
                daily.completed
            ),
            "answered_count": (
                answered_count
            ),
            "questions": (
                serialized_questions
            ),
        }


daily_assessment_service = (
    DailyAssessmentService()
)