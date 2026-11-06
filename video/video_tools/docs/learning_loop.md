# Learning loop: how the kit gets better after every project

The production agents (reviewers, reframers, QA…) make one film. The **knowledge team** improves the kit itself so the next film is faster and better. Nothing that was learned should live only in a chat transcript.

## Why four agents, not one
Harvesting lessons, writing code, editing docs and checking the result are different skills. A single agent that checks its own work lets mistakes through. In the first project, independent QA agents found 2 HIGH issues the builders had missed. So there are separate roles with clear contracts, plus a gate where the manager (Claude) approves:

| # | Agent (definition in `agents/`) | Uzbek name | Reads | Writes | Never touches |
|---|---|---|---|---|---|
| 1 | `video-retro` | Retrospektiv tahlilchi | the finished project's work folder, QA reports, logs, EDL versions, `inbox.md`, owner feedback | `retro/<date>_<project>.md` (findings + proposals) | the kit files, the owner's media |
| 2 | `video-toolsmith` | Asbobsoz | approved tool/engine proposals, project scripts | `engine/`, `tools/`, `requirements.txt`, tool READMEs | docs/templates (except READMEs), the owner's media |
| 3 | `video-curator` | Kutubxonachi | approved lesson/template/doc proposals, the retro report | `docs/lessons.md`, `docs/workflow.md`, `templates/`, `CLAUDE.md`, `README.md`, `docs/metrics.md`, `docs/backlog.md`, `CHANGELOG.md`, `inbox.md` (clears processed items) | code |
| 4 | `video-kit-auditor` | Kit tekshiruvchisi | the whole kit after changes | `audit/<date>.md` (PASS/FAIL) | everything else (read-only + selftest) |

## When it runs
1. **During a project (cheap, continuous):** whenever something surprising happens (a QA finding of a new kind, a bug, an owner correction, a workaround, a time sink), the manager appends one entry to `inbox.md`. It takes 30 seconds and needs no agent.
2. **At the end of every project (mandatory, about 30–60 min, in the background):** the manager runs the loop below. Before starting, tell the owner in one line that this "saboq olish" step is happening.
3. **On demand:** the owner says "saboq ol", "asboblarni yangila" or similar → run the loop on the latest project.

## The loop
```
inbox.md + project folder ──► [1 video-retro] ──► retro/<date>_<project>.md (proposals P1–P3)
                                                        │
                                          manager reviews, approves/rejects
                                  (asks the owner only about preference-type items)
                                                        │
                           ┌────────────────────────────┴───────────────────────────┐
                 [2 video-toolsmith] (tool/engine items)              [3 video-curator] (lesson/template/doc items)
                           └────────────────────────────┬───────────────────────────┘
                                                        ▼
                                            [4 video-kit-auditor]
                                     selftest + docs↔code consistency + safety
                                                        │
                                FAIL → back to 2/3 with the audit report (max 2 rounds)
                                PASS → curator writes the CHANGELOG entry; manager tells the owner what improved
```
Agents 2 and 3 run in parallel; they own disjoint files. Agent 4 always runs last and never fixes anything itself.

## What counts as a finding (the retro agent's rules)
Each proposal must have:
- **evidence**: a file path, measurement, log line, or quote from the owner;
- **generality**: why it applies beyond this footage;
- **an actionable change**: exact target file and what to add or change;
- **a type**: one of `lesson` · `template` · `tool` · `engine` · `doc` · `preference` · `metric` · `backlog`;
- **a priority**: P1 = prevented or would prevent a visible defect or a big time sink; P2 = saves noticeable time; P3 = nice to have.

Criteria for proposing a **tool**: code was written ad hoc twice or more (by different agents or projects); or a manual check was repeated three or more times; or a defect class reached QA that an automatic check could have caught (e.g. "keys outside the valid region" became `project_keys`).

Criteria for a **template** change: an agent misunderstood something, produced the wrong schema, wasted time, or needed a follow-up message. Example: the reframer's coordinate space under hflip was ambiguous.

Criteria for a **lesson**: a non-obvious fact that cost time, with the rule to apply. Update an existing lesson rather than adding a near-duplicate, and record "confirmed in N projects".

`preference` items (what the owner likes or dislikes) need the owner's confirmation if they're inferred rather than stated.

## Metrics (`docs/metrics.md`)
Per project: footage counts, film length, wall time per phase, number of agents, tokens and duration per agent (from task notifications), renders and preview iterations, QA findings by severity, the owner's verdict. These make time estimates honest; the owner asks "qancha qoldi?" often.

## Backlog (`docs/backlog.md`)
Bigger ideas that aren't approved yet (engine features, automation). The retro agent lists them in its report, the curator copies them into the backlog, and the manager promotes them to approved work when there's time.

## How to brief each knowledge agent
The definitions in `agents/` hold the static role (method, rules, output schema). The manager's Agent call adds only the specifics:

```
video-retro:      "Project: <path to project root>. Work folder: <_ish path>. Final film: <path>.
                   Owner feedback during the project: <bullet quotes>. Inbox: video_tools/inbox.md.
                   Task notifications summary (agent, duration, tokens): <table>."
video-toolsmith:  "Approved items: <ids + text from retro report>. Retro report: <path>."
video-curator:    "Approved items: <ids>. Retro report: <path>. Also update metrics.md with: <table>."
video-kit-auditor:"Changes since last audit: <list / CHANGELOG draft>. Run the full audit."
```

## Installing the agents
The source of truth is `video_tools/agents/*.md`. For the agents to be available in every project folder, copy them to the user-level folder `C:\Users\Flex\.claude\agents\`, either with `python agents/install.py` or by copying manually. Re-copy after editing them. A new Claude Code session is needed before new agent types appear.
