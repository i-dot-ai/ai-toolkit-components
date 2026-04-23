"""
Unit tests for components/pii_cleanse/src/cleanse.py
No LLM or network calls — all external I/O is mocked.
"""
import unittest
from unittest.mock import MagicMock, patch

import requests

import cleanse
from cleanse import build_system_prompt, call_model


class TestBuildSystemPrompt:
    def test_redact_action_produces_replace_rule(self):
        config = {"PERSON": "redact"}
        prompt = build_system_prompt(config)
        assert "replace with [PERSON]" in prompt

    def test_ignore_action_produces_leave_unchanged(self):
        config = {"DATE": "ignore"}
        prompt = build_system_prompt(config)
        assert "leave unchanged" in prompt
        assert "DATE" in prompt

    def test_non_ignore_action_treated_as_redact(self):
        config = {"ID": "mask"}
        prompt = build_system_prompt(config)
        assert "replace with [ID]" in prompt

    def test_entity_hint_appended_for_post_code(self):
        config = {"POST CODE": "redact"}
        prompt = build_system_prompt(config)
        assert "UK postcode" in prompt

    def test_entity_hint_appended_for_location(self):
        config = {"LOCATION": "ignore"}
        prompt = build_system_prompt(config)
        assert "place names" in prompt

    def test_no_hint_for_unknown_entity(self):
        config = {"CUSTOM_ENTITY": "redact"}
        prompt = build_system_prompt(config)
        assert "CUSTOM_ENTITY" in prompt
        assert "replace with [CUSTOM_ENTITY]" in prompt

    def test_prompt_contains_header(self):
        config = {"PERSON": "redact"}
        prompt = build_system_prompt(config)
        assert "You are a PII detection assistant" in prompt

    def test_prompt_contains_footer_instruction(self):
        config = {"PERSON": "redact"}
        prompt = build_system_prompt(config)
        assert "Return ONLY the modified text" in prompt

    def test_all_entities_appear_in_prompt(self):
        config = {"PERSON": "redact", "EMAIL": "redact", "DATE": "ignore"}
        prompt = build_system_prompt(config)
        assert "PERSON" in prompt
        assert "EMAIL" in prompt
        assert "DATE" in prompt

    def test_empty_config_still_returns_valid_prompt(self):
        prompt = build_system_prompt({})
        assert "You are a PII detection assistant" in prompt
        assert "Return ONLY the modified text" in prompt


class TestCallModel:
    def test_ollama_calls_api_chat_endpoint(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Hello [PERSON]"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("cleanse.requests.post", return_value=mock_response) as mock_post:
            result = call_model("Hello John", "mistral-small:24b", "ollama", "system prompt", 120)

        assert result == "Hello [PERSON]"
        call_url = mock_post.call_args[0][0]
        assert "/api/chat" in call_url

    def test_ollama_returns_message_content(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "masked output"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("cleanse.requests.post", return_value=mock_response):
            result = call_model("input text", "model", "ollama", "prompt", 120)

        assert result == "masked output"

    def test_ollama_raises_on_http_error(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500")

        with patch("cleanse.requests.post", return_value=mock_response):
            try:
                call_model("text", "model", "ollama", "prompt", 120)
                assert False, "Expected HTTPError"
            except requests.HTTPError:
                pass

    def test_openai_returns_message_content(self):
        mock_choice = MagicMock()
        mock_choice.message.content = "openai masked output"
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch("cleanse.OpenAI", return_value=mock_client):
            result = call_model("input text", "gpt-4o", "openai", "system prompt", 120)

        assert result == "openai masked output"

    def test_openai_passes_system_prompt(self):
        mock_choice = MagicMock()
        mock_choice.message.content = "result"
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch("cleanse.OpenAI", return_value=mock_client):
            call_model("text", "gpt-4o", "openai", "my system prompt", 120)

        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs[1]["messages"]
        system_messages = [m for m in messages if m["role"] == "system"]
        assert any("my system prompt" in m["content"] for m in system_messages)
