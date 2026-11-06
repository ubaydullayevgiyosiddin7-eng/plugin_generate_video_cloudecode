# Project
<One-line pitch>. Judges care about: <the 3 highest-weighted criteria, with weights>. Deadline: <date/time, timezone>.
Requirements and acceptance criteria: SPEC.md. Progress: features.json (each item: id, description, steps, passes:false).

# Stack (decided, don't swap)
Next.js (App Router, TS strict) + Tailwind + shadcn/ui · Supabase (Postgres/Auth/Storage) · Vercel deploy · zod for all input.
No new dependency without one line saying why.

# Commands
- Install: pnpm install
- Dev: pnpm dev (if a server is already running, reuse its URL)
- Verify all: pnpm lint && pnpm tsc --noEmit && pnpm build
- UI check: playwright-cli screenshots at 390, 768 and 1440 wide; `playwright-cli console` must show 0 errors

# How we work
- First turn every requirement in SPEC.md into a features.json item with concrete acceptance steps. Highest-weighted
  criteria first.
- One feature at a time. Mark passes:true only after its steps pass in a real browser.
- Never edit or delete acceptance criteria or tests to make them pass.
- Commit after each green feature; update PROGRESS.md (done / next / known issues). Deploy early, redeploy often.
- Report "done" with evidence: commands run with output, screenshot paths. No evidence, not done.

# Product quality bar
- Every visible button and link does something real; no dead UI, no "TODO" or lorem ipsum on screen.
- Every async view has loading, empty and error states; errors reach the user (toast), never swallowed.
- Mobile-first: no horizontal scroll at 390px; tap targets >= 44px.
- Demo data looks real, is clearly demo data and lives in supabase/seed.sql, never hardcoded in components.
- One design system: shadcn components and theme tokens; no ad-hoc colors.
- Simple beats clever: fewer screens that all work over many that half work.

# Security
- Secrets only in .env.local (gitignored); keep .env.example up to date.
- Supabase: RLS on every table with policies before anything ships; service-role key server-only.
- Validate every server action / route with zod; check auth on every mutation.

# Gotchas
- <things corrected twice go here>
