from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.skill import Skill, SkillCategory


SKILLS = [
    # Technical
    ("Python", SkillCategory.TECHNICAL, "Programming language widely used in data, backend and AI."),
    ("SQL", SkillCategory.TECHNICAL, "Language used to query and manage relational databases."),
    ("Machine Learning", SkillCategory.TECHNICAL, "Algorithms that learn patterns from data."),
    ("Deep Learning", SkillCategory.TECHNICAL, "Neural network based machine learning methods."),
    ("Data Structures and Algorithms", SkillCategory.TECHNICAL, "Core concepts for efficient problem solving."),
    ("FastAPI", SkillCategory.TECHNICAL, "Python framework for building APIs."),
    ("React", SkillCategory.TECHNICAL, "JavaScript library for building user interfaces."),
    ("Git", SkillCategory.TECHNICAL, "Version control system for software development."),
    ("Cybersecurity", SkillCategory.TECHNICAL, "Protection of systems, networks and data."),
    ("Cloud Computing", SkillCategory.TECHNICAL, "Use of remote computing infrastructure and services."),

    # Analytical
    ("Data Analysis", SkillCategory.ANALYTICAL, "Analyzing data to extract useful insights."),
    ("Statistics", SkillCategory.ANALYTICAL, "Methods for collecting, analyzing and interpreting data."),
    ("Excel", SkillCategory.ANALYTICAL, "Spreadsheet analysis and business reporting."),
    ("Power BI", SkillCategory.ANALYTICAL, "Business intelligence and dashboarding tool."),
    ("Tableau", SkillCategory.ANALYTICAL, "Data visualization and dashboarding platform."),
    ("Business Analytics", SkillCategory.ANALYTICAL, "Using data and analysis for business decisions."),
    ("Financial Analysis", SkillCategory.ANALYTICAL, "Evaluating financial performance and decisions."),
    ("Problem Solving", SkillCategory.ANALYTICAL, "Structured reasoning for solving complex problems."),

    # Business
    ("Business Strategy", SkillCategory.BUSINESS, "Planning and decision-making for organizational goals."),
    ("Marketing", SkillCategory.BUSINESS, "Promotion, customer understanding and market strategy."),
    ("Finance", SkillCategory.BUSINESS, "Managing money, investments and financial decisions."),
    ("Entrepreneurship", SkillCategory.BUSINESS, "Building and managing new ventures."),
    ("Operations Management", SkillCategory.BUSINESS, "Managing processes, resources and efficiency."),
    ("Product Management", SkillCategory.BUSINESS, "Managing product strategy and development."),
    ("Market Research", SkillCategory.BUSINESS, "Studying customers, competitors and markets."),

    # Communication
    ("Communication", SkillCategory.COMMUNICATION, "Clear written and verbal communication."),
    ("Presentation Skills", SkillCategory.COMMUNICATION, "Presenting ideas clearly to an audience."),
    ("Business Writing", SkillCategory.COMMUNICATION, "Professional written communication."),

    # Leadership
    ("Leadership", SkillCategory.LEADERSHIP, "Guiding teams and taking responsibility."),
    ("Team Management", SkillCategory.LEADERSHIP, "Coordinating people toward shared goals."),
    ("Decision Making", SkillCategory.LEADERSHIP, "Selecting effective actions from available choices."),

    # Design
    ("UI Design", SkillCategory.DESIGN, "Designing usable digital interfaces."),
    ("UX Design", SkillCategory.DESIGN, "Designing effective user experiences."),
    ("Graphic Design", SkillCategory.DESIGN, "Visual communication through graphics and layouts."),

    # Domain knowledge
    ("Research", SkillCategory.DOMAIN_KNOWLEDGE, "Systematic investigation and evidence gathering."),
    ("Economics", SkillCategory.DOMAIN_KNOWLEDGE, "Study of markets, resources and economic systems."),
    ("Healthcare Analytics", SkillCategory.DOMAIN_KNOWLEDGE, "Applying analytics in healthcare contexts."),
    ("Legal Research", SkillCategory.DOMAIN_KNOWLEDGE, "Finding and analyzing legal information."),

    # Soft skills
    ("Time Management", SkillCategory.SOFT_SKILLS, "Organizing tasks and time effectively."),
    ("Adaptability", SkillCategory.SOFT_SKILLS, "Adjusting effectively to changing situations."),
    ("Critical Thinking", SkillCategory.SOFT_SKILLS, "Evaluating information logically and carefully."),
    ("Collaboration", SkillCategory.SOFT_SKILLS, "Working effectively with others."),
]


def seed_skills():
    db = SessionLocal()

    try:
        created = 0
        skipped = 0

        for name, category, description in SKILLS:
            existing = db.scalar(
                select(Skill).where(
                    Skill.name == name
                )
            )

            if existing:
                skipped += 1
                print(f"SKIP: {name}")
                continue

            skill = Skill(
                name=name,
                category=category,
                description=description,
            )

            db.add(skill)
            created += 1
            print(f"ADD:  {name}")

        db.commit()

        print()
        print("==============================")
        print("Skill seeding completed")
        print(f"Created: {created}")
        print(f"Skipped: {skipped}")
        print("==============================")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_skills()