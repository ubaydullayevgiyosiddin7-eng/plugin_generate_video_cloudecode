---
name: hackathon
description: Win a hackathon or competition build. Use when the user mentions a hackathon, xakaton, contest, competition, saralash, final, pitch to judges, or pastes a task with requirements and judging criteria. Turns the brief into a requirements table, plans to the judging weights, builds, verifies and prepares pitch and submission.
---

# Hackathon

The full playbook (rubrics, rules, timeline, pitch, checklist) is
`C:\My_poject\helpful_cloude\hackathon\PLAYBOOK.md`; templates are in `...\hackathon\templates\`. Read the playbook first.
Talk to the user in Uzbek unless they write otherwise.

1. **Decode the brief.** Convert task files with `markitdown` if needed. Ask the user once for anything missing: judging
   criteria and weights, deadline and timezone, submission format, required tech or sponsor APIs, team size and roles.
2. **SPEC.md** from `templates/SPEC.md`: one-line pitch, criteria with weights, a requirements table with EVERY explicit
   and implied requirement and its acceptance check, the 90-second demo script, what is out of scope. Show it to the
   user before building. Nothing gets built that the demo script doesn't need.
3. **Project setup:** copy `templates/CLAUDE.md` (fill in pitch, criteria, deadline) and `templates/settings.json` into
   the project's `.claude/`; copy `agents/spec-reviewer.md` into `.claude/agents/`. Adapt the stack lines if the brief
   requires another stack.
4. **Design:** website or landing → `design-taste-frontend` skill; app UI (dashboard, CRM, panel) → a `DESIGN.md` from
   awesome-design-md for a similar product. Simple, one system, professional.
5. **Build** one feature at a time in criterion-weight order; deploy early; keep features.json and PROGRESS.md current.
6. **Verify before every demo or submission:** `playwright-cli` at 390 / 768 / 1440 with 0 console errors, every button
   clicked; `web-design-guidelines`; then run the `spec-reviewer` agent and fix its top gaps. Claim "done" only with evidence.
7. **Pitch and submission** per the playbook sections 4–5: slides outline, demo script, Q&A prep, demo video (the
   `video/` kit can make it), README and the submission checklist.
8. **After the event** write `hackathon/cases/<date>-<name>.md` from `cases/TEMPLATE.md` with what worked and what didn't.
