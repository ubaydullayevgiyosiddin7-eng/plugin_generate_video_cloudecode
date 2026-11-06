# Lessons learned

Facts that cost real time, each with the rule to apply. Sources: **MS** = Magic Safari (zoo, 2026-10-03, full pipeline), **KS** = Kuzgi sayr (garden + TV tower, 2026-10-05/06, fast mode). Read before starting a new video.

## iPhone footage

- **Rotation tags lie about content.** ffmpeg autorotates by the tag (`-180`/`0` → landscape, `±90` → portrait), but the phone was sometimes turned *during* recording: MS 7 of 61 clips (IMG_4364, 4483, 4488 throughout; 4385, 4348, 4390, 4482 in part), KS 2 of 22 (IMG_4559 and 4565 tagged +90 with sideways content; 4559 also ~35° tilted). Reviewers must look at frames and report `rotate` fixes per segment; the engine applies an extra `rotate` (90 = clockwise) after autorotate. (confirmed: kuzgi_sayr)
- **Front-camera selfies are mirrored** ("Mirror Front Camera"), so text reads backwards. Videos: set `hflip: true` only where text matters (KS g06 "azimut" sign); viewers don't notice mirroring otherwise. `heic_convert` un-mirrors photos (KS: 16 front-camera HEIC). (confirmed: kuzgi_sayr)
- **Reframe keys are measured in the UPRIGHT frame after autorotate + rotate + hflip.** On MS IMG_4361 the keys already matched the flipped view, and mirroring them again (cx → 1−cx) reversed the pan. State this in every reframing prompt and verify with a strip; with the rule stated, KS g06 was right first time. (confirmed: kuzgi_sayr)
- **HEIC:** use `pillow-heif` because it handles tile grids, orientation and mirroring. `IMG_E####.HEIC` is the user's edited version. There it was always Portrait-mode blur plus a light tone change, and the blur sometimes smeared a bird's head, so compare against the original. `.AAE` sidecars are 0-byte junk. Convert Display P3 to sRGB.
- Clips under ~1 s are almost always accidental. Many clips end with the phone pointing at the ground or with a whip pan; reviewers must give hard usable limits.
- 4K60 HEVC sources make **clean 0.5× slow motion** (60→30 fps, one source frame per output frame). A 9:16 crop of a 4K landscape frame is 1215×2160, which downsamples nicely to 1080×1920. Always render finals from the 4K sources, never from 1080p proxies.

## Motion: the "trembling Ken Burns" problem (the owner's top complaint)

- **Never use ffmpeg `zoompan` for Ken Burns.** It steps in whole pixels: measured 0.28 px rms / 0.7 px max residual jitter, which the owner saw on an earlier Claude video. With subpixel warps KS photo jitter was rms ≤ 0.061 px and drew no complaint. (confirmed: kuzgi_sayr)
- Use subpixel affine warps: prescale with `INTER_AREA` to about the output size × max zoom, then `cv2.warpAffine` (bicubic) per frame. Measured 0.006–0.04 px.
- **A hard per-frame clamp causes a jolt.** If a key sits outside the valid window region (e.g. `cy=0.55` at `zoom=1.0`, where only 0.5 is valid), the clamp engages and then releases mid-move. The result is a velocity reversal of over 1 px/frame. Fix: project every key into its valid region before interpolating (`project_keys`). The engine also has a clamp→smooth safety.
- Interpolate keys with a monotone cubic (Fritsch–Carlson). Interpolate zoom in log space.
- **Speeds that aren't exact frame ratios ghost.** 0.8× or 0.75× on a 60 fps source makes the engine blend two frames, which gives double images and a 6 Hz judder (QA FAIL). Use 0.5×, 1×, 2× (or 2.5× = 5 source frames per output frame).
- **Whip pans step visibly.** Over about 90 px/frame with no motion blur looks bad. A pan should take ≥ 1.5 s of *output* time per frame width.
- **Measure, and judge against the planned path.** Measure photo items (static content) with `tools/measure_motion.py` / `final_check`; for video items analyse the planned camera path, because handheld motion dominates. A plain smoothing residual false-alarms on fast designed moves (KS g12 rms 0.157 / max 0.78 px, t08 0.103 / 0.75 px vs limits 0.15 / 0.6, yet clean bell-shaped velocity 0 → 20.6 → 0 px/frame) and on animated text/sparkles (MS end slate). `final_check` compares photo motion against the engine's planned path (added 2026-10-07); on any remaining WARN, check per-frame velocity for sign flips before changing keys.

## Vertical (9:16) reframing of 16:9 selfies

- A 9:16 crop shows only 31.6 % of a 16:9 frame. Her face and the animal often don't fit together.
- Options, in order: (1) a full-bleed crop with a *motivated* pan (hold on the face, ease to the subject at its moment); (2) a "box" layout (4:5 / 1:1 / 4:3 window over a blurred copy of the same frame) for must-see-together moments such as a wingspan next to a face, or group photos. Too many boxes look inconsistent: the MS critic flagged 7; KS used 2 of 27.
- A reframer must render "what the viewer sees" strips at several times and look at them. The highlight moment must be framed (ostrich beak, ball dropping into the bin…).
- Reels safe zones: avoid the top ~12–14 % and bottom ~22 % for faces and text; keep 6 % side margins.

## Selection, editing and story

- **Ask who the film is for before choosing a length.** Personal trip film → default **memory cut ~1:30** (1:15–1:45); a Reels cut (30–60 s) is only an optional extra from the same picks. KS: the 43.6 s cut was "juda qisqa … xotira" and was superseded 25 min later, after a 16.5-min final render and an extra music round. (owner decision, confirmed by delegation 2026-10-07)
- **Repetition: no near-identical shots, and never the same place back-to-back.** Same viewpoint/framing/setup = duplicate; drop it even if it's good. Memory cut: 1–2 *different* shots per place are fine (owner, stated 2026-10-06); Reels: 1 per place. Repetition was the critic's top finding in both films (MS crane ×4, macaw ×6; KS t05/t06 the same window view, 3 similar face close-ups, two storks adjacent), so reviewers self-check and decide instead of deferring to the critic. (confirmed: kuzgi_sayr)
- **Posed static portrait photos mid-film: at most ~1.5 s**; they are fine as an end-card background. MS: the owner removed a 3 s posed portrait (i03) after delivery, which cost a re-render and a re-export. (owner decision, confirmed by delegation 2026-10-07)
- **Hook:** the first 1–3 s must show the best moment, and the hook shot stays ≤ ~3 s (KS critic: 5.07 → 3.1 s). Open on the signature shot (crane wingspan, slow-mo) under the title, not on an empty path. Write every critic fix (trims as well as drops) into the picks, so later cuts inherit it; the KS memory cut re-used a 5.37 s hook.
- **Selfie fatigue:** about 10 MS clips used the same "animal → swing to her face" move. Keep her face for reactions.
- **The material budget sets the length; check it before briefing the music length.** Sum `dur_suggest` and the maximum usable seconds per section first (`tools/picks_check.py`, added 2026-10-07). MS: 2:26 music → 2:07 → 1:43 (~83 s of unique material); KS: a 57 s bed became a 43.6 s film, then 50.1 s of garden picks met a 56.36 s garden section. (confirmed: kuzgi_sayr, 3rd occurrence)
- **A video shot never runs past its reviewed `in`/`out`.** The KS auto layout v1 stretched 9 video shots 0.01–0.9 s past their pick limits to fill the music, which put whip blur (g18, ~0.35 s), a blurred spin (g10, ~0.5 s) and an empty-lake tail (g06) into the delivered memory cut; fixed 2026-10-07 with strict caps and re-filling the remaining shots. Fill a shortfall with more picks, photos or a shorter section, never by stretching (the `edl_builder` auto layout caps at the limits, added 2026-10-07). Check every long cut at ~1 frame/s plus the shot boundaries: the 2.5 s overview sheet missed these defects.
- Cut on the music grid: the cut-list builder places every cut on a beat (100 BPM: beat 0.6 s, bar 2.4 s). Audio QA measured 0 ms error.
- Music structure drives the edit: cold open (title) → playful main (cuts every 1–2 bars) → gentle breakdown (slow-motion tender moments) → finale → end card. The final accent should land on the end slate.
- End card: about 5 s, not 12. A static boxed photo over full-energy music drags. A logo slate (title over a blurred background made from the top of a photo, no face ghost) bookends the opening title.

## Audio

- Clip audio from iPhone selfies is mostly wind. Apply a 120–200 Hz high-pass and keep clip ambience about 10 dB under the music.
- Only duck music where there is a *real audible* reaction. Measure the clip's envelope first: in 2 of 3 "laughing" clips the laugh was visible but silent. Duck with `duck_window` (a short window), not the whole item. Whole-item ducking made a 6.9 LU hole in a high-energy section.
- Slow-motion segments are muted. Don't duck the music over silence.
- Loudness target −14 LUFS integrated, true peak ≤ −1.5 dBTP (two-pass linear loudnorm; KS −13.9 LUFS / −2.8 dBTP). Set the music `fade_out` short (0.3 s) so the natural ring-out isn't cut.

## Music and licensing

- Kevin MacLeod / incompetech (CC BY 4.0) downloads work directly and are safe for YouTube and Instagram **with attribution**. **No credit on screen** (owner, stated 2026-10-03): the end slate is title + date (+ places), and the credit goes only in the post caption text that the owner always receives (confirmed: kuzgi_sayr):
  `"<Title>" Kevin MacLeod (incompetech.com) / Licensed under Creative Commons: By Attribution 4.0 License / http://creativecommons.org/licenses/by/4.0/`
- **Splices only on 8-bar phrase lines** (4-bar splices scored 0.5–0.6 similarity, which is audible). Score joins by bar similarity, chord match and onset correlation; an MS breakdown→finale join scored 0.78 timbre but 0.998 chords and sounded like a natural "drop into the last chorus". Track entries and exits (no splice) may use 4-bar lines.
- **Multi-location films: one track per location, joined at the scene change.** Track A fades into its phrase-end breath; track B enters on a downbeat exactly at the cut and plays unedited to its natural ending. Change the length with the end-anchored entry bar of the last track, not with splices (KS Senbazuru → Fretless: 44.62 / 57.32 / 89.82 s beds, no splices). `music_bed` builds this from a multi-part spec (added 2026-10-07).
- **Rubato (live) tracks: cut on measured bars, not a constant grid.** A constant 81.211 BPM grid missed Senbazuru's bar starts by 0.24–0.92 s (bars 2.67–3.32 s). `music_beats` flags rubato tracks and reports measured bar lines (added 2026-10-07).
- No vocals. 100–130 BPM with a clean ending suits energetic films; a slow track (KS 81-BPM koto) suits a calm scenic section.

## Machine limits (this PC)

- Only drive C:, nearly full; 7.6 GB RAM. Parallel 4K HEVC decodes grew the Windows pagefile to about 10 GB and hit "No space left on device". Run at most 2 heavy 4K jobs at once. Keep intermediates compact (CRF 12–14, never raw frames on disk). Delete proxies, frames and caches as soon as a phase is done. The engine aborts below 1 GB free disk. (confirmed: kuzgi_sayr)
- **Free RAM matters as much as free disk.** With ~1 GB RAM free (Chrome and Word open) the KS 43.6 s final took 16.5 min: 2.6 s of film per min, items 4–10× slower, assembly 1.6–2.4 fps. After the owner closed Word, 88.7 s took 7.4 min (~11 fps). Before every final render check free disk *and* RAM; below 2.5 GB free RAM ask the owner to close Chrome/Word. `render.py` logs free RAM and warns when it is low (added 2026-10-07).
- **Render times with RAM free:** final from 4K ≈ 12 s of film per min (MS 12.2, KS 12.0), so minutes ≈ film minutes × 5 (1:30 → ~7.5 min). Preview from 4K with `--preview --no-proxy --hwaccel d3d11va` ≈ 17.5 s of film per min (57.3 s in 197 s), so minutes ≈ film minutes × 3.5. Re-assembly with cached items ≈ 5.7 min for 1:43.
- **Proxies only for long films (> ~3 min).** Previews from the 4K sources are fast enough; the MS Texnik spent 86 min and ~1.5 GB of disk on proxies that were barely used. (confirmed: kuzgi_sayr)
- **Render caches belong next to the EDL** (`<EDL folder>/cache`, the default since 2026-10-07). KS builders without `paths.cache` left 545 MB inside the kit. Free each EDL's cache with `python engine/render.py <edl> --clean-cache` when the project ends.
- When an agent is stopped, its ffmpeg children keep running. Find and kill them.

## Agents and cost

- **Fast mode costs about a quarter of the full pipeline.** KS: ≈125 agent-min / ≈1.4 M tokens, first preview at 51 min, master at 74 min. MS full pipeline: ≈520 agent-min / ≈3.0 M tokens, ~2 h to the first preview. A merged reviewer-reframer took ~35 min per location (MS: review 17 min + reframe 47 min in sequence).
- **The fresh-eyes critic has the best value per minute** (MS 5.1 min → 6/10 with a top-5 fix list; KS 1.8 min / 59k tokens → 6.5/10 and 4 fixes). Always run one, and it must write `viewer_report.md`: the KS critic's findings survived only as code comments. (confirmed: kuzgi_sayr)
- **Resumes are expensive:** 153–232k tokens for 1–7-min jobs (KS Bog' 232k / 6.9 min, Minora 165k / 4.7 min, Musiqachi 3 × 153–160k for ~1-min re-renders). Resume agents only for judgement work (new picks); run mechanical steps (bed length, EDL rebuild, render, export) yourself and tell the owner in one line "bu oddiy kod, agent emas" (she asked "agent ishlamayaptimi?").

## Delivery

- Master: H.264 CRF 17, about 20 Mbps (263 MB for 1:43).
- **One sharing export is enough: H.264 at ~3.45 Mbps** (MS 45.6 MB / 103 s = 3.53 Mbps, VMAF 91.6; KS 38.4 MB / 88.7 s = 3.46 Mbps). The owner is happy with ~45–50 MB and needs no 100 MB / 20 MB / HEVC variants. Times: KS 43.6 s → 19 MB in 2.6 min; MS 103 s 2-pass veryslow ~14 min. `export.py --mbps` sizes the file from the film length (added 2026-10-07). (confirmed: kuzgi_sayr)
- Size-targeted multi-variant searches with VMAF on every variant took 30+ min with two agents and were stopped. One well-chosen preset is enough; use VMAF `n_subsample` for speed.
- The owner judges the film herself and wants files early: hand over as soon as it's watchable (her KS length feedback came within minutes of the export), then keep polishing. (confirmed: kuzgi_sayr)
