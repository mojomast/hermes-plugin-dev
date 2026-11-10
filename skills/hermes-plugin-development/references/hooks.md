# Hooks: the 46 names and what each may return

Sources: `hermes_cli/plugins.py::VALID_HOOKS` (the runtime allowlist), the
catalog table in `website/docs/user-guide/features/hooks.md` (exact payload
fields per event), and the observer contract in
`website/docs/developer-guide/observer-hooks.md`. Verified against
`origin/main` @ `acdc8f1ba6` (2026-11-08): 46 names.

Register with `ctx.register_hook(hook_name, callback, *, hold_stream=False)` and
declare **every** name in `provides_hooks` — `validate` compares the two.
`hold_stream=True` is only for hooks that must see a completed stream; it is not
a way to slow the token path.

## Four return shapes — read this before writing a callback

| Category | What the return value does |
|---|---|
| **Observer** | Ignored. Use it to record, not to steer. |
| **Transform** | The first valid string (or dict, where documented) replaces the value; `None` passes through. |
| **Directive/control** | Only documented shapes are consumed (`{"action": "block"}`, `{"action": "continue"}`, …); anything else is ignored. |
| **Policy** (`pre_tool_call`) | Block wins over approve; `modify` returns are shallow-merged into the tool arguments. A timed-out policy callback **fails closed** (tool blocked). |

Everything else **fails open**: a callback that raises or times out is logged and
skipped, and the agent keeps running. Timeouts come from
`plugins.hook_callback_timeout` (default 30 s; `0` disables, max 600).
`subagent_stop` is never moved onto a timeout worker — it has a caller-thread
contract.

## Names by family

**Tools and the model loop**

| Hook | Kind | Note |
|---|---|---|
| `pre_tool_call` | policy | May block/approve/modify; raw args, so treat as sensitive |
| `post_tool_call` | observer | Fires after blocked, error and success alike |
| `transform_tool_result` | transform | After `post_tool_call`, before the conversation append |
| `transform_terminal_output` | transform | After bounded foreground capture, before output limiting |
| `pre_llm_call` | directive | String / `{"context": ...}` returns are joined into the user message; `{"action": "block"}` ends the turn |
| `post_llm_call` | observer | Successful, non-interrupted turns; carries `side_question_token` |
| `transform_llm_output` | transform | First non-empty string replaces the response |
| `pre_verify` | directive | Bounded edited-code verify gate; `agent.max_verify_nudges` |
| `pre_api_request` / `post_api_request` / `api_request_error` | observer | Per provider attempt; `request` is the sanitized copy |
| `pre_auxiliary_call` / `post_auxiliary_call` | observer | Titling, compression, MoA, vision, approval calls; adds `aux_task` |
| `transform_api_error_classification` | directive | Return a `reason` + flags to override the failover classifier |

**Streaming** (off the token path, immutable payloads): `on_stream_start`,
`on_stream_delta`, `on_stream_end`, `on_interim_message`.

**Sessions and skills**: `on_session_start`, `on_session_end`,
`on_session_finalize`, `on_session_reset`, `on_session_delete`,
`on_skill_lifecycle`, `subagent_start`, `subagent_stop`, `agent_loop_stopped`,
`post_compaction`.

**Gateway and messaging**: `pre_gateway_dispatch` (skip/rewrite an inbound
event before auth and pairing), `post_gateway_admission`,
`gateway_platform_event` (normalized envelopes only — never adapter handles),
`on_room_member_activity`, `pre_command` (before a recognized slash command;
deliberately not fired on the running-agent intercept path).

**Approvals and human input**: `pre_approval_request`,
`post_approval_response`, `on_human_input_request`, `on_human_input_resolved`.
Returns are ignored — **veto through `pre_tool_call`**, not here.

**Kanban** (all post-commit, returns ignored): `kanban_task_claimed`,
`kanban_task_completed`, `kanban_task_blocked`, `on_kanban_worker_spawned`,
`on_kanban_worker_exited`, `on_kanban_worker_stale_claim`,
`on_kanban_task_updated` (field names only, never values), `on_kanban_dispatch_tick`.

**Speech**: `pre_transcription` — mutate `prompt` / `language` / `model` before
any STT backend runs (`file_path` is read-only, last writer wins).

## Rules that bite

- Accept `**kwargs`. Signature inspection passes only the fields a legacy
  callback names; `**kwargs` gets the whole current payload.
- Field mistakes are reported once at WARNING (naming the fields the hook
  actually sends) and then at DEBUG, so a typo does not flood the log.
- `conversation_id` survives compression rotation; key per-conversation state on
  it, not on `session_id`.
- **Middleware is not a hook.** Prompt injection, tool-call wrapping and other
  behaviour changes belong to `ctx.register_middleware(kind, callback)`, which
  has its own registry and its own `provides_middleware` catalog capability.
- Do not push standing instructions through `pre_llm_call` on every turn. Use
  `ctx.register_system_prompt_section(id, callable|str, position="after_memory",
  max_chars=...)` — it is cached, frozen on compression and resume-safe.
- `hermes hooks list` shows configured shell/outbound hooks, **not** this plugin
  surface. The runtime truth is `VALID_HOOKS`; when it disagrees with this page,
  the source wins.
