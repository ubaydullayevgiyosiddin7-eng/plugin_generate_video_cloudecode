# Agent definitions: the knowledge team

| File | Role |
|---|---|
| `video-retro.md` | Retrospective analyst: evidence → proposals report (read-only on the kit) |
| `video-toolsmith.md` | Implements approved tool/engine items (engine/, tools/) |
| `video-curator.md` | Implements approved lesson/template/doc items, metrics, backlog, changelog, inbox |
| `video-kit-auditor.md` | Independent PASS/FAIL audit after every kit change |

The process is in `docs/learning_loop.md`. To install for all projects, run `python agents/install.py`, which copies these files to `~/.claude/agents/`, then start a new Claude Code session. Production roles (reviewer, reframer, QA…) are still prompt templates in `templates/agent_prompts.md`.
