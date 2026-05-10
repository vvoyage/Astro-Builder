"""Unit-тесты для CriticAgent.

Запуск:
    cd backend
    pytest tests/test_critic_agent.py -v
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# Хелпер
# ---------------------------------------------------------------------------

def _make_critic(llm_response: str):
    """Создаёт CriticAgent с замоканным _call_llm."""
    from app.agents.critic import CriticAgent
    agent = CriticAgent.__new__(CriticAgent)
    agent.model = "test-model"
    agent.max_retries = 1
    agent._call_llm = AsyncMock(return_value=llm_response)
    return agent


SAMPLE_FILES = {
    "src/pages/index.astro": "---\n---\n<Layout>\n<h1>Hello</h1>\n</Layout>",
    "src/layouts/Layout.astro": '<html><head><script is:inline src="https://cdn.tailwindcss.com"></script></head><body><slot /></body></html>',
    "src/components/Header.astro": "---\n---\n<header>Nav</header>",
}

SAMPLE_SPEC = {
    "site_name": "Test Site",
    "pages": [{"name": "Home", "path": "/", "sections": ["hero", "features"]}],
}

APPROVED_RESPONSE = json.dumps({
    "approved": True,
    "score": 95,
    "issues": [],
    "regenerate_files": [],
})

REJECTED_RESPONSE = json.dumps({
    "approved": False,
    "score": 42,
    "issues": [
        {"file": "src/pages/index.astro", "severity": "critical", "description": "Секция features не реализована"},
        {"file": "src/components/Header.astro", "severity": "warning", "description": "TODO-заглушка в навигации"},
    ],
    "regenerate_files": ["src/pages/index.astro"],
})


# ---------------------------------------------------------------------------
# run() — базовые кейсы
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestCriticAgentRun:

    async def test_approved_response_returns_correct_fields(self):
        agent = _make_critic(APPROVED_RESPONSE)
        result = await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        assert result["approved"] is True
        assert result["score"] == 95
        assert result["issues"] == []
        assert result["regenerate_files"] == []

    async def test_rejected_response_returns_correct_fields(self):
        agent = _make_critic(REJECTED_RESPONSE)
        result = await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        assert result["approved"] is False
        assert result["score"] == 42
        assert len(result["issues"]) == 2
        assert result["regenerate_files"] == ["src/pages/index.astro"]

    async def test_issues_structure_preserved(self):
        agent = _make_critic(REJECTED_RESPONSE)
        result = await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        issue = result["issues"][0]
        assert issue["file"] == "src/pages/index.astro"
        assert issue["severity"] == "critical"
        assert "features" in issue["description"]

    async def test_calls_llm_once(self):
        agent = _make_critic(APPROVED_RESPONSE)
        await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        agent._call_llm.assert_called_once()

    async def test_spec_included_in_llm_call(self):
        agent = _make_critic(APPROVED_RESPONSE)
        await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        _, user_prompt = agent._call_llm.call_args[0]
        assert "Test Site" in user_prompt

    async def test_file_paths_included_in_llm_call(self):
        agent = _make_critic(APPROVED_RESPONSE)
        await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        _, user_prompt = agent._call_llm.call_args[0]
        for path in SAMPLE_FILES:
            assert path in user_prompt

    async def test_file_contents_included_in_llm_call(self):
        agent = _make_critic(APPROVED_RESPONSE)
        await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        _, user_prompt = agent._call_llm.call_args[0]
        assert "Hello" in user_prompt

    async def test_empty_files_dict_does_not_crash(self):
        agent = _make_critic(APPROVED_RESPONSE)
        result = await agent.run({"files": {}, "spec": SAMPLE_SPEC})
        assert result["approved"] is True

    async def test_missing_files_key_uses_empty(self):
        agent = _make_critic(APPROVED_RESPONSE)
        result = await agent.run({"spec": SAMPLE_SPEC})
        assert "approved" in result

    async def test_missing_spec_key_uses_empty(self):
        agent = _make_critic(APPROVED_RESPONSE)
        result = await agent.run({"files": SAMPLE_FILES})
        assert "approved" in result


# ---------------------------------------------------------------------------
# Fallback при ошибке парсинга
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestCriticAgentFallback:

    async def test_invalid_json_returns_approved_true(self):
        agent = _make_critic("это не JSON вообще")
        result = await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        assert result["approved"] is True
        assert result["score"] == 100
        assert result["issues"] == []
        assert result["regenerate_files"] == []

    async def test_llm_raises_exception_returns_approved_true(self):
        from app.agents.critic import CriticAgent
        agent = CriticAgent.__new__(CriticAgent)
        agent.model = "test-model"
        agent.max_retries = 1
        agent._call_llm = AsyncMock(side_effect=RuntimeError("LLM timeout"))
        result = await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        assert result["approved"] is True
        assert result["score"] == 100

    async def test_partial_json_missing_fields_gets_defaults(self):
        """LLM вернул JSON без некоторых полей — fallback на дефолты."""
        partial = json.dumps({"approved": False, "score": 60})
        agent = _make_critic(partial)
        result = await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        assert result["approved"] is False
        assert result["score"] == 60
        assert result["issues"] == []
        assert result["regenerate_files"] == []

    async def test_markdown_json_block_is_parsed(self):
        """_extract_json должен обработать ответ в markdown-блоке."""
        wrapped = f"```json\n{APPROVED_RESPONSE}\n```"
        agent = _make_critic(wrapped)
        result = await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        assert result["approved"] is True
        assert result["score"] == 95


# ---------------------------------------------------------------------------
# Типы возвращаемых значений
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestCriticAgentReturnTypes:

    async def test_approved_is_bool(self):
        # LLM может вернуть строку "true" — проверяем bool-кастинг
        response = json.dumps({"approved": True, "score": 80, "issues": [], "regenerate_files": []})
        agent = _make_critic(response)
        result = await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        assert isinstance(result["approved"], bool)

    async def test_score_is_int(self):
        response = json.dumps({"approved": True, "score": 75.5, "issues": [], "regenerate_files": []})
        agent = _make_critic(response)
        result = await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        assert isinstance(result["score"], int)
        assert result["score"] == 75

    async def test_issues_is_list(self):
        agent = _make_critic(APPROVED_RESPONSE)
        result = await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        assert isinstance(result["issues"], list)

    async def test_regenerate_files_is_list(self):
        agent = _make_critic(REJECTED_RESPONSE)
        result = await agent.run({"files": SAMPLE_FILES, "spec": SAMPLE_SPEC})
        assert isinstance(result["regenerate_files"], list)


# ---------------------------------------------------------------------------
# Усечение длинных файлов
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestCriticAgentFileTruncation:

    async def test_long_file_is_truncated_in_prompt(self):
        """Файлы длиннее 3000 символов обрезаются с маркером [truncated]."""
        long_content = "x" * 5000
        agent = _make_critic(APPROVED_RESPONSE)
        await agent.run({"files": {"src/pages/big.astro": long_content}, "spec": {}})
        _, user_prompt = agent._call_llm.call_args[0]
        assert "[truncated]" in user_prompt
        # Полного содержимого нет — только первые 3000 символов
        assert "x" * 3001 not in user_prompt

    async def test_short_file_is_not_truncated(self):
        """Файлы до 3000 символов — без маркера."""
        short_content = "short content"
        agent = _make_critic(APPROVED_RESPONSE)
        await agent.run({"files": {"src/pages/short.astro": short_content}, "spec": {}})
        _, user_prompt = agent._call_llm.call_args[0]
        assert "[truncated]" not in user_prompt
        assert short_content in user_prompt
