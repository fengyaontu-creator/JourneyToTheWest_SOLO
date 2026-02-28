# WeChat Group Command Draft

This file defines a minimal command set for multi-player TRPG in group chat.

## Room lifecycle

- `/new` Create room for current group.
- `/join` Join current room.
- `/start` Host starts the game.
- `/end` Host ends the room.

## Player setup

- `/pick <role_name>` Set role display name.
- `/me` Show current room/session/turn summary.
- `/party` Show party summary.

## Turn actions

- `/act <text>` Submit action on your turn.
- `/pass` Skip your own turn.
- `/next` Host forces next turn.

## Control

- `/pause` Host pauses game.
- `/resume` Host resumes game.

## Integration notes

- Adapter should pass `group_id`, `user_id`, `message_id`, and `text` into
  `services.game_service.handle_message`.
- Adapter should broadcast every returned line to the group.
- Message id should be stable for dedup.

## Local adapter run

```powershell
cd E:\VScodeProjects\xiyouTRPG\xiyou_solo
set WECHAT_TOKEN=your_token
python -m adapters.wechat_adapter
```

POST callback payload example:

```json
{
  "group_id": "group_1",
  "user_id": "user_1",
  "message_id": "msg_1001",
  "text": "/new"
}
```
