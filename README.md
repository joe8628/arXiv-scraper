# arXiv-scraper

A local web app for resolving and batch-downloading arXiv papers as PDFs.

## Features

- Accepts multiple input formats: arXiv IDs, full URLs, `arXiv:` prefixes, old-style IDs, or plain paper titles
- Verifies each paper against the arXiv API before downloading
- Batch-downloads selected PDFs with a live progress bar
- Serves downloaded files directly from the browser

## Requirements

- Python 3.10+

## Installation & Running

```bash
# Clone the repo
git clone https://github.com/your-username/arXiv-scraper.git
cd arXiv-scraper

# Start the app (creates a virtualenv and installs deps automatically)
./run.sh
```

Then open `http://localhost:5000` in your browser.

To run manually without the script:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Usage

### 1. Enter papers

Paste one entry per line in the text area. Supported formats:

| Format | Example |
|--------|---------|
| arXiv ID | `2401.12345` |
| Versioned ID | `2401.12345v2` |
| `arXiv:` prefix | `arXiv:2310.06825` |
| Full URL | `https://arxiv.org/abs/1706.03762` |
| Old-style ID | `cs.AI/0607046` |
| Paper title | `Attention Is All You Need` |

### 2. Search & Verify

Click **Search & Verify**. The app queries the arXiv API and shows each paper's title, authors, year, and a found/not-found badge. Click **Abstract ▾** on any result to preview the abstract.

### 3. Select papers

Check individual papers or use **Select all found** to select everything that was resolved. The selected count updates in real time.

### 4. Download

Click **Download Selected PDFs**. A progress bar tracks each download. When complete, clickable download links appear for every PDF. Files are saved to the `downloads/` folder next to `app.py`. Re-downloading a paper that already exists locally is instant (cached).

## Project structure

```
arXiv-scraper/
├── app.py              # Flask backend
├── requirements.txt    # Python dependencies
├── run.sh              # One-shot launcher
├── templates/
│   └── index.html      # Single-page frontend
└── downloads/          # PDF output directory (created on first run)
```
