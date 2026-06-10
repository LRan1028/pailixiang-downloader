---
name: pailixiang-downloader
description: Use when the user wants to download, save, back up, or archive all photos from a 拍立享 / pailixiang.com album link (live.pailixiang.com/album/...). Handles the Vue single-page app that lazy-loads photos so scrolling/HTML scraping misses most of them.
---

# Pailixiang Album Downloader

## Overview

拍立享 (pailixiang.com) album pages are Vue single-page apps. The HTML contains **no
photos** — they load lazily from a JSON API as the user scrolls. Scraping the page,
screenshotting, or "scrolling to load" all miss most photos.

`pailixiang_dl.py` (in this skill's directory) talks to the API directly and downloads
every **original full-resolution** photo. It is pure Python 3 standard library — no pip,
no browser — and runs on macOS, Windows, and Linux.

## When to Use

- User gives a `live.pailixiang.com/album/...` link and wants the photos saved locally.
- User says "download all photos", "保存所有照片", "下载这个相册", "back up this album".

## Quick Start

```bash
python3 pailixiang_dl.py <album-url-or-code> -o <output-dir>
# example:
python3 pailixiang_dl.py https://live.pailixiang.com/album/a12581882107 -o ~/Downloads/album
```

- `--list-only` prints the total count without downloading (use it to confirm the count first).
- `-o` defaults to `./<album name>` if omitted.
- Re-running resumes: existing non-empty files are skipped.
- On Windows use `python` instead of `python3` if that's the launcher name.

## Critical Gotcha: Pagination

**The biggest mistake is downloading only the first page (~80 photos) and thinking that's
all of them.** The `AlbumGetView` field `PhotoSearchCount` is the **page size, not the
total.** Albums commonly have hundreds of photos across multiple pages.

The API pages via `StartIndex` (1, 81, 161, …). Keep requesting until a page returns
fewer than `page_size` items. The script already does this and dedupes by photo ID —
**always trust the script's paged total, not the first response.** If you ever hand-roll
a request, you MUST loop the pagination.

## How It Works (for fixing it if the site changes)

1. `POST https://mapi.pailixiang.com/plx/WapAbm/AlbumGetView` with `{"ID": "<numeric code>", ...}`
   → returns the internal `AlbumID` and album name.
2. `POST .../WapAbm/AlbumSearchPhoto` with that `AlbumID`, paging by `StartIndex`
   → returns photo objects. Use the `DownloadImageUrl` field (signed, original file).
   `BigImageUrl` (style/pbig) and `ImageUrl` (style/psmall) are processed/smaller — avoid them.
3. Each request needs an `ak` signature. It is generated client-side, NOT a session token:
   `ak = <3 random digits> + appKey`, where for each digit `e` the appKey char is copied
   `t[e+15] = t[e]`. `appKey = "1e3a58fb24de413c9873542fc5667a25"`. `gen_ak()` reproduces this.

## If It Breaks (maintenance)

If downloads start failing, the site probably rotated `appKey` or moved the API.
Re-extract the current constants with the bundled zero-dependency tool:

```bash
python3 tools/inspect_bundle.py <album-url>
```

It prints the current `appKey`, API base URL, and the `ak` algorithm snippet from the
live JS bundle. Update `APP_KEY` / `API_BASE` at the top of `pailixiang_dl.py` to match.

If the `ak` algorithm itself changed (the snippet no longer does `t[e+15]=t[e]`),
re-derive `gen_ak()` from the printed snippet. As a last resort, rediscover the whole
API with Chrome DevTools: open the album with remote debugging, watch XHR to
`mapi.pailixiang.com/plx/WapAbm/*`, and read the request bodies.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Only ~80 photos downloaded | You stopped at page 1. Loop `StartIndex` until a short page. |
| Photos look low-res / watermarked | You used `ImageUrl`/`BigImageUrl`. Use `DownloadImageUrl`. |
| Tried to scroll the page / scrape HTML | HTML has no photos. Use the API script. |
| `ak` rejected | Don't reuse a captured `ak` forever; generate a fresh one per run via `gen_ak()`. |
