#!/usr/bin/env python3
"""
Export Cursor agent transcript(s) to a single markdown file suitable for
pasting into Claude (Claude Code, API, or chat) for context.

Run from project root: python3 scripts/export_chat_history_for_claude.py

Reads from all known Cursor project transcript folders (folder + workspace)
so history is available after reopen or Cursor update.
Optional: set CHAT_HISTORY_FOR_CLAUDE_OUTPUT to write to a specific file path.
"""
from pathlib import Path
import json
import os
import sys

# Project root = parent of scripts/ (or use cwd if script run from project that has scripts/)
_SCRIPT_DIR = Path(__file__).resolve().parents[0]
_PROJECT_ROOT = _SCRIPT_DIR.parents[0]
if (Path.cwd() / "scripts" / "export_chat_history_for_claude.py").exists():
    _PROJECT_ROOT = Path.cwd()
OUTPUT_PATH = Path(os.environ.get("CHAT_HISTORY_FOR_CLAUDE_OUTPUT", str(_PROJECT_ROOT / "CHAT_HISTORY_FOR_CLAUDE.md")))

# All known Cursor project transcript roots for adam-platform
_TRANSCRIPT_ROOTS = [
    Path.home() / ".cursor" / "projects" / "Users-chrisnocera-Sites-adam-platform" / "agent-transcripts",
    Path.home() / ".cursor" / "projects" / "Users-chrisnocera-Sites-adam-platform-adam-cursor-project-code-workspace" / "agent-transcripts",
]
if os.environ.get("CURSOR_AGENT_TRANSCRIPTS"):
    _TRANSCRIPT_ROOTS.insert(0, Path(os.environ["CURSOR_AGENT_TRANSCRIPTS"]))


def extract_text(content: list) -> str:
    """Extract plain text from message content (may be list of text/other blocks)."""
    parts = []
    for block in content or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif isinstance(block, str):
            parts.append(block)
    return "\n".join(parts).strip()


def load_transcript(path: Path) -> list[tuple[str, str]]:
    """Load a single .jsonl transcript into (role, text) pairs. Skip subagent transcripts."""
    turns = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    role = obj.get("role") or obj.get("type") or "unknown"
                    msg = obj.get("message") or obj
                    content = msg.get("content") if isinstance(msg, dict) else []
                    if isinstance(content, str):
                        text = content
                    else:
                        text = extract_text(content) if isinstance(content, list) else str(msg)
                    if text:
                        turns.append((role, text))
                except json.JSONDecodeError:
                    continue
    except OSError as e:
        print(f"Warning: could not read {path}: {e}", file=sys.stderr)
    return turns


def main() -> None:
    seen: set[str] = set()
    collected: list[tuple[Path, list[tuple[str, str]]]] = []
    for root in _TRANSCRIPT_ROOTS:
        if not root.exists():
            continue
        for folder in sorted(root.iterdir()):
            if not folder.is_dir() or "subagents" in str(folder):
                continue
            session_id = folder.name
            jsonl_file = folder / f"{session_id}.jsonl"
            if not jsonl_file.exists() or session_id in seen:
                continue
            seen.add(session_id)
            turns = load_transcript(jsonl_file)
            if turns:
                collected.append((jsonl_file, turns))

    if not collected and not any(r.exists() for r in _TRANSCRIPT_ROOTS):
        print("No agent-transcripts directory found.", file=sys.stderr)
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(
            "# Chat history for Claude\n\nNo Cursor agent transcripts found. "
            "Run this script after using Cursor agent chats. Transcripts are under ~/.cursor/projects/.../agent-transcripts/.\n",
            encoding="utf-8",
        )
        return

    if not collected:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(
            "# Chat history for Claude\n\nNo transcript turns found in agent-transcripts.\n",
            encoding="utf-8",
        )
        print("No transcript content found.", file=sys.stderr)
        return

    collected.sort(key=lambda x: x[0].parent.name)
    lines = [
        "# Chat history for Claude",
        "",
        "Exported from Cursor agent transcripts. Use for context when continuing work.",
        "Refresh: run `python3 scripts/export_chat_history_for_claude.py` from project root.",
        "",
        "---",
        "",
    ]
    for path, turns in collected:
        lines.append(f"## Session: `{path.parent.name}`")
        lines.append("")
        for role, text in turns:
            label = "User" if role == "user" else "Assistant"
            lines.append(f"### {label}")
            lines.append("")
            lines.append(text)
            lines.append("")
        lines.append("---")
        lines.append("")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} ({len(collected)} session(s))")


if __name__ == "__main__":
    main()
