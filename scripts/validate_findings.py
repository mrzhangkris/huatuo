#!/usr/bin/env python3
"""validate_findings.py — 审计发现结构化输出验证器（skill-audit 收尾用）

对 findings.json 做零依赖 schema 校验（schema 定义在 references/findings-schema.json）。
审计报告写成散文前，先落一份机器可查的 findings.json 并跑本验证器——
保证每条发现四要素齐全（证据/触发方式/定级/修复），CI 也能消费。

用法：
  python3 validate_findings.py <findings.json>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA = {
    "required": ["skill", "audited_at", "findings"],
    "finding_required": ["id", "severity", "file", "line", "quote", "trigger", "fix", "status"],
    "severity_enum": ["blocker", "high", "medium", "low", "info"],
    "status_enum": ["open", "fixed", "refuted", "deferred"],
}


def check(instance: dict) -> list[str]:
    errs: list[str] = []
    for key in SCHEMA["required"]:
        if key not in instance:
            errs.append(f"顶层缺字段：{key}")
    for key in ("skill", "audited_at"):
        if key in instance and not isinstance(instance[key], str):
            errs.append(f"{key} 必须是字符串")
    findings = instance.get("findings")
    if not isinstance(findings, list):
        errs.append("findings 必须是数组")
        return errs
    for i, f in enumerate(findings):
        pre = f"findings[{i}]"
        if not isinstance(f, dict):
            errs.append(f"{pre} 必须是对象")
            continue
        for key in SCHEMA["finding_required"]:
            if key not in f:
                errs.append(f"{pre} 缺字段：{key}")
        for key in ("id", "file", "quote", "trigger", "fix"):
            if key in f and not isinstance(f[key], str):
                errs.append(f"{pre}.{key} 必须是字符串")
        if "line" in f and not isinstance(f["line"], int):
            errs.append(f"{pre}.line 必须是整数")
        if f.get("severity") not in SCHEMA["severity_enum"]:
            errs.append(f"{pre}.severity 必须是 {SCHEMA['severity_enum']} 之一")
        if f.get("status") not in SCHEMA["status_enum"]:
            errs.append(f"{pre}.status 必须是 {SCHEMA['status_enum']} 之一")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description="审计发现 findings.json 验证器")
    ap.add_argument("file", type=Path)
    args = ap.parse_args()
    try:
        data = json.loads(args.file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"❌ 读取失败：{e}")
        return 1
    errs = check(data)
    if errs:
        print(f"❌ findings.json 未通过 schema（{len(errs)} 处）：")
        for e in errs:
            print("  " + e)
        return 1
    n = len(data.get("findings", []))
    print(f"✅ findings.json 通过 schema：{n} 条发现，四要素齐全")
    return 0


if __name__ == "__main__":
    sys.exit(main())
