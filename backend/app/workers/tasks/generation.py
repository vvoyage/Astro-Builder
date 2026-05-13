"""Celery task для полного pipeline генерации: A0 → A1 → A2 → сохранение в MinIO → сборка."""
from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

import redis as redis_lib

from app.agents.architect import ArchitectAgent
from app.agents.code_generator import CodeGeneratorAgent
from app.agents.optimizer import OptimizerAgent
from app.core.config import settings
from app.db.database import AsyncSessionFactory, engine
from app.repositories import project as project_repo
from app.repositories import snapshot as snapshot_repo
from app.services.storage import StorageService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="generation.run_pipeline", max_retries=2)
def run_generation_pipeline(
    self, project_id: str, user_id: str, prompt: str, ai_model: str, template_prompt: str | None = None
) -> dict:
    """
    Запускает полный pipeline: A0 → A1 → A2 → MinIO → build.
    Прогресс пишется в Redis: generation:{project_id}:status = {"stage": ..., "progress": ...}
    """
    try:
        storage = StorageService()
    except Exception as exc:
        logger.exception("Failed to initialize StorageService for project %s", project_id)
        _set_redis_status(project_id, "failed", 0)
        raise self.retry(exc=exc, countdown=10)

    try:
        asyncio.run(_run_pipeline(project_id, user_id, prompt, ai_model, storage, template_prompt=template_prompt))
    except Exception as exc:
        logger.exception("Generation pipeline failed for project %s: %s", project_id, exc)
        _set_redis_status(project_id, "failed", 0)
        raise self.retry(exc=exc, countdown=10)
    return {"project_id": project_id, "status": "building"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _expand_with_dependents(files_to_regen: list[str], sorted_files: list[dict]) -> list[str]:
    """BFS по обратному графу зависимостей: возвращает files_to_regen + все файлы, которые зависят от них."""
    # Строим обратный граф: dependent -> set of dependencies
    reverse: dict[str, set[str]] = {f["path"]: set() for f in sorted_files}
    for f in sorted_files:
        for dep in f.get("dependencies", []):
            if dep in reverse:
                reverse[dep].add(f["path"])

    # BFS
    queue = list(files_to_regen)
    visited: set[str] = set(files_to_regen)
    while queue:
        current = queue.pop(0)
        for dependent in reverse.get(current, set()):
            if dependent not in visited:
                visited.add(dependent)
                queue.append(dependent)

    # Возвращаем в исходном топологическом порядке
    return [f["path"] for f in sorted_files if f["path"] in visited]


def _topological_sort(files: list[dict]) -> list[dict]:
    """Сортирует файлы так, чтобы зависимости шли раньше зависящих от них файлов."""
    path_to_file = {f["path"]: f for f in files}
    visited: set[str] = set()
    result: list[dict] = []

    def visit(path: str) -> None:
        if path in visited:
            return
        visited.add(path)
        file = path_to_file.get(path)
        if file is None:
            return
        for dep in file.get("dependencies", []):
            visit(dep)
        result.append(file)

    for f in files:
        visit(f["path"])

    return result


def _set_redis_status(project_id: str, stage: str, progress: int) -> None:
    try:
        r = redis_lib.from_url(settings.REDIS_URL)
        r.set(
            f"generation:{project_id}:status",
            json.dumps({"stage": stage, "progress": progress}),
        )
    except Exception:
        logger.warning("Could not write Redis status for project %s", project_id)


async def _run_pipeline(
    project_id: str, user_id: str, prompt: str, ai_model: str, storage: StorageService, template_prompt: str | None = None
) -> None:
    await engine.dispose()
    await _pipeline(project_id, user_id, prompt, ai_model, storage, template_prompt=template_prompt)


async def _pipeline(
    project_id: str, user_id: str, prompt: str, ai_model: str, storage: StorageService, template_prompt: str | None = None
) -> None:
    async with AsyncSessionFactory() as db:
        await project_repo.update_status(db, UUID(project_id), "generating")
        await db.commit()

    _set_redis_status(project_id, "optimizer", 10)
    logger.info("Pipeline started: project=%s user=%s model=%s", project_id, user_id, ai_model)

    # A0 — разбираем промпт пользователя в структурированную спецификацию
    optimizer = OptimizerAgent(model=ai_model)
    optimizer_input: dict = {"prompt": prompt}
    if template_prompt:
        optimizer_input["template_slug"] = template_prompt
    structured_spec: dict = await optimizer.run(optimizer_input)
    logger.info("A0 structured spec: %s", json.dumps(structured_spec, ensure_ascii=False, indent=2))
    _set_redis_status(project_id, "optimizer", 25)

    # A1 — по спецификации строим список файлов проекта
    _set_redis_status(project_id, "architect", 30)
    architect = ArchitectAgent(model=ai_model)
    file_specs: dict = await architect.run(structured_spec)
    files_list: list[dict] = file_specs.get("files", [])
    if not files_list:
        logger.error("A1 returned empty files list! Full response: %s", file_specs)
    else:
        logger.info("A1 file plan (%d files): %s", len(files_list), json.dumps(files_list, ensure_ascii=False, indent=2))
    _set_redis_status(project_id, "architect", 45)

    # A2 — генерируем код файлов последовательно в порядке топологической сортировки,
    # передавая каждому следующему файлу код уже сгенерированных зависимостей
    _set_redis_status(project_id, "code_generator", 50)
    code_gen = CodeGeneratorAgent(model=ai_model)
    sorted_files = _topological_sort(files_list)
    generated_files: dict[str, str] = {}
    for i, file_spec in enumerate(sorted_files):
        deps_context = {
            path: content
            for path, content in generated_files.items()
            if path in file_spec.get("dependencies", [])
        }
        result = await code_gen.run({
            "file": file_spec,
            "project_spec": structured_spec,
            "generated_files": deps_context,
        })
        generated_files[result["path"]] = result["content"]
        progress = 50 + int((i + 1) / len(sorted_files) * 15)
        _set_redis_status(project_id, "code_generator", progress)
    logger.info("A2 generated %d files: %s", len(generated_files), list(generated_files.keys()))
    _set_redis_status(project_id, "code_generator", 65)

    # Critic — проверяем качество, при необходимости перегенерируем проблемные файлы
    _set_redis_status(project_id, "critic", 66)
    try:
        from app.agents.critic import CriticAgent  # noqa: PLC0415
        critic = CriticAgent(model=ai_model)
        critic_result = await critic.run({"files": generated_files, "spec": structured_spec})
        logger.info("Critic result: approved=%s score=%s issues=%d",
                    critic_result.get("approved"), critic_result.get("score"), len(critic_result.get("issues", [])))
        if not critic_result.get("approved", True) and critic_result.get("regenerate_files"):
            to_regen = _expand_with_dependents(critic_result["regenerate_files"], sorted_files)
            logger.info("Critic: regenerating %d files: %s", len(to_regen), to_regen)
            critique_issues = critic_result.get("issues", [])
            for i, file_path in enumerate(to_regen):
                file_spec = next((f for f in sorted_files if f["path"] == file_path), None)
                if file_spec is None:
                    continue
                deps_context = {
                    path: content
                    for path, content in generated_files.items()
                    if path in file_spec.get("dependencies", [])
                }
                result = await code_gen.run({
                    "file": file_spec,
                    "project_spec": structured_spec,
                    "generated_files": deps_context,
                    "critique": critique_issues,
                })
                generated_files[result["path"]] = result["content"]
                progress = 66 + int((i + 1) / len(to_regen) * 2)
                _set_redis_status(project_id, "critic", progress)
    except Exception:
        logger.warning("Critic failed, continuing best-effort", exc_info=True)
    _set_redis_status(project_id, "critic", 68)

    # сохраняем исходники в MinIO
    _set_redis_status(project_id, "saving", 70)
    await storage.save_source_files(user_id, project_id, generated_files)
    logger.info("Source files saved for project %s", project_id)
    _set_redis_status(project_id, "saving", 80)

    # создаём снапшот v1 — начальное состояние проекта (только src/-файлы, остальные не редактируются)
    src_files = {p: c for p, c in generated_files.items() if p.lstrip("/").startswith("src/")}
    async with AsyncSessionFactory() as db:
        for path, content in src_files.items():
            file_path = path.lstrip("/").removeprefix("src/")
            snap_path = f"projects/{user_id}/{project_id}/snapshots/v1/{file_path}"
            await storage.save_file("projects", snap_path, content.encode("utf-8"))
            await snapshot_repo.create(
                db,
                project_id=UUID(project_id),
                version=1,
                minio_path=snap_path,
                description=f"Первоначальная генерация: {prompt[:200]}",
            )
        await project_repo.set_active_snapshot_version(db, UUID(project_id), 1)
        await db.commit()
    logger.info("Initial snapshot v1 created for project %s (%d src files)", project_id, len(src_files))

    # запускаем сборку (импорт здесь, чтобы не было circular import на уровне модуля)
    from app.workers.tasks.build import run_build  # noqa: PLC0415
    run_build.delay(project_id, user_id)
    _set_redis_status(project_id, "building", 85)
    logger.info("Build task queued for project %s", project_id)
