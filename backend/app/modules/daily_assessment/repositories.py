import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.assessment import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentSkillResult,
    AssessmentType,
    AttemptStatus,
    DifficultyLevel,
    QuestionOption,
    QuestionType,
)
from app.models.profile import StudentProfile
from app.models.skill import Skill
from app.models.student_skill import StudentSkill

from app.modules.daily_assessment.models import (
    AssessmentAnswer,
    DailyAssessment,
    DailyAssessmentQuestion,
)
from app.modules.preferences.models import (
    UserLearningSkill,
    UserPreference,
)


class DailyAssessmentRepository:
    def __init__(self, db: Session):
        self.db = db

    # =========================================================
    # STUDENT
    # =========================================================

    def get_student_profile(
        self,
        user_id: uuid.UUID,
    ) -> StudentProfile | None:
        return self.db.scalar(
            select(StudentProfile).where(
                StudentProfile.user_id == user_id
            )
        )

    # =========================================================
    # PREFERENCES
    # =========================================================

    def get_preferences(
        self,
        user_id: uuid.UUID,
    ) -> UserPreference | None:
        return self.db.scalar(
            select(UserPreference).where(
                UserPreference.user_id == user_id
            )
        )

    # =========================================================
    # CURRENT STUDENT SKILLS
    # =========================================================

    def get_student_skills(
        self,
        student_id: uuid.UUID,
    ) -> list[StudentSkill]:

        student = self.db.get(
            StudentProfile,
            student_id,
        )

        if not student:
            return []

        return list(
            student.student_skills
        )

    # =========================================================
    # SKILLS USER WANTS TO LEARN
    # =========================================================

    def get_learning_skills(
        self,
        user_id: uuid.UUID,
    ) -> list[UserLearningSkill]:

        return list(
            self.db.scalars(
                select(UserLearningSkill)
                .options(
                    selectinload(
                        UserLearningSkill.skill
                    )
                )
                .where(
                    UserLearningSkill.user_id
                    == user_id
                )
            ).all()
        )

    # =========================================================
    # LATEST ASSESSMENT RESULTS
    # =========================================================

    def get_latest_skill_scores(
        self,
        student_id: uuid.UUID,
    ) -> dict[uuid.UUID, float]:

        rows = self.db.execute(
            select(
                AssessmentSkillResult,
                AssessmentAttempt,
            )
            .join(
                AssessmentAttempt,
                AssessmentAttempt.id
                == AssessmentSkillResult.attempt_id,
            )
            .where(
                AssessmentAttempt.student_id
                == student_id,
                AssessmentAttempt.status
                == AttemptStatus.COMPLETED,
            )
            .order_by(
                AssessmentAttempt.completed_at.desc()
            )
        ).all()

        latest: dict[uuid.UUID, float] = {}

        for result, attempt in rows:
            if result.skill_id not in latest:
                latest[result.skill_id] = (
                    result.score
                )

        return latest

    # =========================================================
    # SKILL
    # =========================================================

    def get_skill(
        self,
        skill_id: uuid.UUID,
    ) -> Skill | None:

        return self.db.get(
            Skill,
            skill_id,
        )

    # =========================================================
    # DAILY ASSESSMENT
    # =========================================================

    def get_daily(
        self,
        student_id: uuid.UUID,
        assessment_date: date,
    ) -> DailyAssessment | None:

        return self.db.scalar(
            select(DailyAssessment)
            .options(
                selectinload(
                    DailyAssessment.attempt
                )
            )
            .where(
                DailyAssessment.student_id
                == student_id,
                DailyAssessment.assessment_date
                == assessment_date,
            )
        )

    def get_daily_by_attempt(
        self,
        attempt_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> DailyAssessment | None:

        return self.db.scalar(
            select(DailyAssessment).where(
                DailyAssessment.attempt_id
                == attempt_id,
                DailyAssessment.student_id
                == student_id,
            )
        )

    def create_daily(
        self,
        student_id: uuid.UUID,
        attempt_id: uuid.UUID,
        assessment_date: date,
        question_count: int,
    ) -> DailyAssessment:

        daily = DailyAssessment(
            student_id=student_id,
            attempt_id=attempt_id,
            assessment_date=assessment_date,
            question_count=question_count,
        )

        self.db.add(daily)
        self.db.commit()
        self.db.refresh(daily)

        return daily

    # =========================================================
    # MASTER DAILY ASSESSMENT
    # =========================================================

    def get_or_create_daily_assessment_definition(
        self,
    ) -> Assessment:

        assessment = self.db.scalar(
            select(Assessment).where(
                Assessment.title
                == "Daily Personalized Assessment"
            )
        )

        if assessment:
            return assessment

        assessment = Assessment(
            title="Daily Personalized Assessment",
            description=(
                "AI-generated adaptive daily assessment "
                "based on student skills and progress."
            ),
            assessment_type=(
                AssessmentType.TECHNICAL
            ),
            duration_minutes=10,
            difficulty=DifficultyLevel.MEDIUM,
        )

        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)

        return assessment

    # =========================================================
    # SAVE AI GENERATED QUESTIONS
    # =========================================================

    def create_generated_questions(
        self,
        assessment_id: uuid.UUID,
        generated_questions: list[dict],
        skill_map: dict[str, Skill],
    ) -> list[AssessmentQuestion]:

        created_ids: list[uuid.UUID] = []

        try:
            for generated in generated_questions:

                skill_name = generated[
                    "skill"
                ]

                skill = skill_map.get(
                    skill_name
                )

                if not skill:
                    raise ValueError(
                        f"Unknown skill: {skill_name}"
                    )

                difficulty_map = {
                    "easy": DifficultyLevel.EASY,
                    "medium": DifficultyLevel.MEDIUM,
                    "hard": DifficultyLevel.HARD,
                }

                difficulty = difficulty_map[
                    generated["difficulty"]
                ]

                question = AssessmentQuestion(
                    assessment_id=assessment_id,
                    skill_id=skill.id,
                    question_text=generated[
                        "question"
                    ],
                    question_type=QuestionType.MCQ,
                    difficulty=difficulty,
                    points=1,
                )

                self.db.add(question)
                self.db.flush()

                created_ids.append(
                    question.id
                )

                correct_index = generated[
                    "correct_index"
                ]

                for (
                    index,
                    option_text,
                ) in enumerate(
                    generated["options"]
                ):

                    option = QuestionOption(
                        question_id=question.id,
                        option_text=option_text,
                        is_correct=(
                            index == correct_index
                        ),
                    )

                    self.db.add(option)

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

        return list(
            self.db.scalars(
                select(AssessmentQuestion)
                .options(
                    selectinload(
                        AssessmentQuestion.options
                    )
                )
                .where(
                    AssessmentQuestion.id.in_(
                        created_ids
                    )
                )
            ).all()
        )

    # =========================================================
    # ATTACH QUESTIONS TO DAILY ASSESSMENT
    # =========================================================

    def attach_questions(
        self,
        daily_id: uuid.UUID,
        questions: list[AssessmentQuestion],
    ) -> None:

        for (
            position,
            question,
        ) in enumerate(
            questions,
            start=1,
        ):

            self.db.add(
                DailyAssessmentQuestion(
                    daily_assessment_id=daily_id,
                    question_id=question.id,
                    position=position,
                )
            )

        self.db.commit()

    def get_daily_questions(
        self,
        daily_id: uuid.UUID,
    ) -> list[AssessmentQuestion]:

        rows = self.db.execute(
            select(
                DailyAssessmentQuestion,
                AssessmentQuestion,
            )
            .join(
                AssessmentQuestion,
                AssessmentQuestion.id
                == DailyAssessmentQuestion.question_id,
            )
            .options(
                selectinload(
                    AssessmentQuestion.options
                )
            )
            .where(
                DailyAssessmentQuestion
                .daily_assessment_id
                == daily_id
            )
            .order_by(
                DailyAssessmentQuestion.position
            )
        ).all()

        return [
            question
            for _, question in rows
        ]

    # =========================================================
    # CREATE ATTEMPT
    # =========================================================

    def create_attempt(
        self,
        student_id: uuid.UUID,
        assessment_id: uuid.UUID,
    ) -> AssessmentAttempt:

        attempt = AssessmentAttempt(
            student_id=student_id,
            assessment_id=assessment_id,
            status=AttemptStatus.IN_PROGRESS,
            started_at=datetime.now(
                timezone.utc
            ),
        )

        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)

        return attempt

    # =========================================================
    # QUESTION
    # =========================================================

    def get_question(
        self,
        question_id: uuid.UUID,
    ) -> AssessmentQuestion | None:

        return self.db.scalar(
            select(AssessmentQuestion)
            .options(
                selectinload(
                    AssessmentQuestion.options
                )
            )
            .where(
                AssessmentQuestion.id
                == question_id
            )
        )

    # =========================================================
    # OPTION
    # =========================================================

    def get_option(
        self,
        option_id: uuid.UUID,
    ) -> QuestionOption | None:

        return self.db.get(
            QuestionOption,
            option_id,
        )

    # =========================================================
    # ANSWERS
    # =========================================================

    def get_answer(
        self,
        attempt_id: uuid.UUID,
        question_id: uuid.UUID,
    ) -> AssessmentAnswer | None:

        return self.db.scalar(
            select(AssessmentAnswer).where(
                AssessmentAnswer.attempt_id
                == attempt_id,
                AssessmentAnswer.question_id
                == question_id,
            )
        )

    def save_answer(
        self,
        attempt_id: uuid.UUID,
        question_id: uuid.UUID,
        selected_option: QuestionOption,
    ) -> AssessmentAnswer:

        answer = self.get_answer(
            attempt_id,
            question_id,
        )

        if answer:
            answer.selected_option_id = (
                selected_option.id
            )

            answer.is_correct = (
                selected_option.is_correct
            )

        else:
            answer = AssessmentAnswer(
                attempt_id=attempt_id,
                question_id=question_id,
                selected_option_id=(
                    selected_option.id
                ),
                is_correct=(
                    selected_option.is_correct
                ),
            )

            self.db.add(answer)

        self.db.commit()
        self.db.refresh(answer)

        return answer

    def get_answers(
        self,
        attempt_id: uuid.UUID,
    ) -> list[AssessmentAnswer]:

        return list(
            self.db.scalars(
                select(
                    AssessmentAnswer
                ).where(
                    AssessmentAnswer.attempt_id
                    == attempt_id
                )
            ).all()
        )

    def get_answered_question_ids(
        self,
        attempt_id: uuid.UUID,
    ) -> set[uuid.UUID]:

        return set(
            self.db.scalars(
                select(
                    AssessmentAnswer.question_id
                ).where(
                    AssessmentAnswer.attempt_id
                    == attempt_id
                )
            ).all()
        )

    # =========================================================
    # SKILL RESULTS
    # =========================================================

    def save_skill_result(
        self,
        attempt_id: uuid.UUID,
        skill_id: uuid.UUID,
        score: float,
    ) -> AssessmentSkillResult:

        result = self.db.scalar(
            select(
                AssessmentSkillResult
            ).where(
                AssessmentSkillResult.attempt_id
                == attempt_id,
                AssessmentSkillResult.skill_id
                == skill_id,
            )
        )

        if result:
            result.score = score

        else:
            result = AssessmentSkillResult(
                attempt_id=attempt_id,
                skill_id=skill_id,
                score=score,
            )

            self.db.add(result)

        return result

    # =========================================================
    # COMPLETE ATTEMPT
    # =========================================================

    def complete_attempt(
        self,
        daily: DailyAssessment,
        score: float,
    ) -> AssessmentAttempt:

        attempt = self.db.get(
            AssessmentAttempt,
            daily.attempt_id,
        )

        if not attempt:
            raise ValueError(
                "Assessment attempt not found."
            )

        attempt.status = (
            AttemptStatus.COMPLETED
        )

        attempt.total_score = score

        attempt.completed_at = (
            datetime.now(
                timezone.utc
            )
        )

        daily.completed = True

        self.db.commit()
        self.db.refresh(attempt)

        return attempt

    # =========================================================
    # HISTORY
    # =========================================================

    def list_history(
        self,
        student_id: uuid.UUID,
    ) -> list[DailyAssessment]:

        return list(
            self.db.scalars(
                select(DailyAssessment)
                .options(
                    selectinload(
                        DailyAssessment.attempt
                    )
                )
                .where(
                    DailyAssessment.student_id
                    == student_id
                )
                .order_by(
                    DailyAssessment
                    .assessment_date
                    .desc()
                )
            ).all()
        )