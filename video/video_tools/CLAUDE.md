# video_tools: reusable kit for turning phone footage into finished films

Tools, templates and lessons from "Magic Safari" (zoo, 2026-10-03, full pipeline) and "Kuzgi sayr" (garden + TV tower, 2026-10-05/06, fast mode), both built in `C:\My_poject\video`. Start every new video project from here.

## Working with the owner
- Reply in **Uzbek** (Latin script), simply, without jargon dumps. She is a non-technical hobby creator.
- She wants Claude to act as a **manager AI**: split judgement work across background agents with distinct roles, report progress in short Uzbek updates, and say plainly what is agent work and what is plain code ("bu oddiy kod, agent emas").
- **Fast mode is the default** (confirmed by delegation, 2026-10-07). The full QA team only on request, for films over ~3 min, or public releases. See `docs/workflow.md`.
- **Personal trip films default to the memory cut (~1:30)**, with an optional short Reels cut (confirmed by delegation, 2026-10-07). Phase 0 asks who the film is for.
- She hates **repetition**: no near-identical shots (same viewpoint/framing/setup) and never the same place back-to-back. Memory cut: 1–2 different shots per place are fine (stated 2026-10-06); Reels: one per place.
- Posed static portrait photos mid-film: at most ~1.5 s; fine as an end-card background (confirmed by delegation, 2026-10-07).
- No music credit on screen (stated): the end slate is title + date (+ places); the credit goes in the caption text she gets.
- She likes being asked creative choices (purpose, format, length, music, title) with a recommended option.
- She judges the result herself. Send her the preview at the same time as the critic, and the finished file early; one sharing export (~45–50 MB) is enough. Don't over-polish slow steps while she waits.
- She once got a Claude video with **trembling Ken Burns zooms**. Motion smoothness must be measured, not assumed.

## How to run a new project
Follow `docs/workflow.md` (phases 0–6; fast mode by default). Read `docs/lessons.md` first: iPhone rotation/mirroring traps, jitter/clamp/ghosting fixes, selection rules, music, machine limits, agent costs. Agent prompts: `templates/agent_prompts.md`. Worked examples: `examples/magic_safari/` (full pipeline), `examples/kuzgi_sayr/` (fast mode, two-track music).

## Learning loop (keep the kit improving)
- During a project, append one line to `inbox.md` whenever something surprising happens (a new QA finding type, a bug, an owner correction, a workaround or a time sink).
- At the end of every project, or when the owner says "saboq ol", run the knowledge team per `docs/learning_loop.md`: `video-retro` → manager approves → `video-toolsmith` + `video-curator` (in parallel) → `video-kit-auditor`. The definitions are in `agents/`; install them with `python agents/install.py`. Record the agent durations and tokens from the task notifications for `docs/metrics.md`.

## Tools
- `engine/render.py`: EDL (JSON) → film. `--timeline` (dry run, beat check), `--preview --no-proxy --hwaccel d3d11va` (the standard half-res preview, straight from the 4K sources), `--only id1,id2`, `--jobs 2`, `--clean-cache`. Schema in `engine/README.md`.
- `tools/`: probe_media, heic_convert, make_proxies, contact_sheet, music_beats, music_bed, picks_check, edl_builder (auto layout from picks, added 2026-10-07), reframe_preview, measure_motion, final_check, export, selftest. See `tools/README.md` for flags and the typical order. Run `python tools/selftest.py` (~4 min) after any kit change.
- Engine source folders come from CLI flags (`--video-dir`, `--photo-dir`, `--proxy-dir`, `--music-dir`), then the EDL `paths` block, then `VT_*` env vars, then defaults relative to the EDL file. For a new project, put a `paths` block in the EDL.
- Setup: `pip install -r requirements.txt` (Python 3.11). ffmpeg 8 full build at `C:\ffmpeg-8.0-full_build\bin` (has libx264, libx265, libvmaf).

## Hard rules
- The owner's raw footage folder is **read-only**. Never move or modify it; delete it only when she explicitly asks and confirms in a question that names the folder and its size (and only after any planned re-render that needs it).
- C: is the only drive and it is nearly full; RAM is 7.6 GB. Check `df -h /c` before heavy steps. Run ≤ 2 heavy 4K jobs at once. Delete proxies, frames and caches as soon as a phase is done. Kill orphaned ffmpeg processes after stopping agents.
- **Before every final render check free RAM as well as disk.** Below 2.5 GB free RAM, ask the owner to close Chrome/Word (a RAM-starved final ran 4× slower).
- Final renders come from the 4K sources, never from proxies.
- **A video shot never runs past its reviewed in/out.** Check the material budget before briefing the music length; check every long cut with a ~1 s contact sheet.
- Never use ffmpeg `zoompan`. Keep frame keys inside their valid regions. Use only frame-exact speeds (0.5×, 1×, 2×).
- Music needs a license that allows YouTube and Instagram use. Credit CC BY music in the post caption, and always give the owner the caption text.
- **Never push string edits containing `\n` through bash heredocs or sed**: they become real newlines and broke a .py twice. Use the Edit tool.
- Don't copy the owner's photos, videos or music into this project. Example files here are small JSON/py only.
