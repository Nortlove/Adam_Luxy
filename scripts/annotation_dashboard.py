#!/usr/bin/env python3
"""
Local annotation dashboard for Claude Max workflow.

Serves a web UI at http://localhost:8420 that streamlines the
copy-paste annotation loop: shows batch content, accepts JSON
responses, validates, saves, and tracks progress.

No pip dependencies -- uses only Python stdlib.

Usage:
    python scripts/annotation_dashboard.py
    python scripts/annotation_dashboard.py --dataset all_beauty --port 8420
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("dashboard")

BASE_DIR = Path(__file__).parent.parent
BATCHES_DIR = BASE_DIR / "data" / "annotation_batches"
RESULTS_DIR = BASE_DIR / "data" / "annotation_results"


def get_progress(dataset: str) -> dict:
    """Scan result files to compute progress."""
    product_batches_dir = BATCHES_DIR / dataset / "products"
    review_batches_dir = BATCHES_DIR / dataset / "reviews"
    product_results_dir = RESULTS_DIR / dataset / "products"
    review_results_dir = RESULTS_DIR / dataset / "reviews"

    product_total = len(list(product_batches_dir.glob("batch_*.txt"))) if product_batches_dir.exists() else 0
    review_total = len(list(review_batches_dir.glob("batch_*.txt"))) if review_batches_dir.exists() else 0

    product_done = set()
    if product_results_dir.exists():
        for f in product_results_dir.glob("batch_*_results.json"):
            m = re.search(r"batch_(\d+)_results", f.name)
            if m:
                product_done.add(int(m.group(1)))

    review_done = set()
    if review_results_dir.exists():
        for f in review_results_dir.glob("batch_*_results.json"):
            m = re.search(r"batch_(\d+)_results", f.name)
            if m:
                review_done.add(int(m.group(1)))

    def find_next(done: set, total: int) -> int | None:
        for i in range(1, total + 1):
            if i not in done:
                return i
        return None

    return {
        "dataset": dataset,
        "products": {
            "total": product_total,
            "done": len(product_done),
            "done_ids": sorted(product_done),
            "next": find_next(product_done, product_total),
        },
        "reviews": {
            "total": review_total,
            "done": len(review_done),
            "done_ids": sorted(review_done),
            "next": find_next(review_done, review_total),
        },
    }


def read_batch(dataset: str, batch_type: str, batch_num: int) -> str | None:
    path = BATCHES_DIR / dataset / batch_type / f"batch_{batch_num:04d}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def save_result(dataset: str, batch_type: str, batch_num: int, data: str) -> dict:
    """Validate and save a JSON result."""
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"Invalid JSON: {e}"}

    if isinstance(parsed, dict) and not isinstance(parsed, list):
        parsed = [parsed]

    if not isinstance(parsed, list):
        return {"ok": False, "error": "Expected a JSON array or object"}

    if batch_type == "products":
        id_field = "asin"
    else:
        id_field = "review_id"

    missing_ids = [i for i, item in enumerate(parsed) if not item.get(id_field)]
    if missing_ids:
        return {
            "ok": False,
            "error": f"Items at indices {missing_ids[:5]} missing '{id_field}' field",
        }

    out_dir = RESULTS_DIR / dataset / batch_type
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"batch_{batch_num:04d}_results.json"
    out_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

    return {"ok": True, "items": len(parsed), "path": str(out_path)}


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ADAM Annotation Dashboard</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #0f1117;
  --surface: #1a1d27;
  --surface2: #232734;
  --border: #2e3347;
  --text: #e4e6ef;
  --text-dim: #8b8fa3;
  --accent: #6c63ff;
  --accent-glow: rgba(108, 99, 255, 0.3);
  --green: #22c55e;
  --green-dim: rgba(34, 197, 94, 0.15);
  --red: #ef4444;
  --red-dim: rgba(239, 68, 68, 0.15);
  --orange: #f59e0b;
  --radius: 10px;
  --font: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.5;
  min-height: 100vh;
}

.header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.header h1 {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.3px;
}

.header .dataset-badge {
  background: var(--accent);
  color: white;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 20px;
  font-weight: 600;
}

.header .stats {
  margin-left: auto;
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: var(--text-dim);
}

.header .stats .num { color: var(--accent); font-weight: 700; font-family: var(--font); }

.tabs {
  display: flex;
  gap: 2px;
  padding: 12px 24px 0;
  background: var(--surface);
}

.tab {
  padding: 10px 24px;
  cursor: pointer;
  border-radius: 8px 8px 0 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-dim);
  background: transparent;
  border: 1px solid transparent;
  border-bottom: none;
  transition: all 0.15s;
  user-select: none;
}

.tab:hover { color: var(--text); background: var(--surface2); }
.tab.active {
  color: var(--text);
  background: var(--bg);
  border-color: var(--border);
}

.progress-section {
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.progress-bar-wrap {
  flex: 1;
  height: 8px;
  background: var(--surface2);
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #a78bfa);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.progress-label {
  font-size: 13px;
  color: var(--text-dim);
  font-family: var(--font);
  min-width: 100px;
  text-align: right;
}

.main {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 16px 24px;
  height: calc(100vh - 200px);
  min-height: 500px;
}

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.panel-header h2 {
  font-size: 14px;
  font-weight: 600;
}

.panel-header .badge {
  font-size: 12px;
  font-family: var(--font);
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--surface2);
  color: var(--text-dim);
}

.panel-header .btn {
  margin-left: auto;
}

.btn {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-accent {
  background: var(--accent);
  color: white;
}
.btn-accent:hover { background: #5b52e0; }
.btn-accent:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-green {
  background: var(--green);
  color: white;
}
.btn-green:hover { background: #16a34a; }
.btn-green:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-outline {
  background: transparent;
  color: var(--text-dim);
  border: 1px solid var(--border);
}
.btn-outline:hover { color: var(--text); border-color: var(--text-dim); }

textarea {
  flex: 1;
  width: 100%;
  resize: none;
  background: var(--bg);
  color: var(--text);
  border: none;
  padding: 12px 16px;
  font-family: var(--font);
  font-size: 12px;
  line-height: 1.6;
  outline: none;
}

textarea::placeholder { color: var(--text-dim); opacity: 0.5; }

.status-bar {
  padding: 8px 16px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.ok { background: var(--green); box-shadow: 0 0 6px var(--green); }
.status-dot.err { background: var(--red); box-shadow: 0 0 6px var(--red); }
.status-dot.neutral { background: var(--text-dim); }

.status-text { color: var(--text-dim); }

.bottom-bar {
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
}

.bottom-bar .batch-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: auto;
}

.batch-nav input {
  width: 70px;
  background: var(--surface2);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 5px 8px;
  border-radius: 4px;
  font-family: var(--font);
  font-size: 13px;
  text-align: center;
}

.batch-nav label {
  font-size: 13px;
  color: var(--text-dim);
}

.kbd {
  display: inline-block;
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--surface2);
  border: 1px solid var(--border);
  font-family: var(--font);
  font-size: 11px;
  color: var(--text-dim);
}

.toast {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%) translateY(80px);
  background: var(--surface);
  border: 1px solid var(--green);
  color: var(--text);
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  opacity: 0;
  transition: all 0.3s ease;
  pointer-events: none;
  z-index: 100;
}

.toast.show {
  transform: translateX(-50%) translateY(0);
  opacity: 1;
}

.done-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  font-size: 16px;
  color: var(--green);
  font-weight: 600;
}
</style>
</head>
<body>

<div class="header">
  <h1>ADAM Annotation Dashboard</h1>
  <span class="dataset-badge" id="datasetBadge">--</span>
  <div class="stats">
    <span>Products: <span class="num" id="statProducts">--</span></span>
    <span>Reviews: <span class="num" id="statReviews">--</span></span>
    <span>Total items: <span class="num" id="statItems">--</span></span>
  </div>
</div>

<div class="tabs">
  <div class="tab active" data-tab="products" onclick="switchTab('products')">Products</div>
  <div class="tab" data-tab="reviews" onclick="switchTab('reviews')">Reviews</div>
</div>

<div class="progress-section">
  <div class="progress-bar-wrap">
    <div class="progress-bar-fill" id="progressFill" style="width: 0%"></div>
  </div>
  <div class="progress-label" id="progressLabel">0 / 0</div>
</div>

<div class="main">
  <div class="panel">
    <div class="panel-header">
      <h2>Batch Content</h2>
      <span class="badge" id="batchBadge">batch_0001</span>
      <button class="btn btn-accent" id="copyBtn" onclick="copyBatch()">Copy to Clipboard</button>
    </div>
    <textarea id="batchContent" readonly placeholder="Loading batch..."></textarea>
    <div class="status-bar">
      <div class="status-dot neutral" id="batchDot"></div>
      <span class="status-text" id="batchStatus">Ready</span>
    </div>
  </div>

  <div class="panel">
    <div class="panel-header">
      <h2>Paste Claude's Response</h2>
      <span class="badge" id="validBadge">--</span>
      <button class="btn btn-green" id="saveBtn" onclick="saveAndNext()" disabled>Save &amp; Next</button>
    </div>
    <textarea id="responseInput" placeholder="Paste the JSON response from Claude here..."></textarea>
    <div class="status-bar">
      <div class="status-dot neutral" id="responseDot"></div>
      <span class="status-text" id="responseStatus">Waiting for JSON...</span>
    </div>
  </div>
</div>

<div class="bottom-bar">
  <div class="batch-nav">
    <label>Go to batch:</label>
    <input type="number" id="batchInput" min="1" value="1" onchange="goToBatch()">
    <button class="btn btn-outline" onclick="goToBatch()">Go</button>
    <span style="margin-left: 12px; font-size: 12px; color: var(--text-dim)">
      <span class="kbd">Ctrl</span>+<span class="kbd">Enter</span> Save &amp; Next
    </span>
  </div>
  <button class="btn btn-outline" onclick="skipBatch()">Skip to Next Incomplete</button>
</div>

<div class="toast" id="toast">Saved!</div>

<script>
const API = '';
let state = { tab: 'products', batchNum: 1, progress: null };

async function fetchJSON(url, opts) {
  const r = await fetch(API + url, opts);
  return r.json();
}

async function loadProgress() {
  state.progress = await fetchJSON('/api/status');
  render();
}

function render() {
  const p = state.progress;
  if (!p) return;
  const d = p[state.tab];

  document.getElementById('datasetBadge').textContent = p.dataset;
  document.getElementById('statProducts').textContent = `${p.products.done}/${p.products.total}`;
  document.getElementById('statReviews').textContent = `${p.reviews.done}/${p.reviews.total}`;
  const totalDone = p.products.done * 25 + p.reviews.done * 25;
  const totalAll = p.products.total * 25 + p.reviews.total * 25;
  document.getElementById('statItems').textContent = `~${totalDone.toLocaleString()} / ${totalAll.toLocaleString()}`;

  const pct = d.total > 0 ? (d.done / d.total * 100) : 0;
  document.getElementById('progressFill').style.width = pct + '%';
  document.getElementById('progressLabel').textContent = `${d.done} / ${d.total} batches`;

  document.querySelectorAll('.tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === state.tab);
    const info = p[t.dataset.tab];
    const done = info.done_ids && info.done_ids.includes(state.batchNum);
    t.textContent = `${t.dataset.tab === 'products' ? 'Products' : 'Reviews'}${info.done === info.total ? ' (done)' : ''}`;
  });

  document.getElementById('batchBadge').textContent = `batch_${String(state.batchNum).padStart(4, '0')}`;
  document.getElementById('batchInput').value = state.batchNum;
  document.getElementById('batchInput').max = d.total;

  const isDone = d.done_ids && d.done_ids.includes(state.batchNum);
  const dot = document.getElementById('batchDot');
  const bst = document.getElementById('batchStatus');
  if (isDone) {
    dot.className = 'status-dot ok';
    bst.textContent = 'Already completed';
  } else {
    dot.className = 'status-dot neutral';
    bst.textContent = 'Ready to annotate';
  }
}

async function loadBatch() {
  const content = document.getElementById('batchContent');
  content.value = 'Loading...';
  try {
    const data = await fetchJSON(`/api/batch/${state.tab}/${state.batchNum}`);
    if (data.content) {
      content.value = data.content;
    } else {
      content.value = data.error || 'Batch not found';
    }
  } catch (e) {
    content.value = 'Error loading batch: ' + e.message;
  }
  document.getElementById('responseInput').value = '';
  resetValidation();
  render();
}

function switchTab(tab) {
  state.tab = tab;
  const p = state.progress;
  if (p) {
    const next = p[tab].next;
    state.batchNum = next || 1;
  }
  loadBatch();
}

function goToBatch() {
  const v = parseInt(document.getElementById('batchInput').value);
  if (v > 0) {
    state.batchNum = v;
    loadBatch();
  }
}

function skipBatch() {
  const p = state.progress;
  if (p) {
    const next = p[state.tab].next;
    if (next) {
      state.batchNum = next;
      loadBatch();
    } else {
      showToast('All batches complete!');
    }
  }
}

async function copyBatch() {
  const content = document.getElementById('batchContent').value;
  try {
    await navigator.clipboard.writeText(content);
    const btn = document.getElementById('copyBtn');
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy to Clipboard'; }, 1500);
  } catch (e) {
    showToast('Copy failed - use Ctrl+A, Ctrl+C in the text area');
  }
}

function resetValidation() {
  document.getElementById('responseDot').className = 'status-dot neutral';
  document.getElementById('responseStatus').textContent = 'Waiting for JSON...';
  document.getElementById('validBadge').textContent = '--';
  document.getElementById('saveBtn').disabled = true;
}

document.getElementById('responseInput').addEventListener('input', function() {
  const text = this.value.trim();
  if (!text) { resetValidation(); return; }

  const dot = document.getElementById('responseDot');
  const st = document.getElementById('responseStatus');
  const badge = document.getElementById('validBadge');
  const saveBtn = document.getElementById('saveBtn');

  try {
    let parsed = JSON.parse(text);
    if (!Array.isArray(parsed)) parsed = [parsed];
    const idField = state.tab === 'products' ? 'asin' : 'review_id';
    const withId = parsed.filter(item => item[idField]);

    if (withId.length === 0) {
      dot.className = 'status-dot err';
      st.textContent = `No items with '${idField}' field found`;
      badge.textContent = '0 items';
      saveBtn.disabled = true;
    } else {
      dot.className = 'status-dot ok';
      st.textContent = `Valid: ${withId.length} items with '${idField}'`;
      badge.textContent = `${withId.length} items`;
      saveBtn.disabled = false;
    }
  } catch (e) {
    dot.className = 'status-dot err';
    st.textContent = 'Invalid JSON: ' + e.message.slice(0, 80);
    badge.textContent = 'invalid';
    saveBtn.disabled = true;
  }
});

async function saveAndNext() {
  const text = document.getElementById('responseInput').value.trim();
  if (!text) return;

  const saveBtn = document.getElementById('saveBtn');
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving...';

  try {
    const result = await fetchJSON(`/api/save/${state.tab}/${state.batchNum}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data: text }),
    });

    if (result.ok) {
      showToast(`Saved ${result.items} items to ${result.path.split('/').pop()}`);
      await loadProgress();
      const next = state.progress[state.tab].next;
      if (next) {
        state.batchNum = next;
        loadBatch();
      } else {
        showToast('All ' + state.tab + ' batches complete!');
        document.getElementById('responseInput').value = '';
        resetValidation();
        render();
      }
    } else {
      showToast('Error: ' + result.error);
    }
  } catch (e) {
    showToast('Save failed: ' + e.message);
  }

  saveBtn.textContent = 'Save & Next';
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}

document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    const saveBtn = document.getElementById('saveBtn');
    if (!saveBtn.disabled) saveAndNext();
  }
});

loadProgress().then(() => {
  const p = state.progress;
  if (p) {
    const next = p[state.tab].next;
    state.batchNum = next || 1;
  }
  loadBatch();
});
</script>
</body>
</html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    dataset: str = "all_beauty"

    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")

    def _json_response(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html_response(self, html: str, status: int = 200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "" or path == "/":
            self._html_response(DASHBOARD_HTML)
            return

        if path == "/api/status":
            self._json_response(get_progress(self.dataset))
            return

        m = re.match(r"/api/batch/(products|reviews)/(\d+)", path)
        if m:
            batch_type, batch_num = m.group(1), int(m.group(2))
            content = read_batch(self.dataset, batch_type, batch_num)
            if content:
                self._json_response({"content": content, "batch": batch_num, "type": batch_type})
            else:
                self._json_response({"error": "Batch not found"}, 404)
            return

        self._json_response({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        m = re.match(r"/api/save/(products|reviews)/(\d+)", path)
        if m:
            batch_type, batch_num = m.group(1), int(m.group(2))
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                data_str = payload.get("data", "")
            except json.JSONDecodeError:
                data_str = body

            result = save_result(self.dataset, batch_type, batch_num, data_str)
            self._json_response(result)
            if result["ok"]:
                logger.info(f"Saved {result['items']} items -> {result['path']}")
            return

        self._json_response({"error": "Not found"}, 404)


def main():
    parser = argparse.ArgumentParser(description="ADAM Annotation Dashboard")
    parser.add_argument("--dataset", default="all_beauty", choices=["all_beauty", "bpc", "sephora"])
    parser.add_argument("--port", type=int, default=8420)
    args = parser.parse_args()

    DashboardHandler.dataset = args.dataset

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / args.dataset / "products").mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / args.dataset / "reviews").mkdir(parents=True, exist_ok=True)

    server = HTTPServer(("0.0.0.0", args.port), DashboardHandler)
    progress = get_progress(args.dataset)

    print(f"\n{'='*60}")
    print(f"  ADAM Annotation Dashboard")
    print(f"  Dataset: {args.dataset}")
    print(f"  Products: {progress['products']['done']}/{progress['products']['total']} batches done")
    print(f"  Reviews:  {progress['reviews']['done']}/{progress['reviews']['total']} batches done")
    print(f"{'='*60}")
    print(f"\n  Open in browser: http://localhost:{args.port}")
    print(f"\n  Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
