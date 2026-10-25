DAILY_ASSESSMENT_SYSTEM_PROMPT = """
You generate short educational multiple-choice questions for a daily
assessment system.

Rules:

1. Return ONLY valid JSON.
2. Do not include markdown.
3. Do not include explanations outside JSON.
4. Every question must have exactly 4 options.
5. Every question must have exactly one correct answer.
6. correct_index must be 0, 1, 2, or 3.
7. Questions must match the requested skill and difficulty.
8. Questions should test understanding, not trivia.
9. Avoid repeating nearly identical questions.
10. Keep language clear and suitable for a university learner.

Difficulty meanings:

easy:
- basic concepts
- definitions
- straightforward application

medium:
- conceptual understanding
- common applications
- moderate reasoning

hard:
- deeper reasoning
- scenario-based questions
- application and analysis

Required JSON format:

{
  "questions": [
    {
      "skill": "Python",
      "difficulty": "medium",
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "correct_index": 1
    }
  ]
}
"""


def build_daily_assessment_prompt(
    skill_requests: list[dict],
) -> str:
    lines = []

    for item in skill_requests:
        lines.append(
            (
                f"- Skill: {item['skill_name']} | "
                f"Difficulty: {item['difficulty']} | "
                f"Questions: {item['question_count']}"
            )
        )

    skill_text = "\n".join(lines)

    return f"""
Generate today's personalized assessment.

Create questions according to this distribution:

{skill_text}

Important:
- Generate exactly the requested number of questions.
- Use only the requested skills.
- Match the requested difficulty for each skill.
- Exactly 4 options per question.
- Exactly one correct option.
- Return only JSON.
"""