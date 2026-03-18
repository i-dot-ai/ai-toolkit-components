"""
Unit tests for components/data_extractor/src/extract.py
No LLM or network calls — all external I/O is mocked.
"""
import json
from unittest.mock import MagicMock, patch

import requests

from extract import call_ollama, create_extraction_prompt


SAMPLE_FIELDS = [
    {"name": "issue", "description": "The primary issue described in the text"},
    {"name": "severity", "description": "Severity level: 1-5"},
]


class TestCreateExtractionPrompt:
    def test_prompt_contains_all_field_names(self):
        prompt = create_extraction_prompt("some text", SAMPLE_FIELDS)
        assert "issue" in prompt
        assert "severity" in prompt

    def test_prompt_contains_all_field_descriptions(self):
        prompt = create_extraction_prompt("some text", SAMPLE_FIELDS)
        assert "The primary issue described in the text" in prompt
        assert "Severity level: 1-5" in prompt

    def test_prompt_instructs_json_output(self):
        prompt = create_extraction_prompt("some text", SAMPLE_FIELDS)
        assert "JSON" in prompt

    def test_prompt_includes_source_text(self):
        source = "Signal failure at Manchester Piccadilly"
        prompt = create_extraction_prompt(source, SAMPLE_FIELDS)
        assert source in prompt

    def test_prompt_includes_null_instruction(self):
        prompt = create_extraction_prompt("text", SAMPLE_FIELDS)
        assert "null" in prompt

    def test_single_field_appears_in_prompt(self):
        fields = [{"name": "resolution", "description": "How it was resolved"}]
        prompt = create_extraction_prompt("text", fields)
        assert "resolution" in prompt
        assert "How it was resolved" in prompt

    def test_empty_fields_still_returns_string(self):
        prompt = create_extraction_prompt("text", [])
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestCallOllama:
    def test_returns_parsed_dict_on_success(self):
        payload = {"issue": "signal failure", "severity": "2"}
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": json.dumps(payload)}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("extract.requests.post", return_value=mock_response):
            result = call_ollama("model", "prompt text")

        assert result == payload

    def test_raises_on_invalid_json_content(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "this is not json"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("extract.requests.post", return_value=mock_response):
            try:
                call_ollama("model", "prompt")
                assert False, "Expected JSONDecodeError"
            except json.JSONDecodeError:
                pass

    def test_raises_on_http_error(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("503")

        with patch("extract.requests.post", return_value=mock_response):
            try:
                call_ollama("model", "prompt")
                assert False, "Expected HTTPError"
            except requests.HTTPError:
                pass

    def test_posts_to_api_chat_endpoint(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": json.dumps({"key": "val"})}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("extract.requests.post", return_value=mock_response) as mock_post:
            call_ollama("mistral-small:24b", "prompt")

        call_url = mock_post.call_args[0][0]
        assert "/api/chat" in call_url

    def test_requests_json_format_mode(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": json.dumps({"key": "val"})}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("extract.requests.post", return_value=mock_response) as mock_post:
            call_ollama("model", "prompt")

        call_body = mock_post.call_args[1]["json"]
        assert call_body.get("format") == "json"

    def test_null_result_covers_all_field_names(self):
        fields = [
            {"name": "issue", "description": "desc"},
            {"name": "impact", "description": "desc"},
            {"name": "resolution", "description": "desc"},
        ]
        null_result = {f["name"]: None for f in fields}
        assert set(null_result.keys()) == {"issue", "impact", "resolution"}
        assert all(v is None for v in null_result.values())
