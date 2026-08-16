#!/usr/bin/env python3
"""audit_lint.py — 技能确定性 lint（skill-audit 视角 F：可脚本化检查，零 LLM 零 token）

机械检查先跑一遍，把「确定性缺陷」和「需子代理判断的缺陷」分开——lint 能查的
不浪费子代理。全部 advisory 输出，只有 --strict 且命中 L1/L2 才非零退出（CI 门禁用）。

用法：
  python3 audit_lint.py <技能目录> [--strict]

检查项（判据与阈值见 references/lint-checks.md）：
  L1 链接可解析   md 中引用的相对文件路径是否存在（{SKILL_DIR}/ 前缀自动剥掉）
  L2 引用图       references/ 与 scripts/ 下文件是否被任何 md/py 引用（孤儿）
  L3 token 预算   SKILL.md 行数 / description 字节 / 全库 md 总字符（CJK 按 1 token 估算）
  L4 模糊词       软化词命中（按需/尽量/酌情/视情况/可能/建议考虑…），带行号
  L5 跨语言污染   文本文件 CJK 与拉丁混装（两侧占比都 >25%）
  L6 无关文件     图片/压缩包/缓存/系统文件（png/jpg/zip/.DS_Store/__pycache__…）
  L7 残留标记     TODO/FIXME/待实现 出现在指令文本
  L8 路径硬编码   文档/脚本里的绝对路径（/Users/ /home/ C:\\ ~/.config …）

诚实边界：lint 查质量，不构成安全边界（静态扫描 ≠ 安全审查，安全走 skill-vetter）。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {"__pycache__", "node_modules", ".git", ".venv", "venv"}
TEXT_EXTS = {".md", ".py", ".json", ".txt", ".sh", ".js", ".yaml", ".yml"}
JUNK_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".zip", ".tar",
             ".gz", ".7z", ".rar", ".pdf", ".docx", ".xlsx", ".DS_Store", ".pyc"}
WEASEL = ["尽量", "酌情", "视情况", "酌情处理", "建议考虑", "可考虑", "适当", "在必要时"]
# 注：「按需/可能/一般/通常」不列为 weasel——中文技能里「按需加载」常是精确指令（渐进披露），语境终判归人
ABS_PATH = re.compile(r"(?:/Users/|/home/|C:\\|~/\.config|~/\.dsh|Documents/写作)")
TODO_MARK = re.compile(r"TODO|FIXME|待实现")
# 只查「带路径的引用」（含 / 或 {SKILL_DIR}），裸文件名（如 findings.json）是散文提及，不作坏链接
FILE_REF = re.compile(r"(?:`|\]\(|\s)([\w./{}-]+\.(?:md|py|json|txt|sh|js|yaml|yml|ts))")
CJK = re.compile(r"[\u4e00-\u9fff]")
# 检测器自身文件（词表与判据示例不是被审内容，跳过全部检查）
DETECTOR_FILES = {"scripts/audit_lint.py", "references/lint-checks.md"}


def walk_text(skill: Path) -> list[Path]:
    out = []
    for p in skill.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts[len(skill.parts):]):
            continue
        if p.is_file() and p.suffix.lower() in TEXT_EXTS:
            out.append(p)
    return out


def rel(skill: Path, p: Path) -> str:
    return str(p.relative_to(skill))


def lint(skill: Path) -> dict:
    text_files = [p for p in walk_text(skill) if rel(skill, p) not in DETECTOR_FILES]
    issues: dict[str, list[str]] = {f"L{i}": [] for i in range(1, 9)}
    contents: dict[str, str] = {}
    for p in text_files:
        try:
            contents[rel(skill, p)] = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

    # ---- L1 链接可解析 + L8 路径硬编码 + L7 残留 ----
    for path, text in contents.items():
        for m in ABS_PATH.finditer(text):
            line = text[:m.start()].count("\n") + 1
            issues["L8"].append(f"{path}:{line}  {m.group(0)}")
        for m in TODO_MARK.finditer(text):
            line = text[:m.start()].count("\n") + 1
            issues["L7"].append(f"{path}:{line}  {m.group(0)}")
        if path.endswith(".md"):
            for m in FILE_REF.finditer(text):
                ref = m.group(1).replace("{SKILL_DIR}/", "")
                if "/" not in ref:
                    continue  # 裸文件名：散文提及，不判坏链接
                if "{" in ref:
                    continue  # 模板占位路径（{角色名}/{名}/{step}…），运行时才解析
                # 只查技能包内引用（references/scripts/skills/tests/templates）；
                # .story/.novel/tracking/chapters 等是书项目运行时路径，不在技能包里
                if not ref.startswith(("references/", "scripts/", "skills/", "tests/", "templates/")):
                    continue
                cand = (skill / ref).resolve()
                found = cand.exists() or any(skill.glob(f"**/{ref}"))
                if not found:
                    issues["L1"].append(f"{path}: {ref}  → 文件不存在")

    # ---- L2 引用图（孤儿检测，按 stem 匹配：from _common import 也算引用）----
    all_text = "\n".join(contents.values())
    for sub in ("references", "scripts"):
        base = skill / sub
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.suffix.lower() in TEXT_EXTS:
                if p.name == "__init__.py":
                    continue  # Python 包标识，隐式被 import 使用，不判孤儿
                stem = p.stem
                refs = sum(1 for path, text in contents.items()
                           if (stem in text or p.name in text) and rel(skill, p) != path)
                if refs == 0:
                    issues["L2"].append(f"{rel(skill, p)}  无任何引用（孤儿）")

    # ---- L3 token 预算 ----
    skill_md = skill / "SKILL.md"
    if skill_md.exists():
        lines = skill_md.read_text(encoding="utf-8").count("\n") + 1
        if lines > 300:
            issues["L3"].append(f"SKILL.md {lines} 行（>300，渐进披露建议细节下沉）")
        total = sum(len(t) for t in contents.values())
        issues["L3"].append(f"全库文本 {total} 字符（CJK 近似 token 量级），SKILL.md {lines} 行")

    # ---- L4 模糊词 ----
    for path, text in contents.items():
        if path.endswith(".py"):
            continue  # 只查指令文本，不查实现代码
        hits = 0
        for w in WEASEL:
            hits += text.count(w)
        if hits:
            issues["L4"].append(f"{path}  软化词 {hits} 处（按需/尽量/酌情…）")

    # ---- L5 跨语言污染（只查 md 散文：剥掉代码围栏/行内代码后两侧占比都 >45%）----
    def prose_only(t: str) -> str:
        t = re.sub(r"```.*?```", "", t, flags=re.DOTALL)  # 围栏代码块
        t = re.sub(r"`[^`\n]*`", "", t)                    # 行内反引号
        return t

    for path, text in contents.items():
        if not path.endswith(".md"):
            continue  # 代码/JSON/规则数据天然混装，不算污染
        t = prose_only(text)
        cjk = len(CJK.findall(t))
        latin = len(re.findall(r"[A-Za-z]", t))
        total = cjk + latin
        if total > 200 and cjk / total > 0.45 and latin / total > 0.45:
            issues["L5"].append(f"{path}  CJK:{cjk} 拉丁:{latin}（散文混装）")

    # ---- L6 无关文件 ----
    for p in skill.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts[len(skill.parts):]):
            continue
        if p.is_file() and (p.suffix.lower() in JUNK_EXTS or p.name == ".DS_Store"):
            issues["L6"].append(rel(skill, p))

    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description="技能确定性 lint（skill-audit 视角 F）")
    ap.add_argument("skill", type=Path)
    ap.add_argument("--strict", action="store_true", help="L1/L2 命中即退出 1（CI 门禁）")
    args = ap.parse_args()
    if not (args.skill / "SKILL.md").exists():
        print(f"❌ 不是技能目录（缺 SKILL.md）：{args.skill}")
        return 2
    issues = lint(args.skill)
    total = 0
    for k in (f"L{i}" for i in range(1, 9)):
        items = issues[k]
        if not items:
            continue
        total += len(items)
        print(f"\n[{k}] {len(items)} 处")
        for it in items:
            print("  " + it)
    print(f"\n共 {total} 处确定性发现（advisory；L1/L2 建议必看）")
    if args.strict:
        hard = len(issues["L1"]) + len(issues["L2"])
        if hard:
            print(f"❌ --strict：L1/L2 命中 {hard} 处")
            return 1
        print("✅ --strict 通过（无坏链接/孤儿）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
