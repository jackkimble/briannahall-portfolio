#!/usr/bin/env python3
"""Build Brianna Hall's portfolio into the _site/ folder.

    python build.py              # production build (pretty URLs)
    python build.py --preview    # self-contained preview (explicit index.html links, inlined CSS/JS)

Content lives in content/, uploads live in media/, page layouts live in templates/.
Nothing in here needs editing to change words or photos: use the editor (Pages CMS).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape
from PIL import Image, ImageOps

try:  # lets iPhone photos (.heic) be uploaded directly
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
MEDIA = ROOT / "media"
TEMPLATES = ROOT / "templates"
ASSETS = ROOT / "assets"
CACHE = ROOT / ".cache" / "img"

WIDTHS = (480, 960, 1600)      # responsive sizes generated for every photo
MAX_WIDTH = 2000                # largest file ever served
WEBP_QUALITY = 82
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp", ".heic"}
COPY_EXT = {".svg", ".gif"}     # served exactly as uploaded

SECTIONS = {
    "photography": ("photography/", "Photography"),
    "brand-projects": ("brand-projects/", "Brand Projects"),
    "merch": ("merch/", "Merch"),
    "illustrations": ("illustrations/", "Illustrations"),
}


# ---------------------------------------------------------------- content ----
def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {"body": text}
    data = yaml.safe_load(m.group(1)) or {}
    data["body"] = m.group(2).strip()
    return data


def slug_of(path: Path) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", path.stem.lower()).strip("-")


def load_collection(folder: Path) -> list[dict]:
    items = []
    for path in sorted(folder.glob("*.md")):
        data = load_front_matter(path)
        if data.get("hidden"):
            continue
        data["slug"] = slug_of(path)
        items.append(data)
    items.sort(key=lambda d: (d.get("order") if d.get("order") is not None else 999, d.get("title", "")))
    return items


def check_media(content) -> None:
    """Stop early, naming every photo or video the content uses that isn't in media/."""
    found: list[str] = []

    def walk(value):
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
        elif isinstance(value, str) and value.strip().startswith("/media/"):
            found.append(value.strip())

    walk(content)
    missing = sorted({src for src in found if not MediaPipeline.source(src).exists()})
    if not missing:
        return
    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for src in missing:
        rel = src.lstrip("/")
        folder, name = rel.rsplit("/", 1)
        line = f"Missing file: {rel} (upload {name} into the {folder} folder)"
        print(f"::error::{line}" if in_actions else line)
    raise SystemExit(f"{len(missing)} file(s) missing from the media folder, listed above.")


# ----------------------------------------------------------------- images ----
class MediaPipeline:
    """Turns '/media/…' paths from the content into optimized files in the output."""

    def __init__(self, out: Path, widths=WIDTHS):
        self.out = out
        self.widths = widths
        self.done: dict[str, dict] = {}
        CACHE.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def source(src: str) -> Path:
        rel = src.split("?")[0].lstrip("/")
        if rel.startswith("media/"):
            rel = rel[len("media/"):]
        return MEDIA / rel

    def is_video(self, src: str) -> bool:
        return Path(src).suffix.lower() in {".mp4", ".webm", ".mov", ".m4v"}

    def image(self, src: str) -> dict:
        """Return {'src','srcset','w','h'} with paths relative to the site root."""
        if src in self.done:
            return self.done[src]
        path = self.source(src)
        if not path.exists():
            raise SystemExit(f"Missing file: {src} (looked for {path})")
        ext = path.suffix.lower()
        if ext in COPY_EXT:
            target = self.out / "media" / path.relative_to(MEDIA)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            w = h = None
            if ext == ".gif":
                with Image.open(path) as im:
                    w, h = im.size
            info = {"src": target.relative_to(self.out).as_posix(), "srcset": "", "w": w, "h": h}
            self.done[src] = info
            return info

        data = path.read_bytes()
        digest = hashlib.sha1(data).hexdigest()[:10]
        stem = re.sub(r"[^a-z0-9-]+", "-", path.stem.lower()).strip("-") or "image"
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            W, H = im.size
            widths = sorted({w for w in self.widths if w < W} | {min(W, MAX_WIDTH if self.widths == WIDTHS else 1600)})
            files = []
            for w in widths:
                name = f"{stem}-{digest}-{w}.webp"
                cached = CACHE / name
                if not cached.exists():
                    h = round(H * w / W)
                    frame = im if im.mode in ("RGB", "RGBA") else im.convert("RGBA" if "A" in im.getbands() else "RGB")
                    frame.resize((w, h), Image.LANCZOS).save(cached, "WEBP", quality=WEBP_QUALITY, method=5)
                target = self.out / "img" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    shutil.copyfile(cached, target)
                files.append((w, f"img/{name}"))
        fallback = [f for w, f in files if w <= 1600] or [files[0][1]]
        info = {
            "src": fallback[-1],
            "srcset": [(f, w) for w, f in files],
            "w": W,
            "h": H,
            "largest": files[-1][1],
        }
        self.done[src] = info
        return info

    def file(self, src: str) -> str:
        """Copy a non-image upload (video, pdf) as-is and return its site path."""
        path = self.source(src)
        if not path.exists():
            raise SystemExit(f"Missing file: {src}")
        target = self.out / "media" / path.relative_to(MEDIA)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.stat().st_size != path.stat().st_size:
            shutil.copyfile(path, target)
        return target.relative_to(self.out).as_posix()


# ------------------------------------------------------------------ rows -----
def compose_rows(photos: list[dict], media: MediaPipeline, target: float = 2.7) -> list[dict]:
    """Group photos into rows of 1–3 that share a height, like a laid-out spread.

    A photo marked `feature`, and every other landscape that opens a row, gets a row of
    its own. Everything else is packed until the row's combined width is about `target`
    (in units of row height).
    """
    items = []
    for p in photos:
        if not p or not p.get("image"):
            continue
        info = media.image(p["image"])
        ratio = (info["w"] / info["h"]) if info.get("w") else 1.0
        items.append({**p, "ratio": round(ratio, 4)})

    rows: list[list[dict]] = []
    i, solo_next = 0, True
    while i < len(items):
        it = items[i]
        if it.get("feature") or (solo_next and it["ratio"] >= 1.3 and len(items) - i > 2):
            rows.append([it])
            i += 1
            solo_next = False
            continue
        row, total = [], 0.0
        while i < len(items) and len(row) < 3 and (total < target or len(row) < 2):
            if items[i].get("feature") and row:
                break
            row.append(items[i])
            total += items[i]["ratio"]
            i += 1
        rows.append(row)
        solo_next = True
    # Never end on a lone, unplanned photo: tuck it into the row before.
    if len(rows) > 1 and len(rows[-1]) == 1 and not rows[-1][0].get("feature") and len(rows[-2]) <= 3 \
            and not any(it.get("feature") for it in rows[-2]):
        rows[-2].extend(rows.pop())
    out = []
    for row in rows:
        total = sum(it["ratio"] for it in row)
        for it in row:
            it["share"] = round(it["ratio"] / total * 100, 4)
        out.append({"items": row, "ratio": round(total, 4)})
    return out


# ---------------------------------------------------------------- render -----
def build(preview: bool = False, out: Path | None = None) -> Path:
    out = out or (ROOT / ("_preview" if preview else "_site"))
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    media = MediaPipeline(out, widths=(800, 1600) if preview else WIDTHS)

    site = load_yaml(CONTENT / "site.yml")
    home = load_yaml(CONTENT / "home.yml")
    merch = load_yaml(CONTENT / "merch.yml")
    illustrations = load_yaml(CONTENT / "illustrations.yml")
    albums = load_collection(CONTENT / "photography")
    projects = load_collection(CONTENT / "projects")

    check_media([site, home, merch, illustrations, albums, projects])

    work = {w.get("section"): w for w in home.get("work", []) if w.get("section")}
    for key, (path, title) in SECTIONS.items():
        w = work.setdefault(key, {})
        w.setdefault("title", title)
        w["url"] = path

    css = (ASSETS / "site.css").read_text(encoding="utf-8")
    js = (ASSETS / "site.js").read_text(encoding="utf-8")
    if not preview:
        (out / "assets").mkdir()
        shutil.copyfile(ASSETS / "site.css", out / "assets" / "site.css")
        shutil.copyfile(ASSETS / "site.js", out / "assets" / "site.js")
        for extra in ("favicon.svg",):
            if (ASSETS / extra).exists():
                shutil.copyfile(ASSETS / extra, out / extra)

    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)
    env.filters["softbreak"] = lambda text: Markup(str(escape(text or "")).replace("/", "/<wbr>"))

    def render(template: str, page_path: str, filename: str = "index.html", absolute: bool = False, **ctx):
        """page_path is '' for home or 'section/slug/' style; writes <page_path>/<filename>."""
        depth = page_path.count("/")
        prefix = "/" if absolute else "../" * depth

        def url(target: str) -> str:
            target = target.strip("/")
            target = f"{target}/" if target else ""
            if preview:
                return f"{prefix}{target}index.html"
            return f"{prefix}{target}" or "./"

        def asset(p: str) -> str:
            return prefix + p

        def img(src, alt="", sizes="100vw", cls="", loading="lazy", priority=False, attrs=""):
            if not src:
                return Markup("")
            info = media.image(src)
            alt_attr = escape(alt or "")
            cls_attr = f' class="{escape(cls)}"' if cls else ""
            dims = f' width="{info["w"]}" height="{info["h"]}"' if info.get("w") else ""
            if info["srcset"]:
                srcset = ", ".join(f"{asset(f)} {w}w" for f, w in info["srcset"])
                html = (f'<img src="{asset(info["src"])}" srcset="{srcset}" sizes="{escape(sizes)}"'
                        f'{dims} alt="{alt_attr}"{cls_attr} decoding="async"')
            else:
                html = f'<img src="{asset(info["src"])}"{dims} alt="{alt_attr}"{cls_attr} decoding="async"'
            html += ' fetchpriority="high"' if priority else f' loading="{loading}"'
            if attrs:
                html += " " + attrs
            return Markup(html + ">")

        def full(src):
            info = media.image(src)
            return asset(info.get("largest") or info["src"])

        def ratio(src):
            info = media.image(src)
            return round(info["w"] / info["h"], 4) if info.get("w") else 1

        def file_url(src):
            return asset(media.file(src)) if src else ""

        def poster(src):
            return asset(media.image(src)["src"]) if src else ""

        def md(text):
            return Markup(markdown.markdown(text or "", extensions=["extra", "sane_lists"])) if text else Markup("")

        def is_video(src):
            return bool(src) and media.is_video(src)

        def tel(phone):
            return re.sub(r"[^0-9+]", "", phone or "")

        nav = [(key, work[key]["title"], url(path)) for key, (path, _) in SECTIONS.items()]
        html = env.get_template(template).render(
            site=site, home=home, work=work, nav=nav, albums=albums, projects=projects,
            url=url, asset=asset, img=img, full=full, ratio=ratio, file_url=file_url, poster=poster,
            md=md, is_video=is_video, tel=tel, preview=preview, bare=(preview and page_path == ""),
            inline_css=Markup(css) if preview else None, inline_js=Markup(js) if preview else None,
            year=dt.date.today().year, page_path=page_path, **ctx,
        )
        target = out / page_path / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")

    render("home.html", "", current="home")
    for album in albums:
        album["count"] = len([p for p in album.get("photos") or [] if p and p.get("image")])
    render("photography.html", "photography/", current="photography", section=work["photography"])
    for i, album in enumerate(albums):
        nxt = albums[(i + 1) % len(albums)] if len(albums) > 1 else None
        render("album.html", f"photography/{album['slug']}/", current="photography", album=album,
               rows=compose_rows(album.get("photos") or [], media), next_album=nxt, section=work["photography"])
    render("projects.html", "brand-projects/", current="brand-projects", section=work["brand-projects"])
    for i, project in enumerate(projects):
        nxt = projects[(i + 1) % len(projects)] if len(projects) > 1 else None
        render("project.html", f"brand-projects/{project['slug']}/", current="brand-projects", project=project,
               next_project=nxt, section=work["brand-projects"])
    render("merch.html", "merch/", current="merch", page=merch, rows=compose_rows(merch.get("photos") or [], media),
           section=work["merch"])
    render("illustrations.html", "illustrations/", current="illustrations", page=illustrations, section=work["illustrations"])
    if not preview:
        # Hosts serve /404.html for any missing address, so its links are absolute.
        render("404.html", "", filename="404.html", absolute=True, current="")
    if not preview:
        (out / ".nojekyll").write_text("")
        if site.get("custom_domain"):
            (out / "CNAME").write_text(site["custom_domain"].strip() + "\n")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", action="store_true", help="build a self-contained preview into _preview/")
    ap.add_argument("--out", type=Path, help="output folder")
    args = ap.parse_args()
    result = build(preview=args.preview, out=args.out)
    pages = len(list(result.rglob("*.html")))
    print(f"Built {pages} pages into {result.relative_to(ROOT) if result.is_relative_to(ROOT) else result}")
