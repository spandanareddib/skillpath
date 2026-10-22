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
