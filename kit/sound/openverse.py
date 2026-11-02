"""Openverse: search and download free sound effects (no API key), with the credit written down.

    python kit/sound/openverse.py search "whoosh fast" [--license cc0] [--n 10] [--max-s 3]
    python kit/sound/openverse.py get <id> [--out audio/sfx] [--credits audio/CREDITS.md]

search prints id, length, licence, author and title of each match. get downloads one, names it
<slug>-<id8>.<ext> and appends a line to CREDITS.md (title, author, licence, source URL), so the film's
credits are never reconstructed by hand. CC0 needs no credit but gets one anyway; CC BY needs it.
Default licence filter is cc0 (public domain); --license by allows CC BY too. NC/ND licences are never
offered: a reel for a business is commercial use.

Only the standard library. Behind a TLS-intercepting proxy (corporate networks) it uses the system's
certificates through truststore when that is installed (pip's vendored copy works too).
"""

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.openverse.org/v1/audio/"
UA = "lemo-opuscar-kit/1.0 (+https://github.com/ubaydullayevgiyosiddin7-eng/plugin_generate_video_cloudecode)"
COMMERCIAL_OK = {"cc0": "cc0", "by": "cc0,by", "pdm": "pdm,cc0"}
LAST = Path.home() / ".openverse-last.json"   # the last search, so get needs no second (slow) API call


def _ssl_context() -> ssl.SSLContext:
    for name in ("truststore", "pip._vendor.truststore"):
        try:
            mod = __import__(name, fromlist=["SSLContext"])
            return mod.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        except ImportError:
            continue
    return ssl.create_default_context()


CTX = _ssl_context()


def _get(url: str, tries: int = 3) -> bytes:
    """Openverse answers 504 or stalls now and then: three tries, 5 s and 15 s apart."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=90) as r:
                return r.read()
        except (TimeoutError, urllib.error.URLError) as e:
            if k == tries - 1 or (isinstance(e, urllib.error.HTTPError) and e.code < 500):
                raise
            time.sleep(5 * 3 ** k)


def search(q: str, license_: str, n: int, max_s: float) -> list[dict]:
    params = {"q": q, "license": COMMERCIAL_OK[license_], "page_size": min(50, max(n * 3, 20))}
    data = json.loads(_get(API + "?" + urllib.parse.urlencode(params)))
    out = []
    for r in data.get("results", []):
        dur = (r.get("duration") or 0) / 1000
        if max_s and dur and dur > max_s:
            continue
        out.append(r)
        if len(out) >= n:
            break
    LAST.write_text(json.dumps(out), encoding="utf-8")
    return out


def get(id_: str, out_dir: Path, credits: Path) -> Path:
    last = json.loads(LAST.read_text(encoding="utf-8")) if LAST.exists() else []
    r = next((x for x in last if x["id"] == id_), None)
    if r is None:                       # the detail endpoint can take 20 s or more
        r = json.loads(_get(API + urllib.parse.quote(id_) + "/"))
    url = r["url"]
    ext = Path(urllib.parse.urlparse(url).path).suffix or "." + (r.get("filetype") or "mp3")
    slug = re.sub(r"[^a-z0-9]+", "-", (r.get("title") or "sound").lower()).strip("-")[:40] or "sound"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}-{id_[:8]}{ext}"
    path.write_bytes(_get(url))
    lic = f"{r.get('license', '').upper()} {r.get('license_version') or ''}".strip()
    line = (f"- {path.name}: \"{r.get('title')}\" by {r.get('creator') or 'unknown'}, {lic}, "
            f"{r.get('foreign_landing_url') or url} (via Openverse)\n")
    credits.parent.mkdir(parents=True, exist_ok=True)
    if not credits.exists():
        credits.write_text("# Sound credits\n\n", encoding="utf-8")
    with credits.open("a", encoding="utf-8") as f:
        f.write(line)
    print(f"{path}  ({lic})")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--license", choices=sorted(COMMERCIAL_OK), default="cc0")
    s.add_argument("--n", type=int, default=10)
    s.add_argument("--max-s", type=float, default=0, help="longest clip in seconds (0 = any)")
    g = sub.add_parser("get")
    g.add_argument("id")
    g.add_argument("--out", type=Path, default=Path("audio/sfx"))
    g.add_argument("--credits", type=Path, default=Path("audio/CREDITS.md"))
    a = ap.parse_args()
    if a.cmd == "search":
        for r in search(a.query, a.license, a.n, a.max_s):
            dur = (r.get("duration") or 0) / 1000
            print(f"{r['id']}  {dur:5.1f}s  {r.get('license', ''):4}  {(r.get('creator') or '')[:18]:18}  {r.get('title')}")
    else:
        get(a.id, a.out, a.credits)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
