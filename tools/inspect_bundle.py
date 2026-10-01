#!/usr/bin/env python3
"""
inspect_bundle.py — Maintenance tool. Re-extract the constants pailixiang_dl.py depends on.

Run this if the downloader ever stops working (e.g. the site rotates its appKey or
moves the API). It fetches the album page, finds the current JS bundle, and pulls out:
  - appKey            (the constant pailixiang_dl.gen_ak() needs)
  - API base URL      (e.g. https://mapi.pailixiang.com/plx)
  - the ak algorithm snippet from the bundle (so you can re-verify gen_ak)

Pure standard library. Then update the constants at the top of ../pailixiang_dl.py.

Usage:
    python3 tools/inspect_bundle.py [album-url]
"""
import re
import sys
import urllib.request

DEFAULT_URL = "https://live.pailixiang.com/album/a12581882107"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")


def fetch(url, referer=None):
    headers = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        elif resp.headers.get("Content-Encoding") == "deflate":
            import zlib
            raw = zlib.decompress(raw)
        return raw.decode("utf-8", "replace")


def main():
    album_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    print(f"Fetching album page: {album_url}")
    html = fetch(album_url)

    # The page is served from a CDN host (e.g. abms.pailixiang.com); find the index bundle.
    m = re.search(r'src="(https://[^"]+/js/index\.[a-f0-9]+\.js)"', html)
    if not m:
        m = re.search(r'(https://[^"\s]+/js/index\.[a-f0-9]+\.js)', html)
    if not m:
        print("Could not locate index.*.js bundle in the page HTML.", file=sys.stderr)
        print("The page structure may have changed; inspect the HTML manually.", file=sys.stderr)
        return 1
    bundle_url = m.group(1)
    print(f"Bundle: {bundle_url}")

    # Bundle host enforces a Referer ACL; must send the album origin.
    js = fetch(bundle_url, referer="https://live.pailixiang.com/")

    appkey = re.search(r'appKey:"([0-9a-f]{16,})"', js)
    base = re.search(r'baseURL:"(https://[^"]+)"', js)
    cv = re.search(r'e\.cv="(\d+)"', js)
    ak_fn = re.search(r'.{60}e\.ak=n\+t\.join\(""\)', js)

    print("\n=== extracted constants ===")
    print("appKey   :", appkey.group(1) if appkey else "NOT FOUND")
    print("API base :", base.group(1) if base else "NOT FOUND")
    print("cv       :", cv.group(1) if cv else "NOT FOUND")
    print("ak algo  :", (ak_fn.group(0) if ak_fn else "NOT FOUND (ak generation may have changed)"))

    print("\nUpdate APP_KEY / API_BASE / CLIENT_VERSION at the top of pailixiang_dl.py if these differ.")
    if ak_fn and "e+15" not in ak_fn.group(0):
        print("WARNING: the ak algorithm looks different from the documented one — "
              "re-derive gen_ak() from the snippet above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
