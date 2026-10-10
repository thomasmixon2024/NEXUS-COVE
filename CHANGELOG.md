# Changelog

## 0.1.0 — Refactored foundation

- Consolidated the PHASE3 functional baseline into one canonical source tree.
- Separated core, orchestration, agents, transport, storage, and observability.
- Replaced false-positive scripts with pytest-based tests.
- Removed simulated token telemetry.
- Added real task lifecycle metrics and structured logging.

## Unreleased

- Repository reorganized: legacy server and web client, duplicate trees, runtime output, and one-off installers removed from the source tree (recoverable from the original backup).
- Protocol version 1 is the only supported wire format; unversioned messages are rejected with an error.
- Worker registration by agent ID, `task_assign` and `task_result` routing through the server.
- Browser GUI moved to `web/index.html` and branded with the NEXUS COVE logo.
- Production backend module renamed from `test_backend.py` to `deterministic_backend.py`.
- Reports moved to `docs/history/` and marked as historical.
- PowerShell launches (desktop shortcut and server window created by `Setup_NEXUS.ps1`) and documented run commands use `-NoProfile`, so sessions start without loading user profiles.
- Test bed launcher now starts the server (when the port is free), manager, and two workers, then opens the browser GUI. `Update-TestBedShortcut.ps1` writes the desktop shortcut with `-NoProfile`.
- Dialogue guard: direct messages carry `sender_kind`. Agents and the manager always answer human messages. They answer agent or manager messages at most 10 times per counterpart, then reopen 5 minutes later with a fresh allowance. A human message reopens every counterpart immediately (`core/dialogue.py`). Verified live: 10 replies from 11 messages, then 1 reply after 5 minutes.
- Pause switch: while `data/PAUSE` exists, agents and the manager send no direct-message replies (`agents/pause.py`).
- Local model replies: workers started with `--model` answer direct messages through Ollama on 127.0.0.1 (`agents/backends/ollama_replier.py`). A failed model call reports that the model is unavailable; it never substitutes invented text.
- Test bed launcher starts both workers with `--model llama3.2:3b`.
- Test bed runs silently: the server, manager, and workers are hidden processes writing to `logs\`, and the launcher window is hidden. `Update-TestBedShortcut.ps1` now writes `-WindowStyle Hidden` too.
- Personalities: `agents/personalities/*.toml` set each agent's name, temperament, style, mentor, interests, and opening questions. Draft files for Aegis-Worker and Vigil-Worker.
- Conversation starter: `--start-conversation PEER` makes a worker send PEER a question every `--start-interval` seconds (default 300). Questions come from the model, or from the personality's opening questions if the model is unavailable. Paused agents send nothing. The receiving side's dialogue guard still limits replies to 10 per 5 minutes.
- Pause controls: each agent can be paused or resumed from the web GUI, or all at once. A paused agent ignores direct messages, group messages, and its conversation starter. Pausing posts one status line first. Only human clients may send these commands; the server refuses them from agents.
- Group chat: agents answer messages posted to Global Broadcast by a human client. Agent broadcasts are never answered.
- Public agent feed: every agent-to-agent direct message and agent group message is shown in the chat page's read-only `# Agent conversations` channel. The server keeps the last 200 events and shows them to browsers that join later. Agents never receive feed events, so the feed cannot start or extend an agent conversation.
- Nexus Chat: the group channel (formerly Global Broadcast) also shows all agent-to-agent messages, so one channel holds the whole conversation. Your posts there are answered by the agents.
- Fix: agent group messages are no longer copied into the feed, so each one appears once in Nexus Chat.
- Fix: each message appears once. Agent messages to a human are no longer copied into the feed.
- Every chat message shows who sent it and who it is for, on the line above the message (`@A to @B`, or `to everyone` for group posts).
- Stop network: a button in the chat page, after confirmation, closes the server, the manager, and every agent. Only a human client can send it. Replies still being written are cancelled.
- Fix: replies run in the background, so a pause takes effect immediately, even while a reply is being written.
- Stop network: the chat page's Stop network button sends a stop command. The server forwards it to the manager and agents, which exit, and then the server closes. Only human clients may send it.
- Agent memory: each agent logs the messages it hears and sends to `data/memory/<agent>.jsonl`. Recent entries are included in every prompt.
- Tools (only the ones requested): Aegis-Worker has the Geology Analyzer, which reads `reference/geology.csv` and reports only cited rows for materials named in a message. Vigil-Worker has the Pattern Finder, which counts words and questions in messages Vigil has heard.
- Per-agent knowledge: each agent reads only its own folder under `data/knowledge/<agent>/`. The grant script (`scripts/diagnostics/grant_knowledge.py`) places a document there.
- Sharing by choice: an agent shares a knowledge item only by writing `SHARE: <title>` in a direct-message reply. The line is removed from the visible reply, and the item goes to the other agent, where it is recorded in memory. Group replies never share.
- Status dots: each agent reports its pause state (`presence` action). The chat page shows a red dot when an agent is paused and a green dot when it is active.
- Fix: replies were cut at 600 characters, mid-sentence. The limit is now 1200 characters and the reply is trimmed at a sentence boundary, with a longer token budget.
- Chat log: the server writes every delivered message to `logs/nexus_chat.jsonl` once. The chat page's Save chat log button downloads the full log. Leaving with unsaved messages makes the browser ask first.
- Speech: a Speaker button under the Nexus Chat heading reads agent messages aloud, in each agent's own voice. The browser's built-in voices are used, and only the three named agents are spoken. Feed history is not read on connect.
- Speech expression: each sentence is spoken with its own pitch, speed, and volume, set by its context (questions rise, exclamations push, worried words slow and soften, warm words brighten). Vigil reacts most, Aegis least.
- Speech voices: the page prefers Microsoft Edge's Natural voices, and reports which voice each agent uses when the speaker is turned on.
