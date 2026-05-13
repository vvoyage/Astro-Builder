"""Admin users endpoints — list / get / patch / delete."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.core.dependencies import DbSession, require_role
from app.core.security.keycloak_admin import delete_keycloak_user, set_user_enabled
from app.db.models.asset import Asset
from app.db.models.deployment import Deployment
from app.db.models.project import Project
from app.db.models.snapshot import Snapshot
from app.db.models.user import User
from app.services.storage import StorageService

router = APIRouter(prefix="/admin", tags=["admin"])

_admin = Depends(require_role("admin"))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AdminProjectMeta(BaseModel):
    id: UUID
    name: str
    status: str

    model_config = {"from_attributes": True}


class AdminUserItem(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    is_active: bool
    keycloak_id: Optional[str]
    project_count: int

    model_config = {"from_attributes": True}


class AdminUserDetail(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    is_active: bool
    keycloak_id: Optional[str]
    projects: list[AdminProjectMeta]

    model_config = {"from_attributes": True}


class AdminUserPatch(BaseModel):
    is_active: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[AdminUserItem], dependencies=[_admin])
async def list_users(
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
) -> list[AdminUserItem]:
    """Пагинированный список всех пользователей с кол-вом проектов."""
    subq = (
        select(Project.user_id, func.count(Project.id).label("cnt"))
        .group_by(Project.user_id)
        .subquery()
    )
    rows = await db.execute(
        select(User, func.coalesce(subq.c.cnt, 0).label("project_count"))
        .outerjoin(subq, User.id == subq.c.user_id)
        .order_by(User.email)
        .offset(skip)
        .limit(limit)
    )
    result = []
    for user, project_count in rows.all():
        result.append(
            AdminUserItem(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                keycloak_id=user.keycloak_id,
                project_count=project_count,
            )
        )
    return result


@router.get("/users/{user_id}", response_model=AdminUserDetail, dependencies=[_admin])
async def get_user(user_id: UUID, db: DbSession) -> AdminUserDetail:
    """Детальная информация о пользователе + список его проектов (только мета)."""
    res = await db.execute(
        select(User)
        .options(selectinload(User.projects))
        .where(User.id == user_id)
    )
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return AdminUserDetail(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        keycloak_id=user.keycloak_id,
        projects=[
            AdminProjectMeta(id=p.id, name=p.name, status=p.status)
            for p in user.projects
        ],
    )


@router.patch("/users/{user_id}", response_model=AdminUserDetail, dependencies=[_admin])
async def patch_user(user_id: UUID, body: AdminUserPatch, db: DbSession) -> AdminUserDetail:
    """Обновить is_active (ban/unban). Синхронизирует статус с Keycloak."""
    res = await db.execute(
        select(User)
        .options(selectinload(User.projects))
        .where(User.id == user_id)
    )
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # снимаем проекты до flush, пока relationship ещё в памяти
    projects_snapshot = [
        AdminProjectMeta(id=p.id, name=p.name, status=p.status)
        for p in user.projects
    ]

    user.is_active = body.is_active  # type: ignore[assignment]

    if user.keycloak_id:
        await set_user_enabled(user.keycloak_id, body.is_active)

    await db.flush()
    # refresh не вызываем: он экспайрит selectinload'нутый user.projects,
    # что в async-сессии приведёт к MissingGreenlet при следующем обращении.
    # Значение is_active уже выставлено явно выше.

    return AdminUserDetail(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        keycloak_id=user.keycloak_id,
        projects=projects_snapshot,
    )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    dependencies=[_admin],
)
async def delete_user(user_id: UUID, db: DbSession) -> Response:
    """Каскадное удаление: Keycloak → MinIO assets → снапшоты → проекты → юзер."""
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 1. Keycloak
    if user.keycloak_id:
        await delete_keycloak_user(user.keycloak_id)

    # 2. MinIO — удаляем все объекты пользователя (projects/{user_id}/)
    storage = StorageService()
    try:
        await storage.delete_directory("projects", f"projects/{user_id}/")
    except Exception:
        pass  # best-effort

    # 3. Связанные записи в БД (FK order matters)
    project_ids_result = await db.execute(
        select(Project.id).where(Project.user_id == user_id)
    )
    project_ids = [row[0] for row in project_ids_result.all()]

    if project_ids:
        await db.execute(delete(Snapshot).where(Snapshot.project_id.in_(project_ids)))
        await db.execute(delete(Deployment).where(Deployment.project_id.in_(project_ids)))
        await db.execute(delete(Asset).where(Asset.project_id.in_(project_ids)))

    await db.execute(delete(Project).where(Project.user_id == user_id))
    await db.delete(user)
    await db.flush()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
