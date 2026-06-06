# Architecture Deep Dive

## Overview

The agent is built around three core abstractions: **Providers**, **Tools**, and **Agents**.

```
User Objective (plain language)
         │
         ▼
   ┌─────────────┐
   │   main.py   │  ← reads objective from file or CLI arg
   └──────┬──────┘
          │
          ▼
   ┌─────────────────────┐
   │   Agent (mode)      │
   │  orchestrate /      │
   │  plan_execute       │
   └──────┬──────────────┘
          │
    ┌─────┴──────┐
    │            │
    ▼            ▼
Provider     Tool Registry
(LLM)        (30+ actions)
```

---

## Agent Modes

### Orchestrate Mode

The classic agentic loop. Each step involves a full LLM call.

**Pros:** flexible, handles unexpected situations well
**Cons:** more API calls = higher cost, less predictable execution path

**Loop:**
1. Send current messages + tool schemas to the LLM
2. Parse response (tool call / text / finish)
3. Execute tool → append result to context
4. Repeat until `finish` is called or max steps reached

**Context management:** a sliding window compresses old steps into compact text summaries, keeping token count within model limits while preserving the full recent history.

---

### Plan-Execute Mode

A two-phase approach optimized for cost and reliability.

**Phase 1 — Planning (1 LLM call)**
The model receives the objective and generates a complete JSON execution plan — a list of `{ tool, action, args }` steps. No tools are called yet.

**Phase 2 — Deterministic Execution**
Steps are executed one by one without further LLM calls. The executor routes each step to the correct tool module.

**Phase 3 — Visual Verification** *(visual steps only)*
After steps that interact with a UI, a screenshot is taken and sent to the LLM with a minimal verification prompt: *"Did the step succeed?"*. This uses a cheap, fast model call.

**Phase 4 — Recovery** *(triggered only on verification failure)*
A focused recovery call analyzes the failure and produces a corrected step sequence.

**Cost comparison:**

| Scenario | Orchestrate | Plan-Execute |
|---|---|---|
| 10-step task | 10 full LLM calls | 1 plan call + N cheap verification calls |
| Re-running same task | 10 full LLM calls | 0 calls (Replay mode) |

---

## Record & Replay

Every successfully completed task is serialized to `plans/<md5_hash>.json`:

```json
{
  "objective": "...",
  "recorded_at": "2025-05-10T14:32:00Z",
  "complete": true,
  "token_usage": { "total_input_tokens": 42310, "cost_usd": { "total": 0.259 } },
  "steps": [
    { "tool": "web", "action": "navigate", "args": { "url": "https://..." } },
    { "tool": "web", "action": "fill", "args": { "selector": "#username", "value": "..." } },
    { "tool": "spreadsheet", "action": "write_sheet", "args": { ... } },
    { "tool": "finish", "action": "finish", "args": { "success": true } }
  ]
}
```

On subsequent runs with the same objective, the agent detects the saved plan and replays it with **zero API cost**.

---

## Tool Registry

Tools are discovered and registered at startup. Each tool exposes a schema (name, description, actions, argument types) that is injected into the LLM's system prompt as a JSON tool spec.

```
ToolRegistry.build_default()
    └── registers: web · email · file · spreadsheet · document
                   windows · api · data · memory · visual · user_interaction · logic
```

The executor routes `tool_name + action` pairs to the correct Python module and returns a standardized `ToolResult(success, message, data, diagnostics)`.

---

## Multi-Provider Abstraction

All LLM providers implement a common interface (`BaseProvider`):

```python
class BaseProvider:
    async def create_message(self, model, messages, **config) -> Response: ...
```

Supported providers and their adapters:

| Provider | Protocol | Notes |
|---|---|---|
| Anthropic Claude | Native SDK | Supports Prompt Caching |
| OpenAI GPT-4o | OpenAI SDK | |
| Google Gemini | Gemini SDK | |
| Groq (Llama) | OpenAI-compat | |
| Ollama (local) | OpenAI-compat | No API key required |

Switching providers requires changing a single line in `config.py`.

---

## Recovery Engine

When a tool call fails with `recoverable=True`, the Recovery Engine:

1. Sends the failure details + current screenshot (if visual) to the LLM
2. Receives a corrective action (e.g., "the element wasn't loaded yet — wait and retry")
3. Executes the corrective action and resumes the main flow

Repeat invalid calls (same tool + same args, error on every attempt) are detected and blocked after 3 attempts, preventing infinite loops.

---

## Cost Tracking

Token usage is accumulated per run and broken down by:
- Input tokens
- Output tokens
- Anthropic Prompt Cache write tokens (25% premium over input)
- Anthropic Prompt Cache read tokens (90% discount vs input)

The final report shows exact USD cost based on current published pricing for each model.
