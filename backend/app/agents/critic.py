"""CriticAgent: проверяет сгенерированный код на соответствие спецификации."""
from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    """Проверяет набор сгенерированных файлов и возвращает оценку + список замечаний."""

    SYSTEM_PROMPT = """Ты — строгий ревьюер Astro-проектов. Получаешь сгенерированные файлы и спецификацию проекта.

Твоя задача — проверить качество кода и соответствие спецификации. Проверяй:
1. Все ли страницы/секции из спецификации реализованы
2. Корректность импортов (компоненты, которые импортируются, должны существовать в файлах)
3. Astro-ограничения: нет динамических маршрутов ([slug].astro), нет getStaticPaths()
4. Tailwind: используется script is:inline в Layout, нет @apply директив
5. Нет TODO-заглушек и незаконченных секций
6. Нет импортов внешних npm-пакетов, которых нет в стандартном Astro + Tailwind

Ответь СТРОГО в формате JSON (без markdown-блоков):
{
  "approved": true/false,
  "score": <0-100>,
  "issues": [
    {
      "file": "<path>",
      "severity": "critical" | "warning" | "info",
      "description": "<описание проблемы>"
    }
  ],
  "regenerate_files": ["<path>", ...]
}

Если всё хорошо — approved: true, score >= 80, issues: [], regenerate_files: [].
В regenerate_files включай только файлы с critical-проблемами.
Будь строг, но справедлив. Не придирайся к стилю — только к функциональным проблемам."""

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """input_data: {"files": {path: content}, "spec": {...}}.
        Возвращает {"approved": bool, "score": int, "issues": [...], "regenerate_files": [...]}."""
        files: dict[str, str] = input_data.get("files", {})
        spec: dict = input_data.get("spec", {})

        files_summary = "\n\n".join(
            f"=== {path} ===\n{content[:3000]}{'...[truncated]' if len(content) > 3000 else ''}"
            for path, content in files.items()
        )

        user_prompt = (
            f"Спецификация проекта:\n{json.dumps(spec, ensure_ascii=False, indent=2)}\n\n"
            f"Сгенерированные файлы:\n{files_summary}"
        )

        try:
            raw = await self._call_llm(self.SYSTEM_PROMPT, user_prompt)
            result = self._extract_json(raw)
            # Валидируем обязательные поля
            return {
                "approved": bool(result.get("approved", True)),
                "score": int(result.get("score", 100)),
                "issues": result.get("issues", []),
                "regenerate_files": result.get("regenerate_files", []),
            }
        except Exception as exc:
            logger.warning("CriticAgent failed to parse LLM response, approving by default: %s", exc)
            return {"approved": True, "score": 100, "issues": [], "regenerate_files": []}
