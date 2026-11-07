---
name: hackathon
description: Win a hackathon or competition build. Use when the user mentions a hackathon, xakaton, contest, competition, saralash, final, pitch to judges, or pastes a task with requirements and judging criteria. Turns the brief into a requirements table, plans to the judging weights, builds, verifies and prepares pitch and submission.
---

# Hackathon

The full playbook (rubrics, rules, timeline, pitch, checklist) is
`C:\My_poject\helpful_cloude\hackathon\PLAYBOOK.md`; read it first. `...\hackathon\README.md` maps each stage to the
recommended tools in the other sections (`web\`, `documents\`, `video\`, `uzbek\`, `automation\`, `claude-code\`); the
overall map is `...\helpful_cloude\QOLLANMA.md`. These are recommendations: if the brief requires another stack, style or
format, the brief wins. Talk to the user in Uzbek unless they write otherwise.

1. **Decode the brief.** Convert task files with `markitdown` if needed. Ask the user once for anything missing: judging
   criteria and weights, deadline and timezone, submission format, required tech or sponsor APIs, team size and roles.
2. **SPEC.md** from `hackathon\templates\SPEC.md`: one-line pitch, criteria with weights, a requirements table with EVERY explicit
   and implied requirement and its acceptance check, the 90-second demo script, what is out of scope. Show it to the
   user before building. Nothing gets built that the demo script doesn't need.
3. **Project setup:** copy `helpful_cloude\web\templates\CLAUDE.md` to the project root (fill in pitch, criteria,
   deadline) and `web\templates\settings.json` into the project's `.claude/`. The agent team is already installed
   user-level (see "Agent team" below). Adapt the stack lines if the brief requires another stack.
4. **Design:** website or landing → `design-taste-frontend` skill; app UI (dashboard, CRM, panel) → a `DESIGN.md` from
   awesome-design-md for a similar product. Simple, one system, professional.
5. **Build** in criterion-weight order; deploy early; keep features.json and PROGRESS.md current. Independent features
   go to parallel `feature-builder`s (see below).
6. **Verify before every demo or submission:** `qa-tester` + `design-reviewer` + `spec-reviewer` in parallel, plus
   `web-design-guidelines`; fix their top gaps. Claim "done" only with evidence.
7. **Pitch and submission:** `pitch-writer` drafts `pitch/` (script, slides, Devpost, Q&A) per the playbook sections
   4–5; demo video with the `video/` kit; README and the submission checklist.
8. **After the event** write `hackathon/cases/<date>-<name>.md` from `cases/TEMPLATE.md` with what worked and what didn't.

## Agent team — you are the lead

You orchestrate; subagents do focused work in parallel and return short reports, so your context stays free for
decisions. Agents (user-level, in `~/.claude/agents/`): `hackathon-researcher`, `feature-builder`, `qa-tester`,
`spec-reviewer`, `design-reviewer`, `pitch-writer`.

| Stage | Run in parallel | You (lead) |
|---|---|---|
| Hour 0–2 | `hackathon-researcher` (problem numbers, competitors, sponsor APIs, judges) | decode brief, write SPEC.md + features.json, scaffold the repo, deploy the skeleton |
| Build | 2–4 `feature-builder`s, **each owning separate files** (or `isolation: worktree`); independent features only | shared files (layout, routes, types, schema), merging, deploy |
| After each deploy | `qa-tester` on the live URL | triage: fix demo blockers first |
| UI ready | `design-reviewer` | fix P0/P1 or hand to a builder |
| ~Hour 16 → | `pitch-writer` (from SPEC + PROGRESS) | feature freeze at ~75% of the time |
| Before demo / submit | `spec-reviewer` + `qa-tester` + `design-reviewer` together | fix top gaps, re-run until clean |

Rules for parallel work:
- **Split files, not just tasks.** Two agents never edit the same file. Shared files stay with you; builders list
  "needs from lead".
- Brief every agent fully: feature id + acceptance steps, files it owns, the URL, where SPEC/CLAUDE.md are. Agents do
  not see this conversation.
- Launch independent agents in one message so they run at once; keep working while they run; don't redo their work.
- Trust but verify: a builder's "done" needs its evidence (command output, screenshots); spot-check the riskiest one.
- Reviewers are read-only and report P0/P1/P2; you decide what gets fixed. Don't let review loops eat the clock:
  fix P0 always, P1 if time, P2 only after freeze polish.
- Keep features.json / PROGRESS.md current — every agent reads them.
- A big fan-out (many agents, scripted pipeline) is a Workflow; only use one if the user explicitly asks for it.
