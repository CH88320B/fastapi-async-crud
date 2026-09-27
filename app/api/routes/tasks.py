from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.task import Page, TaskCreate, TaskFilters, TaskRead, TaskUpdate
from app.services import tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=Page[TaskRead])
async def list_tasks(
    user: CurrentUser,
    session: SessionDep,
    filters: Annotated[TaskFilters, Query()],
) -> Page[TaskRead]:
    return await tasks.list_tasks(session, user, filters)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(data: TaskCreate, user: CurrentUser, session: SessionDep) -> TaskRead:
    return TaskRead.model_validate(await tasks.create_task(session, user, data))


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, user: CurrentUser, session: SessionDep) -> TaskRead:
    return TaskRead.model_validate(await tasks.get_task(session, user, task_id))


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, data: TaskUpdate, user: CurrentUser, session: SessionDep) -> TaskRead:
    return TaskRead.model_validate(await tasks.update_task(session, user, task_id, data))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, user: CurrentUser, session: SessionDep) -> Response:
    await tasks.delete_task(session, user, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
