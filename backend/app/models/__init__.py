"""
Import every model module here. Alembic's autogenerate (and SQLAlchemy's
Base.metadata) only knows about a table if the Python class defining it
has actually been imported somewhere in the process — so this file's only
job is to make sure that happens exactly once, in one place.
"""

from app.models.user import User, UserRole  # noqa: F401
from app.models.profile import (  # noqa: F401
    StudentProfile,
    RecruiterProfile,
    AcademicianProfile,
    InstitutionProfile,
)
from app.models.skill import Skill, SkillCategory, skill_relations  # noqa: F401
from app.models.student_skill import StudentSkill, ProficiencyLevel, SkillSource  # noqa: F401
from app.models.career import CareerRole, CareerSkillRequirement  # noqa: F401
from app.models.institution import Institution, InstitutionType  # noqa: F401
from app.models.organization import Organization, OrganizationType  # noqa: F401
from app.models.assessment import (  # noqa: F401
    Assessment,
    AssessmentQuestion,
    QuestionOption,
    AssessmentAttempt,
    AssessmentSkillResult,
    AssessmentType,
    DifficultyLevel,
    QuestionType,
    AttemptStatus,
)
from app.models.project import (  # noqa: F401
    Project,
    ProjectSkill,
    ProjectType,
    ProjectDifficulty,
    ProjectStatus,
    ProjectVisibility,
    ProjectResource,
    ProjectMeeting,
)
from app.models.internship import (  # noqa: F401
    Internship,
    InternshipSkill,
    WorkMode,
    InternshipType,
    ExperienceLevel,
    InternshipStatus,
)
from app.models.application import (  # noqa: F401
    Application,
    ApplicationStatus,
    ApplicationStatusHistory,
)
from app.models.connection import Connection, ConnectionStatus  # noqa: F401
from app.modules.posts.models import (
    Post,
    PostMedia,
    PostLike,
    PostComment,
    SavedPost,
    PostReport,
    PostType,
    MediaType,
)  # noqa: F401
from app.modules.notifications.models import (
    Notification,
    NotificationType,
)  # noqa: F401
from app.modules.mentorship.models import (
    MentorProfile,
    MentorSkill,
    MentoringMode,
)  # noqa: F401
from app.modules.professionals.models import ProfessionalProfile  # noqa: F401
from app.models.project import (
    Project,
    ProjectSkill,
    ProjectMember,
    ProjectApplication,
)
