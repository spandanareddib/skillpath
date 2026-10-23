import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import ResumeStatus, Role


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = ""
    role: Role = Role.job_seeker


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: Role


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    status: ResumeStatus
    error: str | None
    created_at: datetime.datetime


class ResumeDetail(ResumeOut):
    text: str


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    skill_id: str
    name: str
    category: str
    mentions: int
    evidence: str


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    company: str = Field(default="", max_length=200)
    description: str = Field(min_length=30, max_length=20000)


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    company: str
    created_at: datetime.datetime


class JobSkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    skill_id: str
    name: str
    category: str
    required: bool


class JobDetail(JobOut):
    description: str
    skills: list[JobSkillOut]


class MatchOut(BaseModel):
    job_id: int
    resume_id: int
    score: float
    matched: list[JobSkillOut]
    missing: list[JobSkillOut]
    extra: list[str]
