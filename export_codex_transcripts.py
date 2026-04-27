#!/usr/bin/env python3
"""Export Codex session JSONL files into one Markdown transcript.

Usage:
    python3 export_codex_transcripts.py ~/.codex/sessions/2026/04/27 \
        --output all_conversations.md
    python3 export_codex_transcripts.py ~/.codex/sessions/2026/04/27/session.jsonl \
        --output all_conversations.md
    python3 export_codex_transcripts.py ~/.codex/sessions \
        --cwd /path/to/project --output project_conversations.md
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


HIDDEN_MARKERS = (
    "<permissions instructions>",
    "<collaboration_mode>",
    "<skills_instructions>",
    "developer_instructions",
    "base_instructions",
    "encrypted_content",
    "session_meta",
    "turn_context",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Codex session JSONL files from a directory or file into one Markdown transcript.",
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Directory containing Codex .jsonl session files, or one .jsonl file. Directories are searched recursively.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("codex_conversations_transcript.md"),
        help="Markdown file to write. Defaults to codex_conversations_transcript.md.",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Only include sessions whose metadata cwd matches this directory.",
    )
    parser.add_argument(
        "--messages-only",
        action="store_true",
        help="Only export visible user and assistant messages, omitting tool calls and outputs.",
    )
    return parser.parse_args()


def contains_hidden_marker(text: str) -> bool:
    return any(marker in text for marker in HIDDEN_MARKERS)


def sanitize(text: str) -> str:
    if contains_hidden_marker(text):
        return "[omitted because this block contains internal session instructions or encrypted context]"
    return text.rstrip()


def fenced(text: str, info: str = "") -> str:
    text = sanitize(text)
    longest = 0
    current = 0
    for char in text:
        if char == "`":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    ticks = "`" * max(3, longest + 1)
    return f"{ticks}{info}\n{text}\n{ticks}"


def content_text(content: Any) -> str:
    if not isinstance(content, list):
        return ""

    chunks: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str):
            chunks.append(text)
    return "\n\n".join(chunks).rstrip()


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False)


def parse_json_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def load_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    records: list[tuple[int, dict[str, Any]]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                records.append((line_number, record))
    return records


def session_metadata(records: list[tuple[int, dict[str, Any]]]) -> dict[str, Any]:
    for _, record in records:
        if record.get("type") != "session_meta":
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        return {
            "id": payload.get("id"),
            "timestamp": payload.get("timestamp"),
            "cwd": payload.get("cwd"),
            "originator": payload.get("originator"),
            "cli_version": payload.get("cli_version"),
            "git": payload.get("git"),
        }
    return {}


def session_sort_key(path: Path) -> tuple[str, str]:
    records = load_jsonl(path)
    metadata = session_metadata(records)
    timestamp = metadata.get("timestamp")
    if isinstance(timestamp, str):
        return (timestamp, str(path))
    return ("", str(path))


def filter_by_cwd(session_files: list[Path], cwd: Path | None) -> list[Path]:
    if cwd is None:
        return session_files

    expected_cwd = str(cwd.expanduser().resolve())
    filtered = []
    for path in session_files:
        records = load_jsonl(path)
        metadata = session_metadata(records)
        if metadata.get("cwd") == expected_cwd:
            filtered.append(path)

    return filtered


def render_message(timestamp: str, payload: dict[str, Any]) -> list[str]:
    role = payload.get("role")
    if role == "developer":
        return []

    text = content_text(payload.get("content"))
    if not text or text.startswith("<environment_context>"):
        return []

    label = "User" if role == "user" else "Assistant"
    phase = payload.get("phase")
    if role == "assistant" and phase:
        label += f" ({phase})"

    return [
        f"### {timestamp} - {label}",
        "",
        sanitize(text),
        "",
    ]


def render_tool_call(timestamp: str, payload: dict[str, Any], call_names: dict[str, str]) -> list[str]:
    name = str(payload.get("name", "unknown"))
    call_id = str(payload.get("call_id", ""))
    if call_id:
        call_names[call_id] = name

    arguments = parse_json_string(payload.get("arguments"))
    body = pretty_json(arguments) if not isinstance(arguments, str) else arguments
    info = "json" if not isinstance(arguments, str) else "text"

    rendered = [f"### {timestamp} - Tool Call: {name}", ""]
    if call_id:
        rendered.extend([f"Call ID: `{call_id}`", ""])
    rendered.extend([fenced(body, info), ""])
    return rendered


def render_tool_output(timestamp: str, payload: dict[str, Any], call_names: dict[str, str]) -> list[str]:
    call_id = str(payload.get("call_id", ""))
    name = call_names.get(call_id, "unknown")

    rendered = [f"### {timestamp} - Tool Output: {name}", ""]
    if call_id:
        rendered.extend([f"Call ID: `{call_id}`", ""])
    rendered.extend([fenced(str(payload.get("output", "")), "text"), ""])
    return rendered


def render_custom_tool_call(timestamp: str, payload: dict[str, Any], call_names: dict[str, str]) -> list[str]:
    name = str(payload.get("name", "custom_tool"))
    call_id = str(payload.get("call_id", ""))
    if call_id:
        call_names[call_id] = name

    rendered = [f"### {timestamp} - Tool Call: {name}", ""]
    if call_id:
        rendered.extend([f"Call ID: `{call_id}`", ""])
    rendered.extend([fenced(str(payload.get("input", "")), "text"), ""])
    return rendered


def render_web_search(timestamp: str, payload: dict[str, Any]) -> list[str]:
    return [
        f"### {timestamp} - Web Search",
        "",
        fenced(pretty_json(payload.get("action")), "json"),
        "",
    ]


def render_session(path: Path, include_tools: bool) -> list[str]:
    records = load_jsonl(path)
    metadata = session_metadata(records)
    if not records:
        return []

    rendered: list[str] = [
        f"## Session: `{path}`",
        "",
    ]
    if metadata:
        rendered.extend([fenced(pretty_json(metadata), "json"), ""])

    call_names: dict[str, str] = {}
    for _, record in records:
        timestamp = str(record.get("timestamp", ""))
        record_type = record.get("type")
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        payload_type = payload.get("type")

        if record_type == "response_item" and payload_type == "message":
            rendered.extend(render_message(timestamp, payload))
            continue

        if not include_tools:
            continue

        if record_type == "response_item" and payload_type == "function_call":
            rendered.extend(render_tool_call(timestamp, payload, call_names))
            continue

        if record_type == "response_item" and payload_type == "function_call_output":
            rendered.extend(render_tool_output(timestamp, payload, call_names))
            continue

        if record_type == "response_item" and payload_type == "custom_tool_call":
            rendered.extend(render_custom_tool_call(timestamp, payload, call_names))
            continue

        if record_type == "response_item" and payload_type == "custom_tool_call_output":
            rendered.extend(render_tool_output(timestamp, payload, call_names))
            continue

        if record_type == "response_item" and payload_type == "web_search_call":
            rendered.extend(render_web_search(timestamp, payload))

    return rendered


def main() -> None:
    args = parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    cwd_filter = args.cwd.expanduser().resolve() if args.cwd is not None else None

    if source.is_file():
        session_files = [source]
        source_label = "Source file"
    elif source.is_dir():
        session_files = sorted(source.rglob("*.jsonl"), key=session_sort_key)
        source_label = "Source directory"
    else:
        raise SystemExit(f"Source does not exist: {source}")

    session_files = filter_by_cwd(session_files, cwd_filter)

    if not session_files:
        raise SystemExit(f"No .jsonl files found under: {source}")

    markdown: list[str] = [
        "# Codex Conversations Transcript",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"{source_label}: `{source}`",
        f"Sessions included: {len(session_files)}",
    ]
    if cwd_filter is not None:
        markdown.append(f"CWD filter: `{cwd_filter}`")
    markdown.extend(
        [
            "",
            "Internal system/developer instructions, environment context records, encrypted reasoning, token counters, and compaction payloads are omitted.",
            "",
        ]
    )

    include_tools = not args.messages_only
    for session_file in session_files:
        markdown.extend(render_session(session_file, include_tools=include_tools))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(markdown).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Sessions included: {len(session_files)}")


if __name__ == "__main__":
    main()
