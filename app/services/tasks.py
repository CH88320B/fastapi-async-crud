import math

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import Task, TaskPriority, User
from app.schemas.task import Page, TaskCreate, TaskFilters, TaskRead, TaskSortField, TaskUpdate

# Sort priority by business meaning (high > medium > low), not alphabetically.
_PRIORITY_RANK = case(
    {TaskPriority.HIGH.value: 3, TaskPriority.MEDIUM.value: 2, TaskPriority.LOW.value: 1},
    value=Task.priority,
)

_SORT_COLUMNS = {
    TaskSortField.CREATED_AT: Task.created_at,
    TaskSortField.DUE_DATE: Task.due_date,
    TaskSortField.PRIORITY: _PRIORITY_RANK,
    TaskSortField.TITLE: Task.title,
}


def _apply_filters(stmt: Select, owner: User, f: TaskFilters) -> Select:
    stmt = stmt.where(Task.owner_id == owner.id)
    if f.status:
        stmt = stmt.where(Task.status == f.status)
    if f.priority:
        stmt = stmt.where(Task.priority == f.priority)
    if f.search:
        pattern = f"%{f.search.strip()}%"
        stmt = stmt.where(Task.title.ilike(pattern) | Task.description.ilike(pattern))
    if f.due_before:
        stmt = stmt.where(Task.due_date <= f.due_before)
    return stmt


async def list_tasks(session: AsyncSession, owner: User, f: TaskFilters) -> Page[TaskRead]:
    total = await session.scalar(_apply_filters(select(func.count(Task.id)), owner, f)) or 0

    column = _SORT_COLUMNS[f.sort]
    order = column.desc().nulls_last() if f.descending else column.asc().nulls_last()
    stmt = (
        _apply_filters(select(Task), owner, f)
        .order_by(order, Task.id)
        .offset((f.page - 1) * f.size)
        .limit(f.size)
    )
    rows = (await session.scalars(stmt)).all()

    return Page[TaskRead](
        items=[TaskRead.model_validate(t) for t in rows],
        total=total,
        page=f.page,
        size=f.size,
        pages=math.ceil(total / f.size) if total else 0,
    )


async def get_task(session: AsyncSession, owner: User, task_id: int) -> Task:
    # Scoped to the owner: another user's task is indistinguishable from a missing one (no ID probing).
    task = await session.scalar(select(Task).where(Task.id == task_id, Task.owner_id == owner.id))
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")
    return task


async def create_task(session: AsyncSession, owner: User, data: TaskCreate) -> Task:
    task = Task(**data.model_dump(), owner_id=owner.id)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def update_task(session: AsyncSession, owner: User, task_id: int, data: TaskUpdate) -> Task:
    task = await get_task(session, owner, task_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await session.commit()
    await session.refresh(task)
    return task


async def delete_task(session: AsyncSession, owner: User, task_id: int) -> None:
    task = await get_task(session, owner, task_id)
    await session.delete(task)
    await session.commit()
