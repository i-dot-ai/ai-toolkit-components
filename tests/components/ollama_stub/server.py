"""
Minimal Ollama API stub for component testing.
Mimics POST /api/chat and returns canned responses.

If the request body contains "format": "json" (data_extractor uses this),
returns a JSON string in message.content.
Otherwise returns plain masked text (pii_cleanse and pii_eval expect this).
"""
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# Canned JSON extraction result matching extracta_config.json field names
CANNED_EXTRACTION = json.dumps({
    "issue": "signal failure",
    "impact": "minor delays",
    "resolution_action": "engineer dispatched",
    "severity_indicator": "3",
})

# Canned PII-masked text
CANNED_MASKED = "[PERSON] reported a signal failure at [LOCATION] at [TIME]."


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True, silent=True) or {}
    if body.get("format") == "json":
        content = CANNED_EXTRACTION
    else:
        content = CANNED_MASKED
    return jsonify({
        "model": body.get("model", "stub"),
        "message": {"role": "assistant", "content": content},
        "done": True,
    })


@app.route("/api/tags", methods=["GET"])
def tags():
    """Health-check endpoint — some clients call this to verify Ollama is up."""
    return jsonify({"models": [{"name": "stub"}]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=11434)
