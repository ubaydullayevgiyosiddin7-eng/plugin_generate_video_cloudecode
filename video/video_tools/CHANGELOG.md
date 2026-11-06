# Changelog

## 2026-10-07 · v0.2: fast mode by default (from the Magic Safari + Kuzgi sayr retro)
Retro: `retro/2026-10-07_magic_safari+kuzgi_sayr.md`. Tool/engine items were implemented by the toolsmith in parallel; their details are in `tools/README.md` and `engine/README.md`, subject to the audit.
### Added
- `tools/picks_check.py`: material budget per section + repetition flags, run before the music length is briefed (R9).
- `tools/edl_builder.py` auto layout from picks + music plan: durations capped by each pick's `in`/`out`, cuts on beats or measured bars, range table, shortfall report instead of stretching, drop/insert that keeps later cuts (R3).
- `engine/render.py` RAM pre-flight: logs free RAM and warns when it is low (R4).
- `tools/music_bed.py` multi-part (two-track, scene-change) beds with an end-anchored entry bar (R10); `tools/music_beats.py` rubato detection with measured bar lines (R11).
- `tools/contact_sheet.py` film-timeline mode (R13); `tools/reframe_preview.py` picks mode `--picks` (R14); `tools/export.py --mbps` (R23).
- Template **1b Ko'ruvchi-kadrlovchi** (fast mode, one per location) with a fixed picks schema, hard `in`/`out` limits, UPRIGHT-frame keys, mandatory repetition self-check, "decide, don't defer" (R2). `examples/kuzgi_sayr/` + README with a warning about the `build_kuzgi90.py` range-overrun bug (R2).
- `docs/lessons.md` new section "Agents and cost": fast-mode cost, critic value, expensive resumes → run mechanical steps as plain code (R20, R1).
### Changed
- **Fast mode (Tez rejim) is the default workflow**; the full QA team (Puxta rejim) only on request, for films > ~3 min, or public releases. Preview from 4K (`--preview --no-proxy --hwaccel d3d11va`), no proxies; manager ~1 s contact sheet + 1 critic, preview sent to the owner at the same time; critic always writes `viewer_report.md` (R1, R16).
- Phase 0 asks who the film is for; personal trip films default to the ~1:30 memory cut with an optional Reels cut (R7).
- Repetition rule: no near-identical shots, never the same place back-to-back; 1–2 different shots per place in a memory cut, 1 in Reels (R8).
- Music length is decided after the material budget; Musiqachi delivers a recipe + one draft bed; multi-location = one track per location joined at the scene change; rubato tracks cut on measured bars; 4-bar lines allowed for entries/exits; slow tracks fine for calm sections (R18, R1).
- `engine/render.py` cache defaults to `<EDL folder>/cache` instead of the kit (R6); `final_check` judges photo motion against the planned path (R12); engine key-cover warnings summarised (R24).
- Owner preferences in `CLAUDE.md` (confirmed by delegation 2026-10-07): fast mode default, memory cut default, posed static portraits ≤ ~1.5 s mid-film; stated: no on-screen music credit (R17, R25).
- `CLAUDE.md` hard rules: check free RAM before every final render (< 2.5 GB → ask to close Chrome/Word); never push `\n`-containing string edits through bash heredocs/sed, use the Edit tool; a video shot never runs past its reviewed in/out (R5, R3).
### Fixed
- Lesson and rule for the KS memory-cut defect: the auto layout v1 stretched 9 video shots 0.01–0.9 s past their pick limits (visible whip blur, blurred spin, empty tail); fixed with strict caps + re-fill; long cuts now get a ~1 s sheet check (R3, R13).
- Reframer template no longer implies that music may extend shots past their limits (R2, R24).
### Docs
- `docs/lessons.md`: rotation, mirroring, hflip, zoompan, budget, critic and export lessons marked "confirmed: kuzgi_sayr"; RAM and render-time rules (final ≈ film length × 5, preview from 4K ≈ × 3.5, export times) (R5, R16, R19); end slate = title + date (+ places), credit in the caption (R17).
- `docs/workflow.md` rewritten: two modes, phases 0–6, late-change procedure, cleanup offer with exact items and sizes (R1, R7, R17, R21), Kuzgi timing reference.
- `docs/metrics.md`: Kuzgi sayr block + agent table; MS start ≈ 18:30 and agent/token totals (R22).
- `docs/backlog.md`: promoted/closed items ticked; 6 new ideas from the retro. `inbox.md`: all 15 processed entries removed; 1 open question added. `README.md` (Uzbek): new defaults.

## 2026-10-03 · v0.1: initial kit (from Magic Safari)
### Added
- `engine/`: EDL → film render engine (subpixel crop/box framing with keys, speed ramps, rotate/hflip/tilt, stabilisation, grade presets, animated titles, music bed with `duck_window`, two-pass loudnorm), extracted from the Magic Safari project. Source folders are resolved from CLI flags, then the EDL `paths` block, then `VT_*` env vars, then defaults relative to the EDL (no hard-coded project paths). Synthetic test media + a self-contained test EDL. 29 fonts with licence notes.
- `tools/` (12): probe_media, heic_convert, make_proxies, contact_sheet, music_beats, music_bed, edl_builder, reframe_preview, measure_motion, final_check, export (`instagram45` reproduces the Magic Safari Instagram settings 54/54; `small20`, `high100`, `hevc45`), selftest (17 checks, ~4 min, all PASS). Verified on the original footage: probe matches the old pipeline, heic_convert is pixel-identical, music_bed reproduces the tight bed within 2 LSB.
### Fixed
- The engine no longer crashes when printing Uzbek text on a cp1252 console.
- Beat-tracker phase bias (was 20–45 ms early, now within ±7 ms).
### Known limitations
- Automatic downbeats are often one beat off. Verify, or pass `--downbeat`.
- `reframe_preview` doesn't simulate stabilisation or the grade. HDR clips are treated as SDR.
- Old Magic Safari EDLs have no `paths` block, so render them with `--video-dir`/`--photo-dir`.
- `docs/`: workflow, lessons, learning_loop, metrics, backlog. `templates/agent_prompts.md` (10 production roles).
- `agents/`: knowledge team: video-retro, video-toolsmith, video-curator, video-kit-auditor.
- `inbox.md`, `examples/magic_safari/`.
