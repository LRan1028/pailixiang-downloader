#!/usr/bin/env python3
"""
pailixiang_dl.py — Download every original-resolution photo from a 拍立享 (pailixiang.com) album.

Pure standard-library Python 3 (no pip installs, no browser). Works on macOS, Windows, Linux.

The album web page is a Vue single-page app; photos are served by a JSON API.
This tool replicates that API directly:
  1. POST /WapAbm/AlbumGetView   -> resolve the internal AlbumID + total count
  2. POST /WapAbm/AlbumSearchPhoto (paginated by StartIndex) -> list every photo
  3. download each photo's DownloadImageUrl (signed, original full-resolution file)

The API requires an "ak" signature generated client-side from a constant appKey;
gen_ak() below reproduces the site's algorithm exactly, so no browser is needed.

Usage:
    python3 pailixiang_dl.py <album-url-or-code> [-o OUTPUT_DIR] [--page-size N]

Examples:
    python3 pailixiang_dl.py https://live.pailixiang.com/album/a12581882107
    python3 pailixiang_dl.py a12581882107 -o ~/Downloads/my-album
"""
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE = "https://mapi.pailixiang.com/plx"
# Constants baked into the site's JS bundle. ak is derived from appKey.
# cv is the client build the API accepts; a stale value returns Code=9
# ("有新版本需要刷新页面"). Re-extract both with tools/inspect_bundle.py.
APP_KEY = "1e3a58fb24de413c9873542fc5667a25"
CLIENT_VERSION = "169"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")


def gen_ak():
    """Reproduce the site's ak signature: 3 random digits + appKey with
    3 position copies (t[e+15]=t[e]) applied for each digit e."""
    t = list(APP_KEY)
    n = ""
    for _ in range(3):
        e = random.randint(0, 9)
        n += str(e)
        t[e + 15] = t[e]
    return n + "".join(t)


def base_params():
    return {"tt": "", "ct": 0, "cv": CLIENT_VERSION, "lang": "cn",
            "pid": "albumview", "ak": gen_ak()}


def api_post(path, payload, retries=3):
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://live.pailixiang.com",
        "Referer": "https://live.pailixiang.com/",
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
    }
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(API_BASE + path, data=body,
                                         headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("Code") != 0:
                raise RuntimeError(f"API {path} returned Code={data.get('Code')} "
                                   f"Msg={data.get('Msg')!r}")
            return data
        except Exception as e:  # noqa: BLE001 - retry on any transient error
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"API {path} failed after {retries} attempts: {last}")


def parse_album_code(s):
    """Accept a full URL or a bare code; return the numeric ID used by the API.
    e.g. https://live.pailixiang.com/album/a12581882107?... -> '12581882107'"""
    m = re.search(r"/album/([A-Za-z0-9]+)", s)
    code = m.group(1) if m else s.strip()
    code = code.split("?")[0]
    digits = re.sub(r"\D", "", code)  # API's ID param is the numeric part (drops leading 'a')
    if not digits:
        raise ValueError(f"Could not parse an album code from: {s!r}")
    return digits


def get_album_view(album_numeric_id, source_type="singlemessage"):
    payload = {"ID": album_numeric_id, "AccessType": "1", "SourceType": source_type,
               "ClientType": 0, **base_params()}
    data = api_post("/WapAbm/AlbumGetView", payload)
    entity = data["Data"]["Entity"]
    return {
        "album_id": entity["ID"],            # internal id for AlbumSearchPhoto
        "name": entity.get("Name") or entity.get("Title") or album_numeric_id,
        "photo_sort_type": entity.get("PhotoSortType", 1),
        "sort_type": entity.get("SortType", 1),
        "photo_count": data["Data"].get("PhotoSearchCount"),  # per-page size, NOT total
    }


def list_all_photos(view, page_size=80, verbose=True):
    """Page through AlbumSearchPhoto until exhausted. Dedupe by photo ID."""
    seen = {}
    start = 1
    while True:
        payload = {
            "AlbumID": view["album_id"], "GroupID": "", "SearchType": 0,
            "IsPayDownload": False, "PhotoSortType": view["photo_sort_type"],
            "IsNw": False, "IsEmbed": False, "StartIndex": start,
            "SearchCount": page_size, "SortType": view["sort_type"], "OptTime": "",
            **base_params(),
        }
        data = api_post("/WapAbm/AlbumSearchPhoto", payload)
        batch = data.get("Data") or []
        if not batch:
            break
        new = 0
        for p in batch:
            if p["ID"] not in seen:
                seen[p["ID"]] = p
                new += 1
        if verbose:
            print(f"  StartIndex={start}: got {len(batch)}, "
                  f"new {new}, total {len(seen)}")
        if len(batch) < page_size:
            break
        start += page_size
        time.sleep(0.3)
    return list(seen.values())


def safe_name(s):
    # Album titles sometimes contain a newline (two-line event name).
    s = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".")
    return s or "album"


def _fetch_photo(url, path):
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Referer": "https://live.pailixiang.com/"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                content = resp.read()
            if len(content) < 1024:
                raise RuntimeError(f"suspiciously small ({len(content)} bytes)")
            tmp = path + ".part"
            with open(tmp, "wb") as f:
                f.write(content)
            os.replace(tmp, path)
            return len(content)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.0 * (attempt + 1))
    raise last


def download_all(photos, dest, verbose=True, workers=8):
    os.makedirs(dest, exist_ok=True)
    photos = sorted(photos, key=lambda p: p.get("ShootTime") or "")
    width = max(3, len(str(len(photos))))
    used = {}
    jobs = []
    ok, failed = 0, []
    for i, p in enumerate(photos, 1):
        url = p.get("DownloadImageUrl") or p.get("BigImageUrl") or p.get("ImageUrl")
        name = p.get("Name") or p.get("FileName") or f"photo_{i}.jpg"
        if name in used:
            used[name] += 1
            root, ext = os.path.splitext(name)
            name = f"{root}_{used[name]}{ext}"
        else:
            used[name] = 0
        fname = f"{str(i).zfill(width)}_{safe_name(name)}"
        path = os.path.join(dest, fname)
        if os.path.exists(path) and os.path.getsize(path) > 1024:
            ok += 1
            if verbose:
                print(f"[{i}/{len(photos)}] skip (exists) {fname}", flush=True)
            continue
        jobs.append((i, url, fname, path))

    total = len(photos)

    def work(job):
        i, url, fname, path = job
        try:
            nbytes = _fetch_photo(url, path)
            return i, fname, nbytes, None
        except Exception as e:  # noqa: BLE001
            return i, fname, 0, str(e)

    if not jobs:
        return ok, failed
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(work, job) for job in jobs]
        for fut in as_completed(futures):
            i, fname, nbytes, err = fut.result()
            if err:
                failed.append((fname, err))
                print(f"[{i}/{total}] FAIL {fname}: {err}", flush=True)
                continue
            ok += 1
            if verbose:
                print(f"[{i}/{total}] OK {fname} ({nbytes // 1024} KB)", flush=True)
    return ok, failed


def main(argv=None):
    ap = argparse.ArgumentParser(description="Download all photos from a pailixiang album.")
    ap.add_argument("album", help="album URL or code, e.g. https://live.pailixiang.com/album/a12581882107")
    ap.add_argument("-o", "--output", default=None,
                    help="output directory (default: ./<album name>)")
    ap.add_argument("--page-size", type=int, default=80, help="photos per API page (default 80)")
    ap.add_argument("--list-only", action="store_true", help="only list photo count, do not download")
    ap.add_argument("--workers", type=int, default=8, help="parallel downloads (default 8)")
    args = ap.parse_args(argv)

    code = parse_album_code(args.album)
    print(f"Resolving album {code} ...")
    view = get_album_view(code)
    print(f"Album: {safe_name(view['name'])}  (AlbumID={view['album_id']})")

    print("Listing photos (paging) ...")
    photos = list_all_photos(view, page_size=args.page_size)
    print(f"Total photos: {len(photos)}")
    if args.list_only:
        return 0

    dest = args.output or os.path.join(os.getcwd(), safe_name(view["name"]))
    dest = os.path.expanduser(dest)
    print(f"Downloading to: {dest}")
    ok, failed = download_all(photos, dest, workers=args.workers)
    print(f"\nDone: {ok}/{len(photos)} downloaded to {dest}")
    if failed:
        print(f"{len(failed)} failed:")
        for fname, err in failed:
            print(f"  {fname}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
