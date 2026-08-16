# 确定性 lint 检查项判据（skill-audit 视角 F）

> 脚本：`{SKILL_DIR}/scripts/audit_lint.py <技能目录> [--strict]`
> 原则：机械能查的不派子代理；lint 查**质量**，不构成安全边界（安全对抗走 skill-vetter / 视角 E）。
> 所有检查项 advisory；`--strict` 仅 L1/L2 命中才非零退出（CI 门禁）。

| # | 检查项 | 判据 | 来源 |
|---|---|---|---|
| L1 | 链接可解析 | SKILL.md/references 里引用的相对文件路径（含 `{SKILL_DIR}/` 前缀剥除后）不存在 | agent-ecosystem/skill-validator `validate links` |
| L2 | 引用图孤儿 | `references/`、`scripts/` 下的文本文件被任何 md/py 引用 0 次（内部模块 `_common.py` 除外——按文件名被 import 即算引用） | kurtpayne/skillscan-lint GR 系列 |
| L3 | token 预算 | SKILL.md >300 行（渐进披露红线）；全库文本总字符（CJK 近似 1 字符≈1 token 量级）作为上下文成本上报 | agent-ecosystem/skill-validator token counts + HaasStefan/skills-lint |
| L4 | 模糊词 | 指令文本（非 .py）软化词命中：按需/尽量/酌情/视情况/可能/一般/通常/建议考虑… | skillscan-lint weasel words（QL-004） |
| L5 | 跨语言污染 | 文本文件 CJK 与拉丁占比都 >25% 且总长 >200（混装说明来源拼贴） | skill-validator `analyze contamination` |
| L6 | 无关文件 | 技能目录含图片/压缩包/缓存/系统文件（png/jpg/zip/.DS_Store/__pycache__…） | skill-validator「不应出现在技能目录的文件」 |
| L7 | 残留标记 | 指令文本含 TODO/FIXME/待实现（发布前应清掉） | skillscan-lint QL-015 |
| L8 | 路径硬编码 | 文档/脚本含绝对路径（`/Users/`、`/home/`、`C:\`、`~/.config`…）；技能只用 `{SKILL_DIR}` 占位符 + `Path(__file__)` 自定位 | 本技能实战（novel-writer 第三轮审计） |

## 使用位置（执行流程第 2 步）

派子代理前先跑 `audit_lint.py`：L1/L2/L6/L7/L8 的命中直接进清单（无需子代理重复读），L3/L4/L5 作为子代理的「待判断」输入。lint 结果写进审计基线，节省子代理配额。
