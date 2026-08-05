#!/usr/bin/env python3
"""Offline converter for CentOS/x86 shell and Docker scripts -> UOS/Kylin ARM."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent / "rules.json"


def load_rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def compile_rules(rules: dict) -> dict:
    return {
        "pkg_manager": [(re.compile(pattern), repl) for pattern, repl in rules["package_manager"].items()],
        "commands": [(re.compile(pattern), repl) for pattern, repl in rules["commands"].items()],
        "pkg_names": [(re.compile(pattern), repl) for pattern, repl in rules["package_names"].items()],
        "risks": [
            {
                "id": item["id"],
                "pattern": re.compile(item["pattern"]),
                "severity": item["severity"],
                "message": item["message"],
                "suggestion": item["suggestion"],
            }
            for item in rules["risk_patterns"]
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
            for item in rules["image_risks"]
        ],
    }


def add_docker_platform(line: str, arch: str) -> tuple[str, str | None]:
    if "--platform" in line:
        return line, None
    match = re.search(r"\bdocker\s+(run|create|build)\b", line)
    if not match:
        return line, None
    platform = f"--platform linux/{arch}"
    pos = match.end()
    return line[:pos] + f" {platform}" + line[pos:], f"Docker 补齐 {platform} 运行参数"


def convert_text(text: str, rules: dict, target: str, arch: str) -> tuple[str, dict]:
    compiled = compile_rules(rules)
    lines = text.splitlines()
    changelog: list[dict] = []
    risks: list[dict] = []
    recommendation_ids: list[str] = []
    converted_lines: list[str] = []

    for idx, original in enumerate(lines, start=1):
        line = original
        details: list[str] = []

        for pattern, replacement in compiled["pkg_manager"]:
            new_line, count = pattern.subn(replacement, line)
            if count:
                details.append(f"包管理器 yum/dnf 替换为 apt（{count} 处）")
                line = new_line

        for pattern, replacement in compiled["commands"]:
            new_line, count = pattern.subn(replacement, line)
            if count:
                details.append("服务命令适配为 systemctl")
                line = new_line

        if re.search(r"\bapt\b", line, re.IGNORECASE):
            for pattern, replacement in compiled["pkg_names"]:
                new_line, count = pattern.subn(replacement, line)
                if count:
                    details.append(f"软件包名修正（{count} 处）")
                    line = new_line

        new_line, docker_detail = add_docker_platform(line, arch)
        if docker_detail:
            details.append(docker_detail)
            line = new_line

        seen_risk_ids: set[str] = set()
        for item in compiled["risks"]:
            if item["id"] in seen_risk_ids:
                continue
            if item["pattern"].search(line):
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
            if item["pattern"].search(line):
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
                if item["recommendation"] and item["recommendation"] not in recommendation_ids:
                    recommendation_ids.append(item["recommendation"])

        if line != original:
            changelog.append(
                {
                    "line": idx,
                    "type": "modify",
                    "before": original,
                    "after": line,
                    "details": details,
                }
            )
        converted_lines.append(line)

    recommendations = [item for item in rules["recommendations"] if item["id"] in recommendation_ids]
    report = {
        "meta": {
            "target": target,
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
        description="Convert CentOS/x86 shell and Docker scripts to UOS/Kylin ARM environments."
    )
    parser.add_argument("input", nargs="?", help="path to the shell script; read from stdin when omitted")
    parser.add_argument("--target", choices=["uos", "kylin"], default="uos", help="target OS (default: uos)")
    parser.add_argument("--arch", choices=["arm64", "amd64"], default="arm64", help="target architecture (default: arm64)")
    parser.add_argument("--output", help="write converted script to this file; default stdout")
    parser.add_argument("--report", help="write JSON report to this file; default printed after ---REPORT---")
    args = parser.parse_args()

    if args.input:
        source = Path(args.input).read_text(encoding="utf-8", errors="replace")
    else:
        source = sys.stdin.buffer.read().decode("utf-8", errors="replace")

    rules = load_rules()
    converted, report = convert_text(source, rules, args.target, args.arch)

    if args.output:
        Path(args.output).write_text(converted, encoding="utf-8")
    else:
        sys.stdout.buffer.write(converted.encode("utf-8"))
        if not converted.endswith("\n"):
            sys.stdout.buffer.write(b"\n")

    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        sys.stdout.buffer.write(b"\n---REPORT---\n")
        sys.stdout.buffer.write(json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
