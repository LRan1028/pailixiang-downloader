# pailixiang-downloader

[简体中文](README.md) | English

Download every **original full-resolution** photo from a 拍立享 / [pailixiang.com](https://live.pailixiang.com) album in one command.

Pailixiang album pages are Vue single-page apps — the HTML has no photos, they lazy-load
from a JSON API as you scroll. So "save image as", screenshotting, or scroll-and-scrape
all miss most of the album. This tool calls the API directly and grabs everything.

- ✅ Pure Python 3 standard library — **no pip install, no browser/Selenium**
- ✅ Cross-platform: macOS, Windows, Linux
- ✅ Downloads original files (not the compressed/watermarked previews)
- ✅ Handles pagination automatically (albums often have hundreds of photos)
- ✅ Resumable — re-run to skip already-downloaded files

## Install

Requires Python 3.7+. No dependencies.

```bash
git clone https://github.com/muxia23/pailixiang-downloader.git
cd pailixiang-downloader
```

## Usage

```bash
python3 pailixiang_dl.py <album-url-or-code> [-o OUTPUT_DIR]
```

Examples:

```bash
# full URL
python3 pailixiang_dl.py https://live.pailixiang.com/album/a12581882107 -o ~/Downloads/album

# bare code, output to ./<album name>
python3 pailixiang_dl.py a12581882107

# just count the photos, don't download
python3 pailixiang_dl.py a12581882107 --list-only
```

On Windows, use `python` instead of `python3` if that's your launcher.

### Options

| Flag | Description |
|------|-------------|
| `-o, --output DIR` | Output directory (default: `./<album name>`) |
| `--page-size N` | Photos per API page (default 80) |
| `--list-only` | Print total photo count and exit |
| `--workers N` | Parallel downloads (default 8) |

Files are named `NNN_<original-name>.jpg`, ordered by shoot time. Re-running skips files
that already exist (non-empty), so interrupted downloads resume cleanly.

## How it works

1. `POST mapi.pailixiang.com/plx/WapAbm/AlbumGetView` → resolves the album's internal ID.
2. `POST .../WapAbm/AlbumSearchPhoto`, paging by `StartIndex` until exhausted → full photo list.
3. Downloads each photo's signed `DownloadImageUrl` (the original, full-resolution file).

Each request carries an `ak` signature that the site computes client-side from a constant
`appKey`; `gen_ak()` reproduces that algorithm, so no browser/login is needed.

> **Note on `PhotoSearchCount`:** the album-view field `PhotoSearchCount` is the *page
> size*, not the total. The downloader pages through `StartIndex` and dedupes by photo ID
> to get the real total. Don't assume the first ~80 photos are the whole album.

### Maintenance

If the site rotates its `appKey` or moves the API and downloads start failing, re-extract
the current constants (zero dependencies, no browser):

```bash
python3 tools/inspect_bundle.py <album-url>
```

Then update `APP_KEY` / `API_BASE` / `CLIENT_VERSION` at the top of `pailixiang_dl.py`. `Code=9` ("有新版本需要刷新页面") means `CLIENT_VERSION` is stale.

## Disclaimer

For downloading albums you have the right to access (e.g. your own events, or albums
shared with you). Respect the photographers' and platform's terms of use and copyright.
This tool calls the same public API the album web page uses.

## License

MIT
