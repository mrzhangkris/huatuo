# 华佗 · huatuo

> 多视角深度审计技能：确定性 lint 先行，子代理多视角找缺陷，反证门拦截假阳性，产出带文件行号的证据化问题清单 + 修复闭环。

## 审计流程

1. **确定性 lint 先行**：`audit_lint.py` 零 LLM 扫坏链接/孤儿文件/token 预算/模糊词/路径硬编码
2. **多视角子代理**：结构 / 流程 / 数据 / 文档 / 契约同步 独立冷启动，每条缺陷带「文件+行号+原句+触发方式」
3. **反证门**：独立反证代理逐条尝试推翻候选，推不翻的才进最终清单
4. **仲裁定级**：Blocker / High / Medium / Low / Info，输出 `findings.json`（schema 验证）
5. **修复闭环**：按级修复 → 回归验收 → 无新引入 → 存量数据迁移检查

内置大野耐一视角（现地现物 / 七大浪费 / 五个为什么 / 防错）与费曼可解释性测试（定义剥夺 / 大一新生 / 最小例子）。

## 触发场景

- 「审计技能」「这技能写得怎么样」「审一下这个技能」「技能审计」
- 不触发：代码审查（→ bianque）；评分优化（→ darwin）；装第三方安全体检（→ skill-vetter）

## 安装

```bash
git clone https://github.com/mrzhangkris/huatuo.git
# 把 huatuo/SKILL.md 复制到你所用 runtime 的技能目录即可
```

各 runtime 技能目录速查：

| Runtime | 技能目录 |
|---|---|
| DSH | `~/.dsh/skills/` |
| Claude Code | `~/.claude/skills/` |
| Codex / Cursor / OpenClaw 等 | 按各自 skills 根目录约定 |

## 相关技能

- 仓颉 `cangjie` 造技能 · 扁鹊 `bianque` 审代码 · 达尔文 `darwin-skill` 优化

## 许可

MIT © 2026 mrzhangkris
