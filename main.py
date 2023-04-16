import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI

from app.cron import repeat_every
from app.models import (
    InstSchema, CourseSchema, GroupSchema, ScheduleSchema, DayScheduleSchema,
    DisciplineSchema
)

app = FastAPI()

inst_models: list[InstSchema] = []
course_models: list[CourseSchema] = []
groups_models: dict[int, GroupSchema] = {}
schedule_by_group_models: dict[int, ScheduleSchema] = {}


@app.on_event("startup")
@repeat_every(seconds=60 * 60)  # 1 hour
async def parse_schedule():
    await parse_groups()
    schedule_by_group_models.clear()


@app.post('/force_parse')
async def parse():
    await parse_schedule()


@app.get('/insts', response_model=list[InstSchema])
async def insts():
    return inst_models


@app.get('/courses', response_model=list[CourseSchema])
async def courses():
    return course_models


@app.get('/groups', response_model=list[GroupSchema])
async def groups():
    return list(groups_models.values())


@app.get('/schedule/{group_id}', response_model=ScheduleSchema)
async def group_schedule(group_id: int):
    schedule: ScheduleSchema | None = schedule_by_group_models.get(group_id)

    if schedule is None:
        schedule = await parse_group_schedule(group_id)
        schedule_by_group_models[group_id] = schedule

    return schedule


async def parse_groups():
    page = requests.get('https://pnu.edu.ru/rasp/groups/')
    soup = BeautifulSoup(page.text, 'html.parser')

    inst_models.clear()
    course_models.clear()
    groups_models.clear()

    parsed_insts = soup.find_all(class_='inst_name')
    for inst_index, inst in enumerate(parsed_insts):
        inst_model = InstSchema(
            id=inst_index,
            name=inst.text.strip(),
        )
        inst_models.append(inst_model)

        # курсы (заголовок)
        parsed_courses = inst.findNextSibling().find_all('tr')[0].find_all('th')

        # группы (по курсам)
        parsed_groups = inst.findNextSibling().find_all('tr')[1].find_all('td')

        for course_index, course in enumerate(parsed_courses):
            course_model = CourseSchema(
                id=inst_index * 1000 + course_index,
                name=course.text.strip(),
                inst_id=inst_model.id,
            )
            course_models.append(course_model)

            groups_by_course = parsed_groups[course_index].find_all('a')
            for group in groups_by_course:
                group_id = group.get('href')[:-1]

                group_model = GroupSchema(
                    id=group_id,
                    name=group.text.strip(),
                    course_id=course_model.id,
                    inst_id=inst_model.id,
                )
                groups_models[group_id] = group_model


async def parse_group_schedule(group_id: int) -> ScheduleSchema:
    page = requests.get(f'https://pnu.edu.ru/rasp/groups/{group_id}/')
    soup = BeautifulSoup(page.text, 'html.parser')

    parsed_weekdays = soup.find_all(id='all_weeks')[0].find_all(['h3', 'table'])

    step = 2
    stop_index = len(parsed_weekdays)
    day_index = 0

    days_models: list[DayScheduleSchema] = []

    for leftIndex in range(0, stop_index, step):
        right_index = leftIndex + step
        if right_index <= stop_index:
            parsed_schedule_day = parsed_weekdays[leftIndex:right_index]

            parsed_disciplines = parsed_schedule_day[1].find_all('tr')

            prev_discipline_number = ''
            discipline_models: list[DisciplineSchema] = []

            for disc in parsed_disciplines:
                discipline_number = disc.find(class_='time-hour')

                if discipline_number is None:
                    discipline_number = prev_discipline_number
                else:
                    discipline_number = discipline_number.text.strip()
                    prev_discipline_number = discipline_number

                discipline_name: str = disc.find(class_='time-discipline').contents[2].text.strip()
                if discipline_name == '':
                    next_sibling = disc.find(class_='time-discipline').find(
                        class_='event-type').next_sibling
                    if next_sibling is not None:
                        discipline_name = next_sibling.strip()

                discipline_room: str = disc.find(class_='time-room').text.strip()
                discipline_week_type: str = disc.find(class_='time-weektype').text.strip()
                discipline_teacher: str = disc.find(class_='time-prepod').text.strip()
                discipline_event_type: str = disc.find(class_='event-type').text.strip()

                discipline_event_subgroup = disc.find(class_='event-subgroup')
                if discipline_event_subgroup is None:
                    discipline_event_subgroup = ''
                else:
                    discipline_event_subgroup = discipline_event_subgroup.text.strip()

                discipline_model = DisciplineSchema(
                    number=discipline_number,
                    name=discipline_name,
                    room=discipline_room,
                    week_type=discipline_week_type,
                    teacher=discipline_teacher,
                    event_type=discipline_event_type,
                    event_subgroup=discipline_event_subgroup
                )

                discipline_models.append(discipline_model)

            day_schedule_model = DayScheduleSchema(
                index=day_index,
                name=parsed_schedule_day[0].text,
                disciplines=discipline_models
            )
            days_models.append(day_schedule_model)

            day_index += 1

    group = groups_models.get(group_id)

    return ScheduleSchema(
        id=group_id,
        name=group.name if group is not None else '',
        days=days_models,
    )
