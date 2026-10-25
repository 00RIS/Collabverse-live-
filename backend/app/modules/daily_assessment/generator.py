import json
from typing import Any

from fastapi import HTTPException
from google import genai

from app.core.config import settings
from app.modules.daily_assessment.prompts import (
    DAILY_ASSESSMENT_SYSTEM_PROMPT,
    build_daily_assessment_prompt,
)


class DailyAssessmentGenerator:
    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        self.model = "gemini-3.6-flash"

    def generate_questions(
        self,
        skill_requests: list[dict],
    ) -> list[dict]:
        """
        Example skill_requests:

        [
            {
                "skill_name": "Machine Learning",
                "difficulty": "easy",
                "question_count": 2,
            },
            {
                "skill_name": "SQL",
                "difficulty": "medium",
                "question_count": 3,
            },
        ]
        """

        expected_count = sum(
            item["question_count"]
            for item in skill_requests
        )

        user_prompt = build_daily_assessment_prompt(
            skill_requests
        )

        full_prompt = (
            DAILY_ASSESSMENT_SYSTEM_PROMPT
            + "\n\n"
            + user_prompt
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
            )

        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "AI assessment generation failed."
                ),
            ) from exc

        raw_text = getattr(
            response,
            "text",
            None,
        )

        if not raw_text:
            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned an empty assessment."
                ),
            )

        data = self._parse_json(
            raw_text
        )

        questions = data.get(
            "questions"
        )

        if not isinstance(
            questions,
            list,
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned an invalid question format."
                ),
            )

        if len(questions) != expected_count:
            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned the wrong number "
                    "of questions."
                ),
            )

        validated_questions = []

        allowed_skills = {
            item["skill_name"]
            for item in skill_requests
        }

        allowed_difficulties = {
            "easy",
            "medium",
            "hard",
        }

        for question in questions:
            validated_questions.append(
                self._validate_question(
                    question,
                    allowed_skills,
                    allowed_difficulties,
                )
            )

        return validated_questions

    def _parse_json(
        self,
        raw_text: str,
    ) -> dict[str, Any]:
        cleaned = (
            raw_text
            .strip()
        )

        if cleaned.startswith(
            "```json"
        ):
            cleaned = cleaned[
                len("```json"):
            ]

        elif cleaned.startswith(
            "```"
        ):
            cleaned = cleaned[
                len("```"):
            ]

        if cleaned.endswith(
            "```"
        ):
            cleaned = cleaned[:-3]

        cleaned = cleaned.strip()

        try:
            return json.loads(
                cleaned
            )

        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned invalid JSON."
                ),
            ) from exc

    def _validate_question(
        self,
        question: dict,
        allowed_skills: set[str],
        allowed_difficulties: set[str],
    ) -> dict:
        if not isinstance(
            question,
            dict,
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned an invalid question."
                ),
            )

        skill = question.get(
            "skill"
        )

        difficulty = question.get(
            "difficulty"
        )

        question_text = question.get(
            "question"
        )

        options = question.get(
            "options"
        )

        correct_index = question.get(
            "correct_index"
        )

        if skill not in allowed_skills:
            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned a question "
                    "for an unexpected skill."
                ),
            )

        if difficulty not in allowed_difficulties:
            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned an invalid difficulty."
                ),
            )

        if not isinstance(
            question_text,
            str,
        ) or not question_text.strip():
            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned an empty question."
                ),
            )

        if (
            not isinstance(
                options,
                list,
            )
            or len(options) != 4
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "Each AI question must have "
                    "exactly 4 options."
                ),
            )

        if not all(
            isinstance(option, str)
            and option.strip()
            for option in options
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned an invalid option."
                ),
            )

        if (
            not isinstance(
                correct_index,
                int,
            )
            or correct_index not in {
                0,
                1,
                2,
                3,
            }
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "AI returned an invalid "
                    "correct answer index."
                ),
            )

        return {
            "skill": skill.strip(),
            "difficulty": difficulty,
            "question": question_text.strip(),
            "options": [
                option.strip()
                for option in options
            ],
            "correct_index": correct_index,
        }


daily_assessment_generator = (
    DailyAssessmentGenerator()
)