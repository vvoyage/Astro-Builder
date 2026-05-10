"""A2 CodeGeneratorAgent: по спецификации файла от A1 генерирует его исходный код."""
from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent


class CodeGeneratorAgent(BaseAgent):
    """A2: генерирует код файла по спецификации от ArchitectAgent."""

    SYSTEM_PROMPT = """Ты — разработчик Astro-сайтов.
Напиши код файла по заданной спецификации. Используй Astro, TypeScript, Tailwind CSS.
Выведи ТОЛЬКО код файла без пояснений.

КРИТИЧЕСКИ ВАЖНО для файла src/layouts/Layout.astro:
- В <head> ОБЯЗАТЕЛЬНО добавь ИМЕННО ТАК (с атрибутом is:inline): <script is:inline src="https://cdn.tailwindcss.com"></script>
- Атрибут is:inline ОБЯЗАТЕЛЕН — без него Astro удалит этот тег при сборке
- Никаких @apply директив в <style> — только Tailwind utility-классы напрямую в HTML
- Никаких <link rel="stylesheet" href="...tailwind..."> — только тег <script is:inline> выше

СТРОГИЕ ОГРАНИЧЕНИЯ (нарушение ломает сборку):
- НЕ создавай динамические маршруты: никаких файлов вида [slug].astro, [id].astro и т.п.
- НЕ используй getStaticPaths() — только статические страницы
- НЕ пиши сложный кастомный JavaScript (слайдеры, карусели, анимации на JS)
- НЕ импортируй внешние npm-пакеты кроме тех что в package.json проекта
- Галереи и карточки — только статичная HTML-сетка через Tailwind grid/flex, без JS
- Весь интерактив (если нужен) — только через CSS (hover:, focus: классы Tailwind)"""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """input_data: {"file": {...}, "project_spec": {...}, "generated_files": {path: content}}.
        Возвращает {"path": str, "content": str}."""
        file_spec = input_data["file"]
        project_spec = input_data.get("project_spec", {})
        generated_files: dict[str, str] = input_data.get("generated_files", {})

        user_prompt = (
            f"Файл для генерации: {json.dumps(file_spec, ensure_ascii=False)}\n"
            f"Контекст проекта: {json.dumps(project_spec, ensure_ascii=False, indent=2)}"
        )

        if generated_files:
            deps_text = "\n\n".join(
                f"--- {path} ---\n{content}"
                for path, content in generated_files.items()
            )
            user_prompt += (
                f"\n\nУже сгенерированные зависимости (используй их интерфейсы точно — "
                f"пропсы, слоты, имена компонентов должны совпадать):\n{deps_text}"
            )

        critique: list[dict] = input_data.get("critique", [])
        if critique:
            issues_text = "\n".join(
                f"- [{i['severity'].upper()}] {i['description']}"
                for i in critique
                if i.get("file") == file_spec["path"]
            )
            if issues_text:
                user_prompt += f"\n\nЗамечания от ревьюера (ОБЯЗАТЕЛЬНО исправь):\n{issues_text}"

        content = await self._call_llm(self.SYSTEM_PROMPT, user_prompt)
        return {"path": file_spec["path"], "content": content}
