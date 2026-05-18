import re
import threading
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template, request, send_from_directory

app = Flask(__name__)
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

_tasks: dict[str, dict] = {}

ATOM_NS = "http://www.w3.org/2005/Atom"

# ---------------------------------------------------------------------------
# arXiv ID / title parsing
# ---------------------------------------------------------------------------

_NEW_ID = re.compile(r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b")
_OLD_ID = re.compile(r"\b([a-zA-Z.-]+/\d{7})\b")
_URL = re.compile(r"arxiv\.org/(?:abs|pdf)/([^\s?#/]+(?:/\d{7})?)", re.I)
_PREFIX = re.compile(r"arXiv:\s*(\S+)", re.I)


def extract_arxiv_id(text: str) -> str | None:
    for pattern in (_URL, _PREFIX, _NEW_ID, _OLD_ID):
        m = pattern.search(text.strip())
        if m:
            return m.group(1).strip("/")
    return None


# ---------------------------------------------------------------------------
# arXiv API helpers
# ---------------------------------------------------------------------------

_API = "https://export.arxiv.org/api/query"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; arXiv-scraper/1.0)"}


def _parse_feed(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    entries = []
    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        id_el = entry.find(f"{{{ATOM_NS}}}id")
        if id_el is None or id_el.text is None:
            continue
        arxiv_id = id_el.text.split("/abs/")[-1]
        title_el = entry.find(f"{{{ATOM_NS}}}title")
        title = " ".join((title_el.text or "").split()) if title_el is not None else ""
        authors = [
            name.text
            for auth in entry.findall(f"{{{ATOM_NS}}}author")
            if (name := auth.find(f"{{{ATOM_NS}}}name")) is not None and name.text
        ]
        summary_el = entry.find(f"{{{ATOM_NS}}}summary")
        summary = " ".join((summary_el.text or "").split()) if summary_el is not None else ""
        pub_el = entry.find(f"{{{ATOM_NS}}}published")
        published = (pub_el.text or "")[:10] if pub_el is not None else ""
        entries.append(
            {
                "id": arxiv_id,
                "title": title,
                "authors": authors[:5],
                "summary": summary[:300],
                "published": published,
            }
        )
    return entries


def fetch_by_id(arxiv_id: str) -> list[dict]:
    # Build URL directly — using params= would percent-encode the slash in old-style
    # IDs like cond-mat/0110438, which causes the arXiv API to time out.
    r = requests.get(f"{_API}?id_list={arxiv_id}", headers=_HEADERS, timeout=15)
    r.raise_for_status()
    return _parse_feed(r.text)


def fetch_by_title(title: str) -> list[dict]:
    q = f'ti:"{title}"'
    r = requests.get(_API, params={"search_query": q, "max_results": 1}, headers=_HEADERS, timeout=15)
    r.raise_for_status()
    return _parse_feed(r.text)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def api_search():
    raw: list[str] = request.json.get("items", [])
    results = []
    for line in raw:
        line = line.strip()
        if not line:
            continue
        arxiv_id = extract_arxiv_id(line)
        article = None
        try:
            if arxiv_id:
                hits = fetch_by_id(arxiv_id)
                if hits:
                    article = hits[0]
            else:
                hits = fetch_by_title(line)
                if hits:
                    article = hits[0]
        except Exception as exc:
            results.append({"query": line, "status": "error", "article": None, "error": str(exc)})
            continue

        if article:
            results.append({"query": line, "status": "found", "article": article})
        else:
            results.append({"query": line, "status": "not_found", "article": None})

    return jsonify(results)


@app.route("/api/download", methods=["POST"])
def api_download():
    ids: list[str] = request.json.get("ids", [])
    task_id = str(uuid.uuid4())
    _tasks[task_id] = {"status": "running", "total": len(ids), "done": 0, "files": [], "errors": []}

    def worker():
        for arxiv_id in ids:
            safe = arxiv_id.replace("/", "_")
            dest = DOWNLOADS_DIR / f"{safe}.pdf"
            if dest.exists():
                _tasks[task_id]["files"].append({"id": arxiv_id, "file": dest.name})
            else:
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
                try:
                    resp = requests.get(pdf_url, headers=_HEADERS, timeout=60, stream=True)
                    resp.raise_for_status()
                    with open(dest, "wb") as fh:
                        for chunk in resp.iter_content(chunk_size=16384):
                            fh.write(chunk)
                    _tasks[task_id]["files"].append({"id": arxiv_id, "file": dest.name})
                except Exception as exc:
                    _tasks[task_id]["errors"].append({"id": arxiv_id, "error": str(exc)})
                    if dest.exists():
                        dest.unlink(missing_ok=True)
            _tasks[task_id]["done"] += 1
        _tasks[task_id]["status"] = "complete"

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"task_id": task_id})


@app.route("/api/status/<task_id>")
def api_status(task_id: str):
    task = _tasks.get(task_id)
    if task is None:
        return jsonify({"error": "unknown task"}), 404
    return jsonify(task)


@app.route("/downloads/<path:filename>")
def serve_download(filename: str):
    return send_from_directory(DOWNLOADS_DIR.resolve(), filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
