"""Flask web UI for wiki search."""

from __future__ import annotations

from pathlib import Path

from flask import Flask, request, render_template_string

from .engine import search

SEARCH_HTML = """\
<!DOCTYPE html>
<html>
<head>
    <title>Wiki Search</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #1e1e2e; color: #cdd6f4; }
        h1 { color: #89b4fa; }
        input[type=text] { width: 100%; padding: 12px; font-size: 16px; border: 1px solid #45475a; border-radius: 8px; background: #313244; color: #cdd6f4; margin-bottom: 20px; }
        input[type=text]:focus { outline: none; border-color: #89b4fa; }
        .result { margin-bottom: 24px; padding: 16px; background: #313244; border-radius: 8px; }
        .result h3 { margin: 0 0 4px 0; }
        .result h3 a { color: #89b4fa; text-decoration: none; }
        .result .meta { color: #a6adc8; font-size: 14px; }
        .result .summary { color: #bac2de; margin: 8px 0; }
        .result .snippet { color: #a6adc8; font-size: 14px; }
        .result .snippet b { color: #f9e2af; }
        .score { color: #6c7086; font-size: 12px; }
        .count { color: #a6adc8; margin-bottom: 16px; }
    </style>
</head>
<body>
    <h1>Wiki Search</h1>
    <form method="get">
        <input type="text" name="q" value="{{ query }}" placeholder="Search the wiki..." autofocus>
    </form>
    {% if results is not none %}
    <div class="count">{{ results|length }} result(s) for "{{ query }}"</div>
    {% for r in results %}
    <div class="result">
        <h3><a href="#">{{ r.title }}</a></h3>
        <div class="meta">{{ r.category }} &middot; {{ r.path }}</div>
        {% if r.summary %}<div class="summary">{{ r.summary }}</div>{% endif %}
        {% if r.snippet %}<div class="snippet">{{ r.snippet|safe }}</div>{% endif %}
        <div class="score">Score: {{ "%.2f"|format(r.score) }}</div>
    </div>
    {% endfor %}
    {% endif %}
</body>
</html>
"""


def create_app(vault_root: Path) -> Flask:
    """Create the Flask search app."""
    app = Flask(__name__)

    @app.route("/")
    def index():
        query = request.args.get("q", "").strip()
        results = None
        if query:
            results = search(vault_root, query)
        return render_template_string(SEARCH_HTML, query=query, results=results)

    return app
