# Backlog: improvement ideas not yet approved

The retro agent proposes items; the curator records them here. The manager promotes an item to approved work by giving it to the toolsmith or curator. Format: `- [ ] <idea> — why (evidence) · size S/M/L`. Promoted or finished items are ticked with the date and retro id.

## From Magic Safari (2026-10-03)
- [x] **Repetition checker** — promoted 2026-10-07 → `tools/picks_check.py` (R9).
- [x] **Material budget calculator** — promoted 2026-10-07 → `tools/picks_check.py` (R9).
- [ ] **Auto subject tracking for reframing**: face detection (OpenCV DNN) plus saliency/animal detection proposes keys, and the reframers only verify and adjust. Why: reframing took 2 × 47 min; many keys were simple "face → animal" pans. · L
- [ ] **Sideways/upside-down detector**: per-segment orientation check (face/horizon/text detection on sampled frames) to catch content rotation the tag doesn't reflect. Why: MS 7 of 61 clips and KS 2 of 22, found only by the reviewers. · M
- [ ] **Mirrored-text detector**: OCR on sampled frames, flagging text that reads better flipped. Why: the s03 "Spirit of Australia" plate reached QA as a HIGH. · M
- [ ] **Audible-reaction detector**: an envelope + spectral voice/laugh detector that proposes a `duck_window` and nat_sound only where audible. Why: 2 of 3 "laugh" clips were silent; whole-item ducking caused a 6.9 LU hole. · S
- [ ] **Synthetic motion blur on fast pans** (engine): directional blur proportional to per-frame window velocity above ~40 px/frame. Why: motion QA WARN on whip pans of 88–104 px/frame. · M
- [x] **Skip proxies by default** — done 2026-10-07 (R16): previews from 4K with `--preview --no-proxy --hwaccel d3d11va` (KS 57 s in 3.3 min); proxies only for films > ~3 min.
- [x] **Quick export preset** — promoted 2026-10-07 → `export.py --mbps` (R23).
- [x] **Disk pre-flight** — promoted 2026-10-07 → RAM pre-flight in `render.py` (R4) + cache next to the EDL (R6). Per-phase disk estimates and auto-clean are still open.
- [ ] **16:9 version from the same EDL**: auto-derive landscape frames (mostly full-frame, with box→full) for the owner's YouTube channel. Why: the owner mentioned her channel. · M
- [x] **"Quick QC" mode** — covered 2026-10-07 by fast mode (R1): manager contact sheet + 1 critic + `final_check`.

## From Magic Safari + Kuzgi sayr retro (2026-10-07)
- [ ] **Two cuts from one picks set**: memory cut plus an automatic Reels cut (top-rated subset, 1 per place) from the same picks and music recipe. Why: the KS short and long cuts were built by hand twice. · M
- [ ] **Shot-boundary blur detector**: optical-flow magnitude or Laplacian variance over the first and last 0.5 s of each item, flagging whip blur at cuts. Why: the KS g18/g10 blurred starts passed every check. · S
- [ ] **Picks JSON schema + validator** shared by reviewers, builder and checks. Why: schema drift between the two KS picks files (photo `in`/`out` numbers vs null; `screen_time_s` vs `total_screen_time_s`). · S
- [ ] **Face-time / selfie-ratio meter** per section. Why: the MS critic counted ~40 % face time by hand; KS has ≈15 of 27 items with her face. · M
- [ ] **Scratchpad hygiene helper**: agents write 14 MB PNGs and a 54 MB npz into the shared scratchpad; auto-clean at phase end. Why: KS left 103 MB in the scratchpad on a 98 % full disk. · S
- [ ] **Music catalogue cache + candidate screening** (`tools/music_catalog.py`, retro R15, not in the 2026-10-07 round): cached incompetech catalogue with feel/genre/BPM/length/no-vocals filters → `candidates.json` with attribution. Why: the same 881 KB catalogue was fetched and screening code written twice (MS 66.9 min, KS 38.3 min Musiqachi). · M
