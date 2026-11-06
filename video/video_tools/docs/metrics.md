# Project metrics

Use these numbers to give the owner honest time estimates. The curator appends one block per project. Numbers come from task notifications and logs; never estimate them after the fact.

## 2026-10-03 · Magic Safari (zoo trip) · `C:\My_poject\video`
- **Footage:** 61 MOV (4K60 HEVC, ~7 min raw; 3 junk, 7 with rotation problems) + 53 HEIC photos (29 with edited versions).
- **Film:** 1:43 (103.37 s), 1080x1920, 32 shots (23 video segments, 8 photos, 1 slate). Earlier versions: v1/v2 41/40 items at 2:07, and v3 after the critique.
- **Wall time:** start ≈ 18:30 (earliest artifact 18:33) → first preview ~20:33 (~2 h 03 min) → final master 21:30 (~3 h), exports until 22:18. Owner involvement: 4 question rounds and 1 preview watch.
- **Agent totals:** ≈520 agent-minutes (≈400 without the one-time engine build), ≈2.96 M tokens (≈2.45 M without the engine build).
- **Renders:** 6 previews (~2–3 min each, half-res); final full-res 8.5 min (items 4 min + assembly 4 min); re-assembly with cache 5.7 min.
- **QA findings (on v2):** visual 2 HIGH / 11 MED / 13 LOW · audio 2 HIGH / 1 MED / 1 LOW · motion 1 FAIL / 2 WARN · critic 6/10.

| Agent | Role | Duration | Tokens | Tool uses | Note |
|---|---|---|---|---|---|
| Ko'ruvchi 1 | review 21 clips | 17.8 min | 170k | 70 | |
| Ko'ruvchi 2 | review 25 clips | 16.0 min | 171k | 76 | |
| Ko'ruvchi 3 | review 15 clips | 18.2 min | 180k | 72 | |
| Fotograf | 82 HEIC → 53 JPG + review | 33.4 min | 193k | 107 | |
| Texnik | proxies + audio + shake | 86.4 min | 255k | 135 | proxies barely used; disk pressure |
| Musiqachi | 12 candidates → plan + bed | 66.9 min | 224k | 65 | + 2 short follow-ups (~2 min each) |
| Montaj muhandisi | engine build + tests | 119 min | 506k | 179 | one-time; now reusable |
| Kadrlash A | reframe 16 items | 47.4 min | 208k | 149 | |
| Kadrlash B | reframe 26 items | 47.0 min | 236k | 164 | |
| QA Ko'rinish | visual QC | 17.9 min | 251k | 132 | |
| QA Ovoz | audio QA | 17.4 min | 178k | 54 | |
| QA Harakat | motion QA | 27.2 min | 287k | 71 | |
| QA Tomoshabin | fresh-eyes critic | 5.1 min | 101k | 23 | highest value per minute |
| Yakuniy nazoratchi | final QC | stopped | — | — | owner judged it herself |
| Siqish A / B | exports with VMAF search | ~35 min, stopped | — | — | only the 45 MB H.264 was needed (VMAF 91.6) |

- **Post-delivery change (v3.1):** the owner removed one photo shot. Rebuild + render of 4 changed items with 27 cached took 5.7 min; the instagram45 2-pass veryslow export took ~13 min (pass 1 ~5 min, pass 2 ~8 min) → 45.6 MB.

## 2026-10-03/04 · Kit build (video_tools v0.1)
| Agent | Role | Duration | Tokens | Tool uses | Note |
|---|---|---|---|---|---|
| Asbobsoz | extract engine + 12 tools + selftest | 63.4 min | 420k | 139 | selftest 17/17 PASS (~4 min) |
| Manager | docs, templates, agents, learning loop | ~40 min | — | — | |

## 2026-10-05/06 · Kuzgi sayr (Japanese garden + TV tower) · `C:\My_poject\video\_yapon` · FAST MODE (kit v0.1)
- **Footage:** 22 MOV (194.8 s, 4K60 HEVC, 13 landscape / 9 portrait) + 31 HEIC (1 edited pair, 16 front-camera) + 1 AAE.
- **Films:** short cut 43.567 s (12 items: 8 video, 4 photo). Memory cut 1:28.700 (27 items: 17 video, 10 photo incl. end card). EDL iterations: k1 14 items 57.3 s → k2 12 items 43.6 s → k90 27 items 88.7 s.
- **Wall time:** raw copied 22:16–22:20 → first preview 23:09 (**51 min**) → first master 23:32 (**74 min**) → 19.06 MB export handed over 23:35. Owner feedback ("juda qisqa") → memory-cut export 00:00 (**25 min**).
- **Agent totals:** ≈125 agent-minutes, ≈1.37–1.39 M tokens (resumes reported 856–877 k of this; whether that figure is incremental or cumulative can't be verified).
- **Renders:** 1 preview from 4K, no proxies: 57.3 s in 197 s (17.5 s film/min; items 153 s, audio 18 s, assembly 23 s). Short final 989 s, RAM-starved (~1 GB free): 2.6 s film/min, items 434 s, assembly + encode 530 s at 1.6–2.4 fps, 84.0 MB. Memory-cut final 445 s after the owner closed Word: 12.0 s film/min, ~11 fps.
- **Music:** Senbazuru (rubato ~81 BPM) → Fretless (100 BPM), two-track beds 57.32 / 44.62 / 89.82 s, no internal splices. Loudness out −13.86 / −13.91 LUFS, TP −2.64 / −2.76 dBTP.
- **Exports:** 19.06 MB (2.6 min); 38.4 MB = 3.46 Mbps. Disk free at final 3.23 → 2.73 GB.
- **QA findings:** critic 6.5/10 (4 fixes). final_check: short cut all PASS (jitter rms ≤ 0.061 px); memory cut 2 WARN (g12, t08), both false alarms. Found in the retro: range overruns in the memory cut (g18, g10, g06); the manager's recount on 2026-10-07 gave 9 video shots 0.01–0.9 s past their pick limits, fixed with strict caps + re-fill.
- **Owner verdict:** short cut "juda qisqa"; memory cut delivered, no further requests recorded.

| Agent | Role | Duration | Tokens | Tool uses | Note |
|---|---|---|---|---|---|
| Bog' | garden reviewer-reframer, 37 inputs → 18 picks | 34.8 min | 176k | — | + resume 6.9 min / 232k (memory-cut picks) |
| Minora | tower reviewer-reframer, 16 inputs → 10 picks | 35.6 min | 133k | — | + resume 4.7 min / 165k |
| Musiqachi | catalogue → two-track beds | 38.3 min | 149k | — | + 3 resumes ~1 min / 153–160k each (inbox said 2; the manager's brief says 3) |
| Tomoshabin | fresh-eyes critic | 1.8 min | 59k | — | 4 fixes; highest value per minute |
