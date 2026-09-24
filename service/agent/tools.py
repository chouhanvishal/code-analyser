"""Tool definitions and execution environment for the autonomous agent."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from service.sandbox import ExecutionResult, Sandbox


class AgentTools:
    def __init__(self, workspace_root: Path, sandbox: Sandbox, default_test_cmd: str | None = None):
        self.workspace_root = workspace_root.resolve()
        self.sandbox = sandbox
        self.default_test_cmd = default_test_cmd or "bash run_tests.sh"

    def _safe_path(self, rel_path: str) -> Path:
        """Resolve path and ensure it does not escape the workspace."""
        path = (self.workspace_root / rel_path).resolve()
        if not str(path).startswith(str(self.workspace_root)):
            raise ValueError(f"Access denied: path escapes workspace root: {rel_path}")
        return path

    def list_dir(self, path: str = ".") -> str:
        """List files and directories in relative path."""
        try:
            target = self._safe_path(path)
            if not target.exists():
                return f"Error: Directory '{path}' does not exist."
            if not target.is_dir():
                return f"Error: '{path}' is not a directory."

            items = []
            for item in sorted(target.iterdir()):
                rel = item.relative_to(self.workspace_root)
                prefix = "[DIR]" if item.is_dir() else "[FILE]"
                items.append(f"{prefix} {rel}")
            return "\n".join(items) if items else "(empty directory)"
        except Exception as e:
            return f"Error listing directory: {e}"

    def view_file(self, path: str, start_line: int = 1, end_line: int = 500) -> str:
        """Read content of a file with line numbers."""
        try:
            target = self._safe_path(path)
            if not target.exists():
                return f"Error: File '{path}' does not exist."
            if target.is_dir():
                return f"Error: '{path}' is a directory, not a file."

            content = target.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            total_lines = len(lines)

            start = max(1, start_line)
            end = min(total_lines, end_line)

            if start > total_lines:
                return f"File '{path}' has only {total_lines} lines (requested start {start_line})."

            output = []
            for idx in range(start - 1, end):
                output.append(f"{idx + 1:4d} | {lines[idx]}")

            header = f"=== File: {path} (Lines {start}-{end} of {total_lines}) ===\n"
            return header + "\n".join(output)
        except Exception as e:
            return f"Error viewing file: {e}"

    def write_file(self, path: str, content: str) -> str:
        """Write content to a file. Overwrites if file exists, creates parent directories if needed."""
        try:
            target = self._safe_path(path)
            # Check forbidden path prefixes for diff rules
            rel = str(target.relative_to(self.workspace_root))
            if rel.startswith((".git/", "acceptance/", "acceptance_tests/")):
                return f"Error: Writing to protected path '{rel}' is forbidden."

            target.parent.mkdir(parents=True, exist_ok=True)
            # Ensure LF line endings
            content_normalized = content.replace("\r\n", "\n")
            target.write_text(content_normalized, encoding="utf-8")
            return f"Successfully wrote {len(content_normalized.splitlines())} lines to '{path}'."
        except Exception as e:
            return f"Error writing file: {e}"

    def replace_lines(self, path: str, start_line: int, end_line: int, new_content: str) -> str:
        """Replace lines [start_line, end_line] in path with new_content (1-indexed, inclusive)."""
        try:
            target = self._safe_path(path)
            if not target.exists():
                return f"Error: File '{path}' does not exist."

            lines = target.read_text(encoding="utf-8").splitlines()
            total_lines = len(lines)

            if start_line < 1 or end_line > total_lines or start_line > end_line:
                return f"Error: Invalid line range [{start_line}, {end_line}] for file with {total_lines} lines."

            new_lines = new_content.replace("\r\n", "\n").splitlines()
            # Replace slice (0-indexed)
            updated_lines = lines[:start_line - 1] + new_lines + lines[end_line:]
            result_content = "\n".join(updated_lines) + ("\n" if lines and lines[-1] == "" else "\n")

            target.write_text(result_content, encoding="utf-8")
            return f"Successfully updated '{path}' (lines {start_line}-{end_line} replaced)."
        except Exception as e:
            return f"Error replacing lines: {e}"

    def search_code(self, query: str, path: str = ".") -> str:
        """Search for literal string or regex pattern in workspace files."""
        try:
            target = self._safe_path(path)
            results = []
            pattern = re.compile(query, re.IGNORECASE)

            search_files = [target] if target.is_file() else list(target.rglob("*"))
            for file_path in search_files:
                if file_path.is_file() and not file_path.name.startswith(".") and ".git" not in file_path.parts:
                    try:
                        text = file_path.read_text(encoding="utf-8", errors="ignore")
                        for line_no, line in enumerate(text.splitlines(), start=1):
                            if pattern.search(line):
                                rel = file_path.relative_to(self.workspace_root)
                                results.append(f"{rel}:{line_no}: {line.strip()[:150]}")
                                if len(results) >= 50:
                                    results.append("... (more matches truncated)")
                                    break
                    except Exception:
                        continue
                if len(results) >= 50:
                    break

            return "\n".join(results) if results else f"No matches found for '{query}'."
        except Exception as e:
            return f"Error searching code: {e}"

    def run_tests(self, command: str | None = None) -> str:
        """Run the test command in the offline sandbox environment."""
        cmd = command or self.default_test_cmd
        res: ExecutionResult = self.sandbox.run(cmd, self.workspace_root, timeout_s=45.0)
        output = res.output
        if len(output) > 4000:
            output = output[:1500] + "\n\n... [output truncated] ...\n\n" + output[-2500:]

        status = "PASSED" if res.success else f"FAILED (exit code {res.exit_code})"
        return f"=== Test Command: `{cmd}` ===\nStatus: {status}\nDuration: {res.duration_s}s\n\nOutput:\n{output}"

    def execute_tool(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        """Execute a tool by name and return (result_text, is_error)."""
        try:
            if name == "list_dir":
                return self.list_dir(args.get("path", ".")), False
            elif name == "view_file":
                return self.view_file(
                    args["path"],
                    int(args.get("start_line", 1)),
                    int(args.get("end_line", 500))
                ), False
            elif name == "write_file":
                return self.write_file(args["path"], args["content"]), False
            elif name == "replace_lines":
                return self.replace_lines(
                    args["path"],
                    int(args["start_line"]),
                    int(args["end_line"]),
                    args["new_content"]
                ), False
            elif name == "search_code":
                return self.search_code(args["query"], args.get("path", ".")), False
            elif name == "run_tests":
                res = self.run_tests(args.get("command"))
                is_err = "FAILED" in res or "Error" in res
                return res, is_err
            else:
                return f"Error: Unknown tool '{name}'", True
        except Exception as e:
            return f"Error executing tool '{name}': {e}", True


# OpenAI / Standard JSON Schema Tool Specifications
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories in a given relative directory path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory path (default: '.')"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "view_file",
            "description": "Read file contents with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file"},
                    "start_line": {"type": "integer", "description": "Start line number (1-indexed)", "default": 1},
                    "end_line": {"type": "integer", "description": "End line number (inclusive)", "default": 500}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with given text content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file"},
                    "content": {"type": "string", "description": "Entire content of the file"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_lines",
            "description": "Replace a line range in an existing file with new content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file"},
                    "start_line": {"type": "integer", "description": "Starting line number (1-indexed)"},
                    "end_line": {"type": "integer", "description": "Ending line number (1-indexed, inclusive)"},
                    "new_content": {"type": "string", "description": "New replacement content"}
                },
                "required": ["path", "start_line", "end_line", "new_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for text or regex patterns in repository files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "String or regex pattern to search for"},
                    "path": {"type": "string", "description": "Relative directory or file to search within", "default": "."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Execute tests in the offline Docker sandbox. Runs default test command (e.g. bash run_tests.sh) or custom command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Optional specific test or build command to run"}
                }
            }
        }
    }
]
