"""
AKIRA (Accessible Knowledge & Information Retrieval Assistant)
Main Flask Application Server (app.py)
"""

import os
import io
import re
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    Response,
)

import db
import wiki_service
import pdf_service

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

def get_db_path():
    """Retrieve configured database path (defaults to akira.db)."""
    return app.config.get("DB_PATH", db.DB_PATH)


# Ensure database tables exist upon server startup
with app.app_context():
    db.init_db(get_db_path())


@app.route("/")
def index():
    """Render the primary accessible single-page application dashboard."""
    return render_template("index.html")


@app.route("/api/search", methods=["GET"])
def api_search():
    """
    Search Wikipedia, clean article content, generate executive audio summary,
    bullet takeaways, and study flashcards.
    Query parameters:
      - q: search query string (required)
      - mode: 'quick' or 'full' (default: 'standard')
    """
    query = request.args.get("q", "").strip()
    mode = request.args.get("mode", "standard").strip()

    if not query:
        return jsonify({"status": "error", "message": "Search query cannot be empty."}), 400

    result = wiki_service.search_wikipedia(query, mode=mode)

    if result.get("status") == "success":
        # Log to SQLite search history
        try:
            db.add_search(query=query, mode=mode, db_path=get_db_path())
        except Exception as e:
            app.logger.warning(f"Could not log search history: {e}")

        # Check if already bookmarked
        result["is_bookmarked"] = db.is_bookmarked(result.get("title", ""), db_path=get_db_path())

    return jsonify(result)


@app.route("/api/history", methods=["GET"])
def get_history():
    """Retrieve recent search queries."""
    limit = request.args.get("limit", 20, type=int)
    history = db.get_history(limit=limit, db_path=get_db_path())
    return jsonify({"status": "success", "history": history})


@app.route("/api/history", methods=["DELETE"])
def clear_history():
    """Clear all search history."""
    db.clear_history(db_path=get_db_path())
    return jsonify({"status": "success", "message": "Search history cleared."})


@app.route("/api/history/<int:item_id>", methods=["DELETE"])
def delete_history_item(item_id):
    """Delete a single history entry by ID."""
    success = db.delete_history_item(item_id, db_path=get_db_path())
    return jsonify({"status": "success" if success else "error", "deleted": success})


@app.route("/api/bookmarks", methods=["GET"])
def get_bookmarks():
    """Retrieve all saved bookmarks."""
    bookmarks = db.get_bookmarks(db_path=get_db_path())
    return jsonify({"status": "success", "bookmarks": bookmarks})


@app.route("/api/bookmarks", methods=["POST"])
def add_bookmark():
    """Save an article to bookmarks."""
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    summary = data.get("summary", "").strip()
    url = data.get("url", "").strip()
    takeaways = data.get("takeaways")

    if not title:
        return jsonify({"status": "error", "message": "Article title is required."}), 400

    bookmark_id = db.add_bookmark(title=title, summary=summary, url=url, takeaways=takeaways, db_path=get_db_path())
    return jsonify({"status": "success", "id": bookmark_id, "message": f"'{title}' bookmarked."})


@app.route("/api/bookmarks/<int:bookmark_id>", methods=["DELETE"])
def delete_bookmark(bookmark_id):
    """Remove a bookmark by ID."""
    success = db.delete_bookmark(bookmark_id, db_path=get_db_path())
    return jsonify({"status": "success" if success else "error", "deleted": success})


@app.route("/api/export-pdf", methods=["GET"])
def export_pdf():
    """
    Generate and stream a study guide PDF for the requested topic.
    Query parameter:
      - q: article topic title (required)
    """
    topic = request.args.get("q", "").strip()
    if not topic:
        return jsonify({"status": "error", "message": "Missing article topic parameter 'q'."}), 400

    article_data = wiki_service.search_wikipedia(topic)
    if article_data.get("status") != "success":
        return jsonify({"status": "error", "message": "Could not retrieve article data for PDF generation."}), 404

    try:
        pdf_buffer = pdf_service.generate_study_pdf(article_data)
        safe_filename = re.sub(r"[^\w\s-]", "", article_data.get("title", "Notes")).strip().replace(" ", "_")
        filename = f"AKIRA_Study_{safe_filename}.pdf"

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        app.logger.error(f"Error generating PDF: {e}")
        return jsonify({"status": "error", "message": f"Failed to generate PDF: {str(e)}"}), 500


@app.route("/api/export-notes", methods=["GET"])
def export_notes():
    """
    Generate and stream a clean Markdown/Text study summary sheet.
    Query parameter:
      - q: article topic title (required)
    """
    topic = request.args.get("q", "").strip()
    if not topic:
        return jsonify({"status": "error", "message": "Missing topic parameter 'q'."}), 400

    data = wiki_service.search_wikipedia(topic)
    if data.get("status") != "success":
        return jsonify({"status": "error", "message": "Article not found."}), 404

    title = data.get("title", "Topic")
    summary = data.get("summary", "")
    takeaways = data.get("takeaways", [])
    flashcards = data.get("flashcards", [])
    url = data.get("url", "")

    lines = [
        f"# {title} - AKIRA Study Notes",
        f"Source: {url}",
        "=" * 60,
        "",
        "## Executive Summary",
        summary,
        "",
        "## Key Takeaways",
    ]
    for b in takeaways:
        lines.append(f"- {b}")

    if flashcards:
        lines.append("")
        lines.append("## Revision Flashcards")
        for card in flashcards:
            term = card.get("term", "Concept")
            definition = card.get("definition", "")
            lines.append(f"- **{term}**: {definition}")

    lines.append("")
    lines.append("-" * 60)
    lines.append("Generated by AKIRA (Accessible Knowledge & Information Retrieval Assistant)")

    content = "\n".join(lines)
    safe_filename = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")
    return Response(
        content,
        mimetype="text/markdown",
        headers={"Content-Disposition": f"attachment;filename=AKIRA_{safe_filename}_Notes.md"},
    )


@app.route("/api/health", methods=["GET"])
def health():
    """System health & diagnostic endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "AKIRA Assistant",
        "version": "1.0.0",
        "database": "sqlite3 (akira.db)",
    })


if __name__ == "__main__":
    # Run development server on port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)

