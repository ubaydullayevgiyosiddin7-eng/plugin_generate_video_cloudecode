# Render engine

Turns an EDL (JSON) into the finished 9:16 film: H.264 High, yuv420p, BT.709 tags, CRF 17 `slow`,
constant 30 fps, AAC 256 kb/s 48 kHz, `+faststart`, loudness -14 LUFS / -1.5 dBTP.
Built for the "Magic Safari" film (iPhone 4K HEVC footage + HEIC photos -> Instagram Reel).

Needs Python 3.11, ffmpeg/ffprobe on PATH, `pip install -r ../requirements.txt`.

```
python render.py EDL.json --timeline [--timeline-json t.json]   # dry run: frame-accurate timeline
python render.py EDL.json                                       # full quality from the sources
python render.py EDL.json --preview --no-proxy --hwaccel d3d11va   # 540x960 preview straight from 4K (default use)
python render.py EDL.json --only s02,c01                        # re-render items -> <out>_<id>.mp4
python render.py EDL.json --clean-cache                         # delete this EDL's intermediates (new + old location)
```
Other flags: `--jobs N` (parallel item renders, default 2 - each 4K render needs ~1-1.3 GB RAM),
`--force`, `--grade natural|warm_pop|cinematic_soft|none`, `--out path`, `--keep-cache`,
`--consume-cache` (delete each intermediate right after the assembler used it),
`--hwaccel d3d11va` (GPU HEVC decode, bit-exact on the original laptop, frees CPU), `--interp lanczos`,
`--preview` (half size, fast encodes; uses proxies from `paths.proxy` only if they exist - otherwise it
logs a NOTE and decodes the 4K originals; `--no-proxy` forces the originals), and the folder overrides below.

Speed (i5-1335U, 8 GB): full quality ~12 s of film per minute of wall time with `--jobs 2` and >= 2.5 GB
RAM free (1:30 film ~7.5 min; a re-render after small edits only redoes changed items + the assembly);
`--preview` from the 4K sources ~17 s of film per minute (`--hwaccel d3d11va`), enough for films up to
~3 min - proxies (`../tools/make_proxies.py`) are optional, only worth it for longer films or many previews.
With 1 GB free RAM the same final ran 4-10x slower (43.6 s of film in 16.5 min).

RAM guard: after the disk line the engine logs the available RAM (Windows `GlobalMemoryStatusEx`).
Below 2.5 GB it WARNs ("close browsers/Word"); below 1.5 GB it renders with `--jobs 1`. If the final
assembly runs under 5 fps for a whole minute (normal ~11 fps) it WARNs once that the machine is swapping.
(`VT_RAM_GB_OVERRIDE=<GB>` fakes the free amount, for tests.)

## Where sources come from (`paths`)
Every source folder is resolved in this order (first hit wins):

| key | CLI flag | EDL `paths` key | env var | default (relative to the EDL file) |
|---|---|---|---|---|
| raw footage | `--video-dir` | `video` | `VT_VIDEO_DIR` | `.` |
| photos | `--photo-dir` | `photo` | `VT_PHOTO_DIR` | `photos` |
| preview proxies | `--proxy-dir` | `proxy` | `VT_PROXY_DIR` | `proxy` |
| music | `--music-dir` | `music` | `VT_MUSIC_DIR` | `.` |
| cache root | `--cache-root` (`--cache` = exact dir) | `cache` | `VT_CACHE_DIR` | `cache` (next to the EDL) |

Relative paths inside the EDL (`paths.*`, `output.path`, `music.path`) are relative to the EDL file;
CLI and env paths are relative to the current directory. Sources are looked up in their folder and
then next to the EDL. Photos may be given without extension match (`IMG_4353.jpg` finds
`IMG_4353.HEIC`). The cache gets one sub-folder per EDL name (`<root>/<edl name>[_preview]`), so it
lives in the project's work folder and goes away with it - never inside the kit (kit 0.1 defaulted to
`engine/cache`: 545 MB of one project's intermediates stayed in the kit). Backward compatible: if no root is
forced (`--cache-root` / `VT_CACHE_DIR`) and an old `engine/cache/<edl name>` folder with intermediates
exists while the new one doesn't, it is reused (NOTE in the log); `--clean-cache` removes both locations.
`tools/edl_builder.py` writes `"cache": "cache"` into every EDL it builds. `--timeline` prints the resolved
folders (`sources: ...`) and the disk line of a render shows the cache folder actually used.

## Tests and helpers (`test/`)
Run `python test/make_test_media.py` first: it synthesises the test inputs into `test/media/`
(landscape clip, portrait clip with an iPhone-style -90 deg rotation tag, a shaky clip, a 3024x4032
photo, a 75 s 100 BPM music bed, a 48 s rubato "live" track with its true bar lines in a .json;
`--heic IMG.HEIC` uses a real iPhone photo with its Display-P3 ICC,
`--out DIR` writes elsewhere). Then:

- `python render.py test/test_edl.json --preview` - renders every feature (crop/box/fit, keys, speed
  map, uniform slow motion, rotate, tilt, stabilisation, photo Ken Burns, all transitions, all text
  styles, nat sound + `duck_window`, music) -> `test/out/test_film_preview.mp4` in ~0.5-2 min.
- `test/verify.py EDL [--film F] [--preview] [--outdir D]` - format, frame count, loudness,
  black/freeze, clicks at cuts, contact sheets around transitions/texts, photo motion vs plan.
- `test/smooth_test.py [--photo P]` - sub-pixel pan/zoom proof vs an integer-pixel crop.
- `test/path_test.py EDL id [t]` - one item's planned camera path on a still frame, measured vs
  planned motion (separates engine error from path design; uses `../tools/measure_motion.py`).
- `test/grade_sheet.py [shots]` (preset comparison) and `test/font_sheet.py [--bg clip]` (title fonts).
All accept the same `--video-dir/--photo-dir` overrides where they load an EDL; outputs go to `test/out/`
unless `--out`/`--outdir` is given.

## Architecture (why)
1. **Per-item intermediates, in parallel** (`itemrender.py`): ffmpeg decodes the source
   (speed/fps selection, crop of the union of all windows of the shot *before* rotation, Lanczos
   prescale, transpose, explicit BT.709 -> RGB) and pipes raw frames to Python. OpenCV applies
   **one sub-pixel `warpAffine` (bicubic) per frame** whose matrix combines window pan/zoom,
   tilt and stabilisation - the picture is resampled exactly once, so slow pans and Ken Burns
   zooms have no 1-px stepping (proof: `test/smooth_test.py`). The prescale is chosen so the most
   zoomed-in frame is ~1:1 and the warp never downsamples by more than zoom_max/zoom_min (a Gaussian
   pre-blur kicks in above 1.25x). A second ffmpeg applies the grade as a 3D LUT (rgb48,
   tetrahedral) and writes x264 CRF 13 yuv420p. Intermediates are cached under
   `<cache root>/<edl>/<id>_<hash>.mkv`; the hash covers every parameter that affects the pixels,
   so after an EDL edit only changed items re-render.
2. **Audio** (`audio.py`) is mixed in numpy, then two-pass `loudnorm` (linear mode, pre-limiter at
   4x oversampling if the peaks need it).
3. **Assembly** (`assemble.py`): intermediates are read in timeline order, transitions and
   animated texts (`textfx.py`) are composited in Python, and the result is encoded once with x264
   CRF 17 slow.
Why Python warps instead of ffmpeg `zoompan`/`crop`: those round the window to whole pixels per
frame ("trembling Ken Burns"); `scale`+`crop` expressions can't do sub-pixel offsets either. The
warp is also where tilt and stabilisation are folded in for free.

Robustness: every ffmpeg pipe has a stall watchdog (240 s) -> the item is killed and retried
alone; failed items (e.g. out of memory) are retried sequentially; temp files are written then
renamed; stale intermediates are deleted at the start of every render.

Disk: intermediates of grainy 4K-derived footage are ~0.19 MB/frame (CRF 13), the final
~0.11 MB/frame. Before rendering the engine estimates the peak need: < 1 GB free -> abort; if
intermediates + output + 0.3 GB headroom don't fit it switches to `--consume-cache` automatically;
if even that doesn't fit it raises the intermediate CRF (max 18) or aborts.

## EDL schema
```jsonc
{
  "title": "My film",                                             // optional, written as metadata
  "output": {"path": "film.mp4", "w": 1080, "h": 1920, "fps": 30, "crf": 17, "preset": "slow"},
  "paths":  {"video": "D:/footage", "photo": "photos", "proxy": "proxy", "music": ".", "cache": "cache"},
  "grade":  {"preset": "warm_pop"},                               // natural | warm_pop | cinematic_soft | none
  "items": [ ... ], "transitions": [ ... ], "texts": [ ... ],
  "music":  {"path": "bed.wav", "gain_db": 0, "duck_db": -8, "duck_ramp": 0.3,
             "offset": 0.0, "fade_in": 0.0, "fade_out": 2.5},
  "audio":  {"target_lufs": -14, "true_peak": -1.5}
}
```
`--preview` halves w/h and appends `_preview` to the output name (unless `--out` is given).

### Items
| field | meaning |
|---|---|
| `id`, `type` | unique id; `video` (default) or `photo` |
| `src` | file name (looked up in `paths.video` / `paths.photo`, then next to the EDL) or absolute path. Photos may be JPG/PNG/HEIC; an embedded non-sRGB ICC profile (e.g. Display P3) is converted to sRGB; EXIF orientation is applied. |
| `in`, `out` | source seconds (video) |
| `dur` | seconds (photo) |
| `speed` | uniform speed. Integer frame ratios (0.5, 1, 2 from 60 fps) pick exact source frames; other ratios (0.8 ...) go through the time-map path with frame blending (no judder). |
| `speed_map` | `[{"in","out","speed"}, ...]` contiguous over in..out (source s; `in`/`out` default to its ends). Speed changes are eased over ~0.25 s of output time (continuous speed, no stutter). Frames: nearest source frame, or a blend of the two neighbours when the instant falls between them. Keys stay in source time. Clip sound: 1x segments keep their sound, slowed/sped segments are faded out (0.12 s). |
| `frame_blend` | `"auto"` (default: blend between source frames when needed) or `false` (nearest frame) |
| `rotate` | extra rotation after ffmpeg's autorotate: `0`, `90` (clockwise), `-90`, `180`. cx/cy/zoom refer to the rotated frame. |
| `hflip` | mirror after rotate (front-camera selfies). Keys refer to the flipped picture. |
| `tilt_deg` | straightening rotation, degrees, + = clockwise, about the frame centre, after rotate/hflip and before the window. Zoom is auto-raised just enough to hide the empty corners (logged, e.g. -15 deg on a portrait source -> x1.426) and windows slide inwards if needed. |
| `frame` | framing, see below |
| `stabilize` | `true` or `{"smooth": 0.5, "max_zoom": 1.15, "max_shift": 0.08, "rotation": true, "method": "cv"}` - see Stabilisation |
| `nat_sound` | feature the clip sound: the music is ducked by `music.duck_db` (0.3 s raised-cosine ramps, `music.duck_ramp`) and the clip plays at `nat_gain_db` |
| `nat_gain_db` | clip level when `nat_sound` (default 0 dB, relative to the -20 LUFS clip reference) |
| `duck_window` | `[t0, t1]` seconds **from the item's start**: with `nat_sound`, duck the music only in this window (e.g. around a laugh) instead of the whole item; ramps still extend `duck_ramp` outside it |
| `audio_gain_db` | clip level when not featured (default -18) |
| `mute` | drop the clip sound |
| `speed_audio` | uniform speed != 1: `mute` (default) / `pitch` (atempo, pitch preserved) / `natural` (tape-style) |
| `grade_adjust` | `{"exposure": EV, "temperature": -100..100, "tint": -100..100, "saturation": x, "contrast": +-}` applied before the preset look |

Clip sound is high-passed at 120 Hz (wind/handling rumble) and loudness-normalised to -20 LUFS
(max +15 dB) **before** `audio_gain_db` / `nat_gain_db` apply, so gains are predictable.

### frame
| field | meaning |
|---|---|
| `mode` | `crop` (9:16 window fills the frame), `box` (window of `aspect` in a rounded box over a blurred fill), `fit` (= box with the source aspect: whole picture visible) |
| `cx0,cx1,cy0,cy1,zoom0,zoom1` | window centre (normalised upright source coords, 0..1) and zoom at the item's start/end. Shorthands `cx`, `cy`, `zoom` set both ends. zoom 1.0 = largest window of the window aspect that fits the source. Zoom is interpolated geometrically (constant perceived speed). |
| `ease` | `inout` (default), `linear`, `in`, `out`. With keys: anything but `linear` = smooth Hermite. |
| `keys` | `[{"t", "cx", "cy", "zoom"}, ...]` (>= 2; t = **source seconds** for video, seconds from the item start for photos; omitted values carry over from the previous key) - overrides the 0/1 values. Monotone C1 cubic Hermite: ease in/out at the first/last key and at reversals, no overshoot, constant-velocity flow through intermediate keys; values held outside the key range. |
| `aspect` | box mode: window aspect w/h (0.8 = 4:5, 1 = 1:1, 1.333 = 4:3, 1.778 = 16:9) |
| `box_y` (alias `box_cy`) | box/fit: vertical centre of the box on the output (0..1, default 0.5) - e.g. 0.56 to leave room for a title above |
| `box_margin` | px (at 1080 w) left/right margin of the box (default 0 = full width) |
| `radius`, `shadow` | box corner radius px (default 24) and drop-shadow strength (0.45) |
| `bg_blur`, `bg_dim`, `bg_saturation`, `bg_zoom` | blurred fill behind the box: blur sigma px (40), brightness (0.62), saturation (0.85), extra zoom (1.0). The fill is the scaled-to-fill copy of the same frame and follows the window's motion. |

Safety for any EDL: keys / endpoints are first projected into their valid region (zoom >= 1,
window inside the source / the straightened area); if a per-frame clamp still moves the path by
> 0.05 px, the hard clamp is replaced by a smooth push (accumulated, Gaussian 0.15 s, iterated to
< 0.04 px residual) - continuous velocity, no jolts. All such interventions are logged as NOTEs
(`../tools/edl_builder.py` projects keys already when it builds the EDL, and
`../tools/reframe_preview.py` shows the result before rendering).
Key times outside the item's used source range are held. Up to 1 s outside is normal (reframers key
+-0.5 s around a pick) and gives ONE summary NOTE per render; more than 1 s outside is a WARNING per item
(usually a key written in the wrong time base).

### Transitions
`{"after": id, "type": "cut|crossfade|dip_white|dip_black|whip", "dur": s, "dir": "left|right|up|down"}`
Defaults: crossfade 0.5, dips 0.6, whip 0.25 s. Non-cut transitions overlap the neighbours (the
film shrinks by the overlap). Every duration is quantised to frames; `--timeline` prints each item's
start/end, the cut points (transition centres) and the total. Audio: equal-power crossfade under
overlapping transitions, 15 ms raised-cosine micro-fades at cuts.

### Texts
`{"text", "start", "end", "style": "title|subtitle|label|credit"}` (film seconds) plus optional
overrides: `y` (vertical centre, 0..1 of the frame height, e.g. 0.205 for a title above a box), `x`,
`size` (px at 1920 h), `font` (file in `fonts/`), `weight` (variable fonts), `fill` ("#hex" or
[top, bottom] gradient), `stroke`, `stroke_color`, `fade_in`, `fade_out`, `sparkle`, `shine`, `upper`,
`tracking`, `line`, `shadow`, `glow`, `scrim`. `\n` in `text` breaks lines (e.g.
`"Thanks!\nFamily trip 2026"`); long lines wrap/shrink automatically. Everything is kept inside
the Reels safe zone (top 14 %, bottom 22 %, 6 % sides; moved and logged if not). Subtitles without
`y` sit under a concurrent title.
- **title**: Lilita One, yellow->orange gradient, dark-brown outline, drop shadow + warm glow,
  letters pop in one by one, one light sweep, subtle twinkling sparkles; fades/scales out (y 0.30).
- **subtitle**: Baloo 2 Bold, white, letter-spaced, soft shadow, rise + fade.
- **label**: Baloo 2 Bold in a dark translucent pill with an orange accent bar, lower third (y 0.735), slides in.
- **credit**: Montserrat SemiBold, white, soft shadow and a soft dark scrim, rise + fade (y 0.50).
Unicode: per-glyph fallback (Baloo 2); Uzbek okina/apostrophe U+02BB / U+02BC are drawn as
U+2018 / U+2019 when a display font lacks them.

### Music
`music.path` (WAV/MP3/...; looked up in `paths.music`, then next to the EDL) is normalised to -16 LUFS,
then `gain_db` applies; `offset` skips into the file; `fade_in` / `fade_out` (default 2.5 s,
perceptually even cosine-in-dB fade at the film end - use ~0.3 when the bed already ends with a
ring-out); ducking under `nat_sound` items (`duck_db`, `duck_ramp`, per-item `duck_window`). A bed
shorter than the film is padded with silence (warning). Then the whole mix is loudness-normalised
to `audio.target_lufs` with `audio.true_peak` as ceiling.

### Grades
LUTs generated in `grade.py` (same LUT for video and photos): `natural` (clean, light contrast),
`warm_pop` (sunny warm balance, punchy midtones, skin-safe vibrance) - recommended,
`cinematic_soft` (lifted blacks, rolled highlights, teal/amber split), `none`.
Compare with `test/grade_sheet.py`.

### Stabilisation
Default `method: "cv"`, `smooth` = 0.5 s: features tracked on a 960-px grey copy (LK + RANSAC
similarity), the camera path is smoothed with a quadratic Savitzky-Golay filter (follows intentional
pans without the floaty lag of a Gaussian), corrections are soft-limited to a budget (free room
around the window + the margin bought by `max_zoom`, at most `max_shift` = 8 % of the window), and
folded into the single warp (one resample, no black borders; the minimal constant extra zoom is
solved per item). `method: "vidstab"` uses ffmpeg vidstabdetect / vidstabtransform instead.

## Fonts
`fonts/` holds the title/label fonts and alternates (Lilita One, Baloo 2, Montserrat, Titan One,
Luckiest Guy, Bungee, Chewy, ...). All are SIL Open Font License 1.1 (`OFL-*.txt`) except Chewy and
Luckiest Guy (Apache 2.0, `LICENSE-Apache-2.0-*.txt`); see `fonts/FONTS.txt`.

## Known limitations
- Speed is bound by 4K HEVC decoding and x264 `slow`; `--jobs 3+` is not recommended on 8 GB RAM.
- Final master is large (~24 Mbit/s at CRF 17 for grainy 4K-derived footage); use
  `../tools/export.py` for delivery sizes, or set `output.crf` 19-20.
- Text uses Pillow's basic layout (no complex shaping; fine for Latin/Cyrillic).
- `vidstab` method is less tested than `cv`. HDR (HLG) iPhone clips are treated as BT.709 SDR
  (no tone mapping) - shoot SDR or convert first.
- Windows consoles: non-cp1252 characters in logs are printed escaped (`\u02bb`), never crash.
