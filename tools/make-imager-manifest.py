#!/usr/bin/env python3
"""
Generate a Raspberry Pi Imager (v2.x) manifest for locally downloaded
HamClock images, so Imager's OS-customisation step (hostname, user, WiFi,
locale, SSH) is enabled instead of greyed out.

Why this is needed
------------------
Since Imager 2.0, customisation is driven by the `init_format` field of an
image's manifest entry. "Use custom" images have no manifest entry, so
Imager disables customisation. This script writes a manifest entry for each
image you give it, declaring the right `init_format`:

    bookworm-based images -> "systemd"        (firstrun.sh mechanism)
    trixie-based images   -> "cloudinit-rpi"  (cloud-init mechanism)

Usage
-----
    python3 tools/make-imager-manifest.py hamclock-*.img.xz
    # then either double-click the generated hamclock.rpi-imager-manifest,
    # or:  rpi-imager --repo /path/to/hamclock.rpi-imager-manifest
    # or:  App Options > Content Repository > Edit > Use custom file

Pick the image from the OS list (not "Use custom"). Needs only the Python 3
standard library. It decompresses each image once to hash it, which takes a
minute or two per image.
"""
import argparse
import datetime
import hashlib
import json
import lzma
import os
import pathlib
import re
import sys
import urllib.request

OFFICIAL_MANIFEST = "https://downloads.raspberrypi.org/os_list_imagingutility_v4.json"

# Used only if the official manifest can't be downloaded (offline use).
FALLBACK_DEVICES = [
    {"name": "Raspberry Pi 5", "tags": ["pi5-64bit", "pi5-32bit"], "default": False, "matching_type": "inclusive"},
    {"name": "Raspberry Pi 4 / 400 / CM4", "tags": ["pi4-64bit", "pi4-32bit"], "default": False, "matching_type": "inclusive"},
    {"name": "Raspberry Pi 3 / Zero 2 W", "tags": ["pi3-64bit", "pi3-32bit"], "default": False, "matching_type": "inclusive"},
]

INIT_FORMATS = {"bookworm": "systemd", "trixie": "cloudinit-rpi"}


def hash_image(path):
    """Return (extracted_size, extracted_sha256, download_sha256)."""
    dl = hashlib.sha256()
    ex = hashlib.sha256()
    size = 0
    with open(path, "rb") as raw:
        class Tee:
            def read(self, n=-1):
                b = raw.read(n)
                dl.update(b)
                return b
        with lzma.open(Tee()) as xz:
            while True:
                chunk = xz.read(4 * 1024 * 1024)
                if not chunk:
                    break
                ex.update(chunk)
                size += len(chunk)
        # drain anything lzma didn't consume so the download hash is complete
        while True:
            b = raw.read(4 * 1024 * 1024)
            if not b:
                break
            dl.update(b)
    return size, ex.hexdigest(), dl.hexdigest()


def fetch_devices():
    try:
        with urllib.request.urlopen(OFFICIAL_MANIFEST, timeout=20) as r:
            devices = json.load(r).get("imager", {}).get("devices")
        if devices:
            return devices, True
    except Exception as e:  # noqa: BLE001
        print(f"note: couldn't fetch official device list ({e}); using built-in list", file=sys.stderr)
    return FALLBACK_DEVICES, False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", help="HamClock .img.xz file(s)")
    ap.add_argument("-o", "--output", default="hamclock.rpi-imager-manifest")
    ap.add_argument("--init-format", choices=["systemd", "cloudinit", "cloudinit-rpi", "rpi-preseed"],
                    help="override the format guessed from the filename (bookworm/trixie)")
    ap.add_argument("--url", help="download URL to put in the manifest instead of a local file:// URI "
                    "(single image only; used by CI for release assets)")
    ap.add_argument("--offline", action="store_true", help="don't fetch the official device list")
    args = ap.parse_args()
    if args.url and len(args.images) != 1:
        sys.exit("error: --url works with exactly one image")

    devices, official = ((FALLBACK_DEVICES, False) if args.offline else fetch_devices())
    all_tags = sorted({t for d in devices for t in d.get("tags", [])})

    entries = []
    for img in args.images:
        p = pathlib.Path(img).resolve()
        if not p.is_file() or not p.name.endswith(".img.xz"):
            sys.exit(f"error: {img} is not an existing .img.xz file")
        name = p.name
        init = args.init_format
        if not init:
            for codename, fmt in INIT_FORMATS.items():
                if codename in name.lower():
                    init = fmt
            if not init:
                sys.exit(f"error: can't tell bookworm/trixie from '{name}'; pass --init-format")
        is_64 = "arm64" in name.lower()
        tags = [t for t in all_tags if "64bit" in t] if is_64 else all_tags
        m = re.search(r"(\d{4}-\d{2}-\d{2})\.img\.xz$", name)
        date = m.group(1) if m else datetime.date.today().isoformat()

        print(f"hashing {name} ...", file=sys.stderr)
        ex_size, ex_sha, dl_sha = hash_image(p)
        entries.append({
            "name": "HamClock " + name[: -len(".img.xz")],
            "description": f"HamClock Pi image ({init} customisation)",
            "icon": "https://ohb.hamclock.app/favicon.ico",
            "url": args.url or p.as_uri(),
            "extract_size": ex_size,
            "extract_sha256": ex_sha,
            "image_download_size": p.stat().st_size,
            "image_download_sha256": dl_sha,
            "release_date": date,
            "init_format": init,
            "devices": tags,
            "capabilities": [],
        })

    manifest = {"imager": {"devices": devices}, "os_list": entries}
    with open(args.output, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"\nwrote {args.output} ({len(entries)} image(s)); "
          f"device list: {'official' if official else 'built-in fallback'}")
    print("Open it with Imager (double-click it, or rpi-imager --repo FILE), then choose the image from the list.")


if __name__ == "__main__":
    main()
