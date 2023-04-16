from pydantic import BaseModel, Field


class InstSchema(BaseModel):
    id: int = Field(...)
    name: str = Field(...)


class CourseSchema(BaseModel):
    id: int = Field(...)
    name: str = Field(...)
    inst_id: int = Field(...)


class GroupSchema(BaseModel):
    id: int = Field(...)
    name: str = Field(...)
    course_id: int = Field(...)
    inst_id: int = Field(...)


class DisciplineSchema(BaseModel):
    number: str = Field(...)
    name: str = Field(...)
    room: str = Field(...)
    week_type: str = Field(...)
    teacher: str = Field(...)
    event_type: str = Field(...)
    event_subgroup: str = Field(...)


class DayScheduleSchema(BaseModel):
    index: int = Field(...)
    name: str = Field(...)
    disciplines: list[DisciplineSchema] = Field(...)


class ScheduleSchema(BaseModel):
    id: int = Field(...)
    name: str = Field(...)
    days: list[DayScheduleSchema] = Field(...)
