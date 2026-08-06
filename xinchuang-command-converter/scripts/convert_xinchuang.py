#!/usr/bin/env python3
"""Offline static converter for CentOS/x86 shell and Docker scripts.

Security contract
-----------------
This tool performs static text parsing and string replacement only. User-supplied
shell scripts are plain text: they are never executed, evaluated, sourced, or
passed to a subprocess. Comment lines are skipped, and audit output masks
suspected passwords and keys.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent / "rules.json"

TARGET_ENV_MAP = {
    "银河麒麟ARM": {"os": "kylin", "arch": "arm64", "label": "银河麒麟 ARM"},
    "统信UOS ARM": {"os": "uos", "arch": "arm64", "label": "统信 UOS ARM"},
    "欧拉OS ARM": {"os": "euler", "arch": "arm64", "label": "欧拉 OS ARM"},
}

_DEFAULT_NOTICE = "转换完成脚本务必人工复测后上生产环境。"

_PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)
_URL_CREDENTIALS = re.compile(r"(\w+://[^/\s:@]+:)[^@\s/]+@")
_SENSITIVE_ASSIGN = re.compile(
    r"(?i)(\b(?:password|passwd|secret|token|api[_-]?key|private[_-]?key|auth[_-]?token)"
    r"\s*[=:]\s*)[^\s;|&]+"
)
_SENSITIVE_FLAG = re.compile(
    r"(?i)(--(?:password|passwd|secret|token|api[_-]?key|private[_-]?key|auth[_-]?token)"
    r"(?:\s+|=))[^\s]+"
)
_DOCKER_PLATFORM_PATTERN = re.compile(r"\bdocker\s+(run|create|build)\b")


def mask_sensitive(text: str) -> str:
    """Mask suspected credentials so audit logs never echo real secrets."""
    masked = _PRIVATE_KEY_BLOCK.sub("[MASKED_PRIVATE_KEY]", text)
    masked = _URL_CREDENTIALS.sub(r"\1******@", masked)
    masked = _SENSITIVE_ASSIGN.sub(r"\1******", masked)
    masked = _SENSITIVE_FLAG.sub(r"\1******", masked)
    return masked


def split_inline_comment(line: str) -> tuple[str, str | None]:
    """Split an unquoted ``#`` that starts a comment from executable code."""
    in_single = False
    in_double = False
    escaped = False
    for i, ch in enumerate(line):
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_double:
            escaped = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            continue
        if ch == "#" and not in_single and not in_double:
            if i == 0 or line[i - 1].isspace() or line[i - 1] in ";|&(":
                return line[:i], line[i:]
    return line, None


def load_rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def compile_rule_group(rules: dict, group: str) -> list[dict]:
    return [
        {
            "pattern": re.compile(item["pattern"]),
            "replacement": item["replacement"],
            "description": item.get("description", group),
            "note": item.get("note"),
        }
        for item in rules.get(group, [])
    ]


def compile_rules(rules: dict) -> dict:
    return {
        "pkg_manager": compile_rule_group(rules, "package_manager"),
        "commands": compile_rule_group(rules, "commands"),
        "pkg_names": compile_rule_group(rules, "package_names"),
        "risks": [
            {
                "id": item["id"],
                "pattern": re.compile(item["pattern"]),
                "severity": item["severity"],
                "message": item["message"],
                "suggestion": item["suggestion"],
            }
            for item in rules.get("risk_patterns", [])
        ],
        "images": [
            {
                "id": item["id"],
                "pattern": re.compile(item["pattern"], re.IGNORECASE),
                "severity": item["severity"],
                "message": item["message"],
                "suggestion": item["suggestion"],
                "recommendation": item.get("recommendation"),
            }
            for item in rules.get("image_risks", [])
        ],
    }


def add_docker_platform(line: str, arch: str) -> tuple[str, str | None]:
    """Insert --platform when docker run/create/build lacks it."""
    if "--platform" in line:
        return line, None
    match = _DOCKER_PLATFORM_PATTERN.search(line)
    if not match:
        return line, None
    platform = f"--platform linux/{arch}"
    pos = match.end()
    return line[:pos] + f" {platform}" + line[pos:], f"Docker 补齐 {platform} 运行参数"


def convert_text(
    text: str,
    rules: dict,
    target_os: str,
    arch: str,
    target_label: str | None = None,
) -> tuple[str, dict]:
    compiled = compile_rules(rules)
    notice = rules.get("notice") or _DEFAULT_NOTICE
    lines = text.splitlines()
    changelog: list[dict] = []
    risks: list[dict] = []
    recommendation_ids: list[str] = []
    converted_lines: list[str] = []

    for idx, original in enumerate(lines, start=1):
        code, comment = split_inline_comment(original)
        if not code.strip():
            converted_lines.append(original)
            continue

        applied: list[dict] = []
        for group_key in ("pkg_manager", "commands"):
            for item in compiled[group_key]:
                new_code, count = item["pattern"].subn(item["replacement"], code)
                if count:
                    applied.append(item)
                    code = new_code

        if re.search(r"\bapt\b", code, re.IGNORECASE):
            for item in compiled["pkg_names"]:
                new_code, count = item["pattern"].subn(item["replacement"], code)
                if count:
                    applied.append(item)
                    code = new_code

        new_code, docker_detail = add_docker_platform(code, arch)
        if docker_detail:
            applied.append(
                {
                    "description": docker_detail,
                    "note": "请确认目标镜像存在 linux/arm64 架构版本，否则改用国产替代镜像或基于源码构建。",
                }
            )
            code = new_code

        seen_risk_ids: set[str] = set()
        for item in compiled["risks"]:
            if item["id"] in seen_risk_ids:
                continue
            if item["pattern"].search(code):
                seen_risk_ids.add(item["id"])
                risks.append(
                    {
                        "line": idx,
                        "severity": item["severity"],
                        "id": item["id"],
                        "message": item["message"],
                        "suggestion": item["suggestion"],
                    }
                )

        for item in compiled["images"]:
            if item["id"] in seen_risk_ids:
                continue
            if item["pattern"].search(code):
                seen_risk_ids.add(item["id"])
                risks.append(
                    {
                        "line": idx,
                        "severity": item["severity"],
                        "id": item["id"],
                        "message": item["message"],
                        "suggestion": item["suggestion"],
                    }
                )
                recommendation = item.get("recommendation")
                if recommendation and recommendation not in recommendation_ids:
                    recommendation_ids.append(recommendation)

        converted = code + (comment or "")
        if converted != original:
            details: list[str] = []
            notes: list[str] = []
            for item in applied:
                description = item.get("description")
                if description and description not in details:
                    details.append(description)
                note = item.get("note")
                if note and note not in notes:
                    notes.append(note)
            changelog.append(
                {
                    "line": idx,
                    "type": "modify",
                    "before": mask_sensitive(original),
                    "after": mask_sensitive(converted),
                    "details": details,
                    "notes": notes,
                }
            )
        converted_lines.append(converted)

    recommendations = [
        item for item in rules.get("recommendations", []) if item["id"] in recommendation_ids
    ]
    report = {
        "notice": notice,
        "meta": {
            "target_env": target_label or target_os,
            "os": target_os,
            "arch": arch,
            "input_lines": len(lines),
            "modified_lines": len(changelog),
            "risk_count": len(risks),
        },
        "changelog": changelog,
        "risks": risks,
        "recommendations": recommendations,
    }
    return "\n".join(converted_lines), report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert CentOS/x86 shell and Docker scripts to UOS/Kylin/Euler ARM environments."
    )
    parser.add_argument("input", nargs="?", help="path to the shell script; read from stdin when omitted")
    parser.add_argument(
        "--target-env",
        choices=list(TARGET_ENV_MAP),
        default=None,
        help="目标信创环境：银河麒麟ARM / 统信UOS ARM / 欧拉OS ARM",
    )
    parser.add_argument(
        "--target",
        choices=["uos", "kylin", "euler"],
        default="uos",
        help="target OS, kept for compatibility (default: uos)",
    )
    parser.add_argument(
        "--arch",
        choices=["arm64", "amd64"],
        default="arm64",
        help="target architecture, kept for compatibility (default: arm64)",
    )
    parser.add_argument("--output", help="write converted script to this file; default stdout")
    parser.add_argument("--report", help="write JSON report to this file; default printed after ---REPORT---")
    args = parser.parse_args()

    if args.input:
        source = Path(args.input).read_text(encoding="utf-8", errors="replace")
    else:
        source = sys.stdin.buffer.read().decode("utf-8", errors="replace")

    if args.target_env:
        env = TARGET_ENV_MAP[args.target_env]
        target_os, arch, target_label = env["os"], env["arch"], env["label"]
    else:
        target_os, arch, target_label = args.target, args.arch, f"{args.target}/{args.arch}"

    rules = load_rules()
    converted, report = convert_text(source, rules, target_os, arch, target_label)

    if args.output:
        Path(args.output).write_text(converted, encoding="utf-8")
    else:
        sys.stdout.buffer.write(converted.encode("utf-8"))
        if not converted.endswith("\n"):
            sys.stdout.buffer.write(b"\n")

    report_json = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        Path(args.report).write_text(report_json, encoding="utf-8")
    else:
        sys.stdout.buffer.write(b"\n---REPORT---\n")
        sys.stdout.buffer.write(report_json.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
