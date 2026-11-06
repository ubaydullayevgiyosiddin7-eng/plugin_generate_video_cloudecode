# Workflow: raw phone footage → finished vertical film

Claude acts as the **manager**. Judgement work goes to background agents; Claude reviews their output, decides, keeps the owner informed in short Uzbek updates, and says which steps are plain code ("bu oddiy kod, agent emas"). Prompts: `templates/agent_prompts.md`. Tools: `tools/`, `engine/`. Facts behind each rule: `docs/lessons.md`.

## Two modes
- **Tez rejim (fast mode) is the default** (owner delegated the choice; decided 2026-10-07). One merged Ko'ruvchi-kadrlovchi per location and the Musiqachi run in parallel; no Texnik, no proxies; preview straight from 4K; QA = the manager's contact-sheet check + 1 fresh-eyes critic, and the owner gets the preview at the same time as the critic.
- **Puxta rejim (full pipeline):** Texnik (+ proxies), separate reviewers + Fotograf, 2 reframers, the visual/audio/motion QA team, an optional final-QC agent. Only on request, for films over ~3 min, public/monetised releases, or the first film after engine changes.

Project layout:
```
<project>/
  <raw folder>/          # owner's footage — READ-ONLY, never modify
  _ish/                  # work: reports/, photos/, <location>/, music/, edl/ (render cache lands next to the EDL), qa/
  <Title>.mp4            # master
  <Title>_<N>MB.mp4      # one sharing export
```

## Phase 0: intake (manager, ~5 min)
1. `python tools/probe_media.py <raw>`: counts, durations, rotation tags, portrait/landscape split, junk (< 1 s clips, .AAE). Convert photos with `python tools/heic_convert.py <raw> _ish/photos`.
2. Check free disk (`df -h /c`; clean up early if < 5 GB) and free RAM.
3. Ask the owner (one AskUserQuestion, max 4 questions, recommended option first):
   - **"Bu video kim uchun?"** (A) o'zingiz uchun xotira, 1:15–1:45, har joydan 1–2 kadr [tavsiya] · (B) Reels 30–60 s · (C) ikkalasi (bir xil tanlovdan)
   - format (9:16 phone vs 16:9), music (own mp3 / Claude finds licensed music / natural sound), title text.
4. Write the brief (purpose, cut type, length range, format, music, title) into memory and into **every** agent prompt.

## Phase 1: picks + music (background agents in parallel, ~35 min)
| Agent | Mode | Job | Output |
|---|---|---|---|
| Ko'ruvchi-kadrlovchi (1 per location) | Tez | review the videos + photos of one location, choose picks in story order, frame them, verify every pick with a `reframe_preview` strip, self-check repetition (template 1b) | `<location>/picks_<location>.json` |
| Musiqachi | both | licensed candidates → analysis → recipe (sections, joins, final accent) + one draft bed. The final length is set in Phase 2 | `music/music_plan*.json`, `music_bed*.wav` |
| Texnik | Puxta | proxies (films > ~3 min only), loudness/silence/wind, shake profile, junk | `reports/texnik.json` |
| Ko'ruvchi 1..N | Puxta | ~20 clips each (template 1) | `reports/review_gN.json` |
| Fotograf | Puxta | HEIC pairs, review, burst groups, Ken Burns focus | `reports/photos.json` |

## Phase 2: budget, story and music length (manager, ~5–10 min)
1. **Material budget first.** `python tools/picks_check.py` (added 2026-10-07) sums `dur_suggest` and the maximum usable seconds per section and flags repetition: same source with overlapping or near ranges, too many picks per place, the same place/setup adjacent. Fix repetition now, not after the critic.
2. Set section lengths from the budget (memory cut 1:15–1:45 if the material allows; never pad with weak shots), then brief the music length. Multi-location: one track per location joined at the scene change, length from the last track's entry bar (lessons → Music). Re-render beds yourself with `tools/music_bed.py` (plain code); don't resume the Musiqachi for a length change.
3. Puxta only: write `shotlist.json` (id, src, rotate/hflip, window, use, speed, intent).

## Phase 3: reframing (Puxta only, 2 background agents, ~45 min)
Kadrlash A/B (template 5) → `reports/reframe_A.json`, `reframe_B.json`. In fast mode this was done in Phase 1.

## Phase 4: EDL + preview + checks (manager, ~10 min per iteration)
1. Build the EDL with `tools/edl_builder.py`. Auto layout from picks + music plan (added 2026-10-07): durations start from `dur_suggest`, are capped by each pick's `in`/`out` (or `ext_in`/`ext_out`) ÷ speed, cuts snap to beats or measured bars, a range table (used vs limits, highlight inside) is printed, and a section shortfall is reported instead of stretched. **A video item never runs past its pick limits**: fill a shortfall with more picks, photos or a shorter section.
2. `python engine/render.py edl.json --timeline`: ranges, cut points, total.
3. Preview from the 4K sources: `python engine/render.py edl.json --preview --no-proxy --hwaccel d3d11va` (≈ 17.5 s of film per min; 57 s in 3.3 min).
4. Manager check: a contact sheet of the whole film at ~1 frame/s labelled with film time + item id (`contact_sheet` timeline mode, added 2026-10-07), plus the first and last frames of every item. A 2.5 s sheet missed sub-second blur at cuts. Do this for every new cut, including re-cuts after owner feedback.
5. At the same time: send the owner the preview link **and** launch 1 fresh-eyes critic (template 9; ~2–5 min; writes `viewer_report.md`).
6. Write the fixes into the picks (drops *and* trims, e.g. the hook length), rebuild, re-preview (unchanged items come from the cache).

## Phase 5: QA team (Puxta only, background agents in parallel, ~15–25 min)
| Agent | Checks |
|---|---|
| QA Ko'rinish (visual) | every item: subject framed at its moment, uprightness, mirrored text, empty stretches > 0.7 s, blur at cut boundaries, text legibility and safe zones, transitions, colour jumps |
| QA Ovoz (audio) | LUFS/TP, music sync and joins, clicks at cuts, ducking only where audible, cut-to-beat offsets |
| QA Harakat (motion) | analytic camera-path audit (kinks, clamps, whip pans), photo jitter on full-res renders, ramp ghosting |
| QA Tomoshabin (fresh eyes) | hook, story, **repetition**, pacing, selfie fatigue, ending. Prioritised top-5 |

Claude merges the findings and fixes the EDL (rebuild → preview → spot-check the fixed shots).

## Phase 6: final + delivery
1. Pre-flight: free disk ≥ the peak need in the log (delete proxies and old preview caches) and **free RAM ≥ 2.5 GB**; otherwise ask the owner to close Chrome/Word (`render.py` warns, added 2026-10-07).
2. Full render from the 4K sources: minutes ≈ film minutes × 5 (1:30 → ~7.5 min).
3. `python tools/final_check.py <film> <edl>`: format, loudness, photo motion against the planned path.
4. One sharing export, H.264 at ~3.45 Mbps: `tools/export.py --preset instagram45` with `--mbps` (added 2026-10-07; before that, `--target-mb` ≈ film seconds × 0.43). No multi-variant search. Puxta or on request: an independent final-QC agent; otherwise the owner judges the file herself.
5. Give the owner: the file links and the caption text with the music credit (no credit on screen; the end slate is title + date (+ places)).
6. Cleanup offer listing exact items and sizes (KS: work folder 497 MB, render caches 545 MB, scratchpad 103 MB): the work folder; each EDL's cache via `python engine/render.py <edl> --clean-cache` (full + preview); bulky scratchpad files (thumbnail `.npz`, test PNGs). Keep the masters and copy the small JSON/py files to `examples/<project>/`.
7. Run the learning loop (`docs/learning_loop.md`).

## Late changes after delivery
- More or fewer shots (e.g. "juda qisqa"): resume the location agents only for new picks (judgement, 5–7 min); re-run the budget, bed, layout, render and export yourself (plain code). KS: owner feedback → memory-cut export in 25 min.
- Removing one shot: give its time to the neighbours so later cut times and cached items stay (the `edl_builder` auto layout's drop/insert, added 2026-10-07). MS v3.1 did this by hand and re-rendered 4 of 31 items.

## Timing reference
| Step | Fast mode (KS: 22 MOV + 31 HEIC → 1:29) | Full pipeline (MS: 61 MOV + 53 HEIC → 1:43) |
|---|---|---|
| Picks / analysis + reframing | ~35 min in parallel, music alongside | ~30 min + ~45 min |
| Start → first preview | 51 min | ~2 h |
| Start → first master | 74 min | ~3 h |
| Preview | 3.3 min for 57 s (4K) | 1.2–3.5 min each (proxies) |
| QA | critic 1.8 min | ~25 min |
| Final render | 7.4 min for 1:29 (RAM free); 16.5 min for 0:44 (RAM-starved) | 8.5 min |
| Sharing export | 2.6 min (0:44) | ~14 min (2-pass veryslow) |
| Owner feedback → re-cut export | 25 min | — |
