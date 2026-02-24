# xiyou_solo v0.5

单人 CLI 跑团，支持多存档、任务开局、自动掷骰、被动检定、商店道具，并接入 OpenRouter 叙事 DM。

## 运行

```powershell
cd xiyou_solo
python main.py
```

## 存档命令

- `new`
- `list`
- `load <session_id>`
- `delete <session_id>`

存档路径：

```txt
data/sessions/<session_id>/state.json
data/sessions/<session_id>/log.json
```

## 游戏命令

- `inv`
- `shop`
- `buy <item_id> [qty]`
- `use <item_id>`
- `seed <int>`
- `lang zh|en`
- `quit`

## OpenRouter 配置

1. 复制 `.env.example` 为 `.env`（或直接设置系统环境变量）
2. 设置：
   - `OPENROUTER_API_KEY`
   - `OPENROUTER_MODEL`（可选，默认 `openai/gpt-4o-mini`）

示例：

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
```

## 在线 / 离线模式

- 有 `OPENROUTER_API_KEY`：在线模式（调用 OpenRouter）
- 无 key 或调用异常：自动回退离线 stub，并提示“当前离线模式”

## 叙事与规则分离

- LLM 只负责：
  - Narrative（叙事文本）
  - Directive JSON（意图建议）
- 引擎负责：
  - 掷骰、优势/劣势、结果等级
  - HP/gold/inventory/state 更新
  - 战斗结算与奖励

## 日志事件

`log.json` 的 `events` 记录：

- `dm_narrative`
- `roll_result`
- `gold_change`
- `item_use`
- `scene`
- `update`
- `action`

