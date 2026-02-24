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

## 运行示例（终端实录）

```text
(base) PS E:\VScodeProjects\xiyouTRPG\xiyou_solo> python main.py
任务：黄风岭迷雾 | 目标：找出真路并护送药材通过山口。 | 地点：黄风岭前哨
HP 8/11 | 金币 45 | 关键道具 dagger,simple_armor
你要做什么？> new
开始新冒险。
Quest Hooks / 任务钩子
1) 黄风岭迷雾 - 商队在黄风岭迷失，真假路标混杂。
2) 白骨疑影 - 村中来客身份可疑，误判可能惹大祸。
3) 火焰山借扇 - 热浪逼城，需借来宝扇缓解灾情。
4) 女儿国风波 - 庆典前夕流言四起，需化解误会。
选择任务（1-4 或 random）：2
白骨疑影
- 村中来客身份可疑，误判可能惹大祸。
- 辨明身份并避免误伤无辜。
输入角色名：小丑
Races / 种族
1) 人族 - 适应力强，开局更富有。 (human)
2) 妖族·狐灵 - 擅社交与欺瞒。 (fox_spirit)
3) 妖族·山精 - 体魄厚实，耐打耐爬。 (mountain_sprite)
4) 龙裔 - 意志强，具龙息。 (dragonkin)
5) 灵修 - 灵性强，受吉兆庇护。 (spirit_born)
选择种族编号：1
Classes / 职业
1) 武行者 - 擅长正面冲突。 (martial)
2) 行脚僧 - 稳住局面，擅长心性。 (pilgrim_monk)
3) 方士 - 调查与符法专精。 (talismanist)
4) 游侠 - 机动与追踪能力强。 (wanderer)
选择职业编号：2
属性生成方式：1)3d6 2)4d6去最低（默认1）> 2
Pick two bonus attributes / 选择两项加值：
1) 体
2) 智
3) 心
4) 运
> 1
Pick two bonus attributes / 选择两项加值：
1) 体
2) 智
3) 心
4) 运

> 2
任务：白骨疑影 | 目标：辨明身份并避免误伤无辜。 | 地点：白骨岭驿站
HP 14/14 | 金币 70 | 关键道具 healing_herbs,incense_charm
你要做什么？> 遇到随机路人发现是自己前男友
[DM] Part A: Narrative
在白骨岭驿站的小道上，你突然认出了路边的那个人，他竟然是你曾经的前男友。昔日的甜蜜回忆涌上心头，但此刻却让你感到一丝错愕和不安。你不知道他此时的身份是否真实，还是潜藏着某种阴谋。周围的环境仿佛也随着这次重逢变得紧张起来，白骨岭的阴影似乎在你们之间游荡。你可以选择上前询问他的来意，保持距离观察他的举动，或者试着寻找周围的线索了解更多情况。

- 你想上前与他对话吗？
- 还是选择躲在一旁观察他？
- 或者你想寻找其他线索？

Part B: Directive JSON
Actions:
1) 上前询问前男友的来意
2) 保持距离观察他的举动
3) 寻找周围的线索
判定类型：被动（不掷骰） | 属性：智
被动值计算：10 + mod(1) + bonus(0) = 11 vs DC15
被动失败：需要更强手段。
任务：白骨疑影 | 目标：辨明身份并避免误伤无辜。 | 地点：白骨岭驿站
HP 14/14 | 金币 70 | 关键道具 healing_herbs,incense_charm
你要做什么？>
```
