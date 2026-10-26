# Brianna Hall — portfolio site

A hand-built replacement for Brianna's Canva site. Every photo, project, video and paragraph from
the Canva site is here. Brianna edits it through **Pages CMS**, a free visual editor; she never
touches code. Every save republishes the site automatically in about a minute.

```
content/       words and lists (one file per page)     ← the editor changes these
media/         every photo and video                   ← uploads land here
templates/     page layouts (HTML)
assets/        site.css, site.js, favicon.svg
build.py       turns content/ + media/ into the finished site in _site/
.pages.yml     what Brianna sees in the editor
.github/       publishes the site on every change
```

## One-time setup (about 30 minutes)

### 1. Put the site on GitHub
1. Create a free GitHub account if needed, then a **new public repository**, e.g. `briannahall-portfolio`.
2. Upload everything in this folder (drag the folder contents into “uploading an existing file”,
   or `git init && git add . && git commit -m "Portfolio" && git push`). Keep the hidden
   `.pages.yml` and `.github` folder; on a Mac press `Cmd + Shift + .` in Finder to see them.

### 2. Turn on publishing
1. In the repository: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Open the **Actions** tab. “Publish site” runs on every change; the first run takes ~2 minutes.
3. The site appears at `https://<your-username>.github.io/briannahall-portfolio/`.

### 3. Connect the domain
Suggested: **briannahall.design** (her name, her field). Backup: **briannahallcreative.com**.
`briannahall.com` is already taken. Both suggestions were unregistered on 26 Oct 2026.

1. Buy it from any registrar (Cloudflare, Porkbun or Namecheap all work).
2. In the registrar’s DNS settings add:
   - four **A** records for `@` → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - one **CNAME** record for `www` → `<your-username>.github.io`
3. In GitHub: **Settings → Pages → Custom domain** → enter the domain → Save. Once the check
   passes, tick **Enforce HTTPS** (can take up to an hour).
4. In the editor, set **Contact & site details → Website address** to `https://briannahall.design`
   so shared links show a preview image.

### 4. Give Brianna the editor
1. Go to **app.pagescms.org**, sign in with GitHub and install the Pages CMS app on the repository.
2. Open the repository there and invite Brianna’s email as a **collaborator**.
   She does not need a GitHub account; she signs in from the email link.
3. Send her `EDITING.md` (or print it).

## Working on the site locally (optional)
```
pip install -r requirements.txt
python build.py            # writes _site/
python -m http.server -d _site 8000
```
`python build.py --preview` makes a self-contained copy in `_preview/` with explicit
`index.html` links, for sharing as a file.

## How the build treats photos
- Any size, JPG/PNG/WebP/HEIC: `build.py` makes 480, 960, 1600 and up-to-2000-pixel WebP
  copies and lets each visitor’s browser pick the right one.
- Album and merch photos are arranged into rows automatically by shape. A photo marked
  “Show this photo big” gets its own row.
- Resized copies are cached in `.cache/` (GitHub keeps the cache between runs), so only new
  photos are processed.

## Other hosts
Netlify or Cloudflare Pages also work: build command `pip install -r requirements.txt && python build.py`,
publish directory `_site`.

## Content notes
- The text is Brianna’s own, copied from the Canva site. Five spelling slips were corrected:
  opprtunity → opportunity, portaryed → portrayed, “fireproofs … drivers where under” → wear,
  “how it effects the overall car” → affects, “our teams 2026 design cycle” → team’s.
- The recruitment poster, the “Formula Electric” grain poster and the two brand-guideline
  spreads were assembled inside Canva rather than uploaded as images; they were rendered from
  the live Canva site at high resolution and saved as images in `media/`.
