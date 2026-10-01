# NAVIER YACHTS FZCO — Website

Static marketing site for NAVIER YACHTS FZCO, a custom aluminium yacht, catamaran and
patrol-vessel builder with a design office in Dubai (DSO) and a production shipyard in
Longkou, Shandong, China.

Live at **https://www.navieryacht.com**

---

## Stack

| Layer | Choice | Notes |
| --- | --- | --- |
| Markup | Hand-written static HTML | 10 pages, no framework, no build step |
| Styling | Plain CSS (`css/`) | No preprocessor |
| Scripts | Vanilla JS (`js/`) | No bundler; loaded directly as ES modules are not used |
| Serverless | EdgeOne Pages Node Functions | `node-functions/api/enquiry.js` |
| Hosting | Tencent EdgeOne Pages | Config in `edgeone.json` |
| Images | Pre-generated WebP variants | `images/opt/`, manifest in `tools/image-manifest.json` |

---

## Site Structure

```
naiver/
  index.html             Homepage — hero slider, platform overview
  about.html             Shipyards, manufacturing capability, FAQ
  products.html          Products & services, TideMaster model line-up
  projects.html          Project case studies (deep-linkable, e.g. #tidemaster-cat38)
  news.html              News, build updates and industry articles
  contact.html           Build enquiry form
  privacy-policy.html    Privacy policy (prose page)
  terms-of-service.html  Terms of service (prose page)
  sitemap.html           HTML sitemap
  404.html               Not-found page (noindex)

  css/
    style.css            Main stylesheet (includes prose/legal page styles)
    hero.css             Homepage hero slider only
    timeline.css         Projects page timeline only

  js/
    main.js              Global interactivity: mobile nav, sliders, tabs, back-to-top
    forms.js             Enquiry + newsletter form submission and inline validation

  node-functions/
    api/enquiry.js       POST /api/enquiry — validates and relays to Lark

  images/                Source images, plus `opt/` WebP derivatives
  tools/                 Maintenance and QA scripts (see below)

  edgeone.json           Response headers, CSP, cache TTLs
  robots.txt             Crawler directives
  sitemap.xml            XML sitemap
```

---

## The enquiry endpoint

`POST /api/enquiry` accepts both the build enquiry form and the footer newsletter form.
It validates input server-side, applies a honeypot and a best-effort rate limit, then
posts an interactive card to a Lark (Feishu) custom bot.

`GET /api/enquiry` returns a health check — useful for confirming configuration:

```json
{ "ok": true, "endpoint": "/api/enquiry", "webhookConfigured": true,
  "secretConfigured": true, "ready": true }
```

### Required environment variables

Set these in the **EdgeOne Pages console** (Project → Settings → Environment Variables).
They are deliberately **not** committed — this repository is public, and anyone holding
the webhook URL plus the secret can post messages into the workspace.

| Variable | Purpose |
| --- | --- |
| `LARK_WEBHOOK_URL` | Full custom-bot webhook URL |
| `LARK_WEBHOOK_SECRET` | Signing secret for that bot |

If either variable is missing the endpoint fails loudly with HTTP 503 rather than
silently dropping enquiries.

### Response codes

| Code | Meaning |
| --- | --- |
| 200 | Delivered (also returned for honeypot hits, which are silently discarded) |
| 400 | Validation failed — response includes a `fields` array |
| 405 | Method not allowed (only GET and POST are exposed) |
| 429 | Rate limited (5 submissions per IP per minute) |
| 502 | Upstream delivery failed — response includes a `fallback` contact hint |
| 503 | Webhook not configured on the server |

---

## Local development

There is no build step and no dependency install. Serve the directory over HTTP and
open a page:

```bash
python -m http.server 8080
```

The enquiry endpoint is a serverless function and will not run under a plain static
server. To exercise it locally, deploy to a preview environment, or stub the request
in the browser console.

---

## Maintenance tooling (`tools/`)

Every script is dependency-free (standard library only) and safe to re-run.

| Script | What it does |
| --- | --- |
| `validate.py` | Primary site check: canonical URLs, JSON-LD validity, broken local links, title/meta presence, secret leakage. `--fix` repairs repairable issues. |
| `check-html.py` | Structural HTML audit using `html.parser`: tag balance, block-element nesting inside `<p>`, unescaped `&`, duplicate attributes, duplicate ids, heading order. |
| `check-js-syntax.py` | Extracts every inline `<script>` block and every `js/*.js` file and runs `node --check` on it. |
| `debris-scan.py` | Finds development leftovers: CJK characters, TODO/FIXME, inline event handlers, `target="_blank"` without `rel="noopener"`, placeholder anchors, images without `alt`. |
| `escape-ampersands.py` | HTML-escapes bare `&` in text and attributes while leaving `<script>`, `<style>` and comments untouched. `--write` applies. |
| `build-partials.py` | Regenerates the shared `<header>` and `<footer>` blocks across all pages from a single source. |
| `optimize-images.py` | Generates the WebP variants in `images/opt/` and rewrites `<img>` tags with `srcset`/`sizes`. |
| `build-assets.py` | Regenerates `favicon.ico`, `favicon.svg`, `apple-touch-icon.png` and `images/og-image.jpg`. |
| `seo-enhance.py` | Adds `theme-color`, `og:locale`, Open Graph image tags, breadcrumb markup and page-level JSON-LD. |
| `migrate-2026-09.py` | Archived one-off migration (domain to `www`, asset renames, keyword meta removal). Kept for the record. |

Run the four read-only auditors before committing:

```bash
python tools/validate.py
python tools/check-html.py
python tools/check-js-syntax.py
python tools/debris-scan.py
```

---

## Conventions and constraints

- **Cache busting** — asset filenames are *not* content-hashed, so `edgeone.json`
  deliberately avoids `immutable` caching. A long `max-age` on `/css/*` or `/js/*`
  would strand returning visitors on stale files. If a build step ever adds hashed
  filenames, the TTLs can be raised to `max-age=31536000, immutable`.
- **`edgeone.json` must stay strict JSON.** It does not accept comments; explanatory
  notes for that file live here and in the audit report instead.
- **Content Security Policy** — `edgeone.json` currently allows `'unsafe-inline'` for
  `script-src` and `style-src`. Removing it requires externalising the page-level
  `<script>` and `<style>` blocks in `about.html`, `news.html` and `projects.html`,
  and eliminating the inline `style=""` attributes. Tracked as future work, not a
  blocker: the rest of the policy (no `object-src`, no framing, `base-uri` and
  `form-action` pinned, `connect-src` self-only) is enforced.
- **No cookies and no analytics.** The site sets no cookies and runs no third-party
  tracking. Keep it that way unless the privacy policy and a consent mechanism are
  updated at the same time.
- **`www` is canonical.** The bare domain `navieryacht.com` is not bound to the
  EdgeOne Pages project; all canonical tags, Open Graph URLs and sitemap entries use
  `https://www.navieryacht.com/`.
- **Accessibility** — interactive controls are real `<button>`/`<a>` elements with
  `aria-*` state, forms have real `<label>`s, and `prefers-reduced-motion` is honoured.

---

## Contact

- **Email:** info@navieryacht.com
- **Phone:** +971 58 508 8518
- **Web:** https://www.navieryacht.com
- **Address:** Dubai Integrated Economic Zones (DSO), Dubai, United Arab Emirates
- **Shipyard:** Longkou, Shandong, China
