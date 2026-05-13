"""Admin stats + templates list endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.dependencies import DbSession, require_role
from app.db.models.project import Project
from app.db.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


class ProjectsByStatus(BaseModel):
    status: str
    count: int


class StatsResponse(BaseModel):
    total_users: int
    total_projects: int
    projects_by_status: list[ProjectsByStatus]
    total_templates: int


@router.get(
    "/stats",
    response_model=StatsResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def get_stats(db: DbSession) -> StatsResponse:
    """Сводная статистика платформы."""
    from app.db.models.template import Template

    total_users_row = await db.execute(select(func.count()).select_from(User))
    total_users: int = total_users_row.scalar_one()

    total_projects_row = await db.execute(select(func.count()).select_from(Project))
    total_projects: int = total_projects_row.scalar_one()

    status_rows = await db.execute(
        select(Project.status, func.count().label("cnt")).group_by(Project.status)
    )
    projects_by_status = [
        ProjectsByStatus(status=row.status, count=row.cnt)
        for row in status_rows.all()
    ]

    total_templates_row = await db.execute(select(func.count()).select_from(Template))
    total_templates: int = total_templates_row.scalar_one()

    return StatsResponse(
        total_users=total_users,
        total_projects=total_projects,
        projects_by_status=projects_by_status,
        total_templates=total_templates,
    )


@router.get(
    "/templates",
    dependencies=[Depends(require_role("admin"))],
)
async def list_all_templates(db: DbSession) -> list[dict]:
    """Все шаблоны включая неактивные — только для admin."""
    from app.db.models.template import Template

    rows = await db.execute(select(Template).order_by(Template.slug))
    templates = rows.scalars().all()
    return [
        {
            "id": str(t.id),
            "slug": t.slug,
            "name": t.name,
            "description": t.description,
            "text_prompt": t.text_prompt,
            "is_active": t.is_active,
        }
        for t in templates
    ]
