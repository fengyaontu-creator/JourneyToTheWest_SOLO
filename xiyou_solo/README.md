# xiyou_solo

LLM-driven TRPG prototype with deterministic rule resolution, multi-session isolation, and pluggable LLM providers.

## Architecture

```text
ui/cli.py
  -> core/engine.py (pure game orchestration; no I/O/fs)
     -> core/rules.py (deterministic dice/check logic)
     -> llm/base.py (provider interface)
        -> llm/openrouter.py | llm/mock.py
  -> infra/session_store.py (SessionStore/GameSessionStore persistence + migration + active session pointers)
  -> infra/metrics.py (latency/tokens per turn)
```

## Quickstart

From repository root:

```powershell
python -m xiyou_solo.ui.cli --provider mock
```

OpenRouter mode:

```powershell
set OPENROUTER_API_KEY=your_key
set OPENROUTER_MODEL=openai/gpt-4o-mini
python -m xiyou_solo.ui.cli --provider openrouter
```

Optional startup session:

```powershell
python -m xiyou_solo.ui.cli --provider mock --session sess_20260228_123456
```

## Demo Script (5 minutes)

1. Run `python -m xiyou_solo.ui.cli --provider mock`
2. Show `/list` (session isolation per player)
3. Run one action like `inspect the cart tracks`
4. Highlight output:
   - narrative + offered actions
   - `[metrics] latency=...ms tokens=...`
5. Run `/new`, do another action, then `/list` again (two isolated sessions)
6. Exit and rerun with `--session <id>` to resume a specific run

## Design Decisions

- LLM constrained by deterministic rules:
  - Provider proposes narrative/directive.
  - Engine resolves checks/outcomes via deterministic `core/rules.py`.
- Session isolation:
  - Session files: `data/sessions/<session_id>/{state.json,log.json,meta.json}`
  - CLI player identity: `~/.xiyou_solo/player_id`
  - Active session pointer: `~/.xiyou_solo/active_session`
  - One-time migration of legacy shared files to isolated session folders.
- Provider abstraction:
  - `LLMProvider` interface with `OpenRouterProvider` and deterministic `MockProvider`.
- Observability:
  - Per-turn latency (required) and tokens (if available) surfaced in CLI.

## Tests

Run from repository root:

```powershell
pytest -q
```

Added coverage includes:
- `tests/test_state_serialization.py`
- `tests/test_rules_deterministic.py`
