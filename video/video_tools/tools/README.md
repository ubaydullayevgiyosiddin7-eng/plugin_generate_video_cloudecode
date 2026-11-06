# tools

Small CLI scripts around the render engine (`../engine`). Every tool has `--help`; none writes into
its input folders (except `reframe_preview --write-back`, on request); outputs default to the current
directory unless an output path is given.
Python 3.11 + `pip install -r ../requirements.txt`, ffmpeg/ffprobe on PATH.

| tool | what it does | example |
|---|---|---|
| `probe_media.py` | inventory a footage folder: per video duration/fps/size/rotation/orientation/audio/HDR + junk flags (< 1 s, decode errors); per photo format/size/IMG_E edit pair/front camera; .AAE junk; totals, portrait vs landscape -> table + JSON | `python tools/probe_media.py D:/footage --json probe.json` |
| `heic_convert.py` | iPhone HEIC -> upright sRGB JPG (edited IMG_E version by default, `--prefer original`; selfies un-mirrored, `--keep-mirror`; `--max-side`) + convert_meta.json | `python tools/heic_convert.py D:/footage D:/proj/photos` |
| `make_proxies.py` | OPTIONAL 1080p H.264 60 fps proxies for `render.py --preview` - only for long films (> ~3 min) or many previews; previews from the 4K sources (`--preview --no-proxy --hwaccel d3d11va`, ~17 s of film/min) are the default | `python tools/make_proxies.py D:/footage D:/proj/proxy` |
| `contact_sheet.py` | labelled frame grid of a clip (fps or count, timestamps, optional 0.1 coordinate grid / 9:16 outline); folder = batch. Films: `--timeline tl.json` labels "film time + item id" and pages at a fixed fps, `--cuts` = first + last 0.1 s of every item on one sheet (blur / empty tails at shot boundaries), `--at t1,t2` big zoom frames | `python tools/contact_sheet.py film.mp4 --timeline tl.json --cuts` |
| `picks_check.py` | BEFORE the music length is briefed: material budget per section (sum of dur_suggest and of max usable seconds, recommended phrase-line lengths, `--plan` comparison) + repetition flags (same take, > N per place, same place back to back, same place+setup, "both mention stork" hints); exit 1 on flags | `python tools/picks_check.py picks_bog.json picks_minora.json --bar 2.96 --phrase-bars 4` |
| `music_catalog.py` | incompetech (Kevin MacLeod, CC BY 4.0) catalogue cached outside the kit (`%LOCALAPPDATA%/video_tools/music`): `fetch`, `search` (feel / instruments / genre / text / BPM / length / `--no-vocals`), `get` (cached MP3 download), `scan` (LUFS, key, tempo, 8-s energy, sound end), `shortlist` (search + get + scan -> candidates.json with attribution text) | `python tools/music_catalog.py shortlist --feel calm --bpm 70-110 --min-len 60 --no-vocals --get 5 --out music --json candidates.json` |
| `music_beats.py` | BPM, beat grid, downbeats, phrase starts, energy curve, sections, final accent -> JSON in the music_plan format; splice scores (`--jump 8:17`, `--suggest-jumps 5`). Rubato / live tracks (constant grid misses by > 40 ms rms) get TRACKED onset-refined bar lines (`tempo_mode`, `bar_starts`; `--grid` forces) | `python tools/music_beats.py song.mp3 --bpm-hint 100 --suggest-jumps 5` |
| `music_bed.py` | render a re-edited music bed from a segment list (bar-line splices, 60 ms equal-power crossfades, peak-limited 24-bit WAV) + plan JSON with timeline beats; measured `bar_starts` for rubato tracks; multi-part spec `{"parts": [...]}` = one track per location joined at the scene change (merged plan with join / final accent); `--length S` = end-anchored entry bar for a target length (seconds, no agent); also re-renders a music_plan_*.json | `python tools/music_bed.py film_bed.json --out music_bed.wav --length 90` |
| `edl_builder.py` | library + CLI: beat-locked cut list -> engine EDL (transition overlaps split around beat-aligned cuts, speed_map fitting, photo key scaling, key projection, mirror/hflip, key tweaks, texts, music; writes `paths.cache: "cache"`). `--layout spec.json` / `--picks ... --plan ...`: AUTOMATIC layout of reviewer picks on the music grid - every shot inside the pick's in/out (or ext_*) counting transition overlaps, photo cap 4.6 s, per-pick `limits`, cuts on beats (half-beats only when needed), a section short of material is an ERROR (or `--stretch-photos`), range table, `--drop ID` / `--insert ID --after ID` re-lay only a small window so other items keep their cache | `python tools/edl_builder.py --layout layout.json --out film.json` |
| `reframe_preview.py` | what the 9:16 viewer sees: strip of an EDL item at N moments, rendered with the engine's own framing code, plus source frames with the window drawn; `--picks picks.json --id g06 [--dur D] [--write-back]` previews a pick without a scratch EDL | `python tools/reframe_preview.py --picks picks_bog.json --id g06 --video-dir D:/raw` |
| `measure_motion.py` | Ken Burns / pan jitter meter (feature tracking, residual vs smoothed motion), time range + ROI | `python tools/measure_motion.py film.mp4 --start 26.9 --end 30.4` |
| `final_check.py` | acceptance checks of a finished film vs its EDL: format, frame count, loudness, photo-item motion measured against the PLANNED camera path (fast designed pans no longer false-alarm; old residual shown as info); exit 1 on FAIL | `python tools/final_check.py film.mp4 film.json` |
| `export.py` | 2-pass delivery encodes: `share` (the owner's sharing file: instagram45 settings at 3.45 Mbit/s total, size follows the length), `instagram45` (exact Magic Safari IG settings), `small20` (720p), `high100`, `hevc45` (hvc1); `--mbps R` (size = length x rate, `--target-mb` caps), `--vmaf` | `python tools/export.py film.mp4 --preset share` |
| `selftest.py` | one-command smoke test of the whole kit on synthetic media (engine + every tool), PASS/FAIL per check, cleans up; exit 1 on failure | `python tools/selftest.py` |

`_vtlib.py` (locations, ffprobe, console safety) and `_picks.py` (picks schema: load/normalise, usable
limits, caps, placement of a shot inside its pick) are shared helper modules, not tools.

Typical order for a new film (fast mode): `probe_media` -> `heic_convert` -> reviewers write picks
(`contact_sheet`, `reframe_preview --picks`) -> `picks_check` (material budget + repetition) ->
`music_catalog` / `music_beats` / `music_bed` (length from the budget; `--length` to re-fit) ->
`edl_builder --layout` -> `engine/render.py --timeline` -> `render.py --preview --no-proxy --hwaccel d3d11va`
-> `contact_sheet --timeline --cuts` + critic -> `render.py` (>= 2.5 GB RAM free) -> `final_check`
-> `export --preset share`. `make_proxies` only for long films.
