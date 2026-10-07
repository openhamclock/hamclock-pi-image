# HamClock Pi Image

Ready-to-flash Raspberry Pi OS images with [HamClock](https://ohb.hamclock.app) pre-installed and pre-configured — no manual setup, no typing commands on the Pi itself. Pick an image, flash it, plug it in.

This repo doesn't host HamClock's source — it's a build pipeline (GitHub Actions + a customized [`install-hc-rpi`](debian/install-hc-rpi) script) that produces complete, bootable `.img` files for six different HamClock/Raspberry Pi OS combinations.

---

## Quick Start

1. Go to the [Actions tab](../../actions/workflows/build-pi-images.yml) (or [Releases](../../releases) if a build has been published)
2. Download the image that matches what you want (see [Which image do I want?](#which-image-do-i-want) below)
3. Flash it with [Raspberry Pi Imager](#flashing-the-image) — **make sure to set your WiFi network in Imager's customization step if you're on the `web` variant**, or connect to the `HamClock-Setup` hotspot on first boot for any variant
4. Boot it up. That's it.

Default login is **`pi` / `pi`** — change it (`passwd`) once you're in, especially before leaving the device on a network you don't fully trust.

---

## Which image do I want?

Every image comes in two OS generations — **Trixie** (current Raspberry Pi OS) and **Bookworm** (previous) — and three "variants" that determine how you actually see/use HamClock:

| Variant | What it is | Needs a screen? | Needs a mouse? | Best for |
|---|---|---|---|---|
| **`web`** | Headless. HamClock runs as a small web server; you access it from any browser on your network. | No | No | Pi Zero 2 W, headless servers, anything without a monitor |
| **`desktop`** | Full X11 desktop, HamClock launches fullscreen automatically. Can open a real browser for links HamClock shows. | Yes (HDMI) | Yes | Pi 4/5 with a monitor, if you want click-through web links to actually work |
| **`fb0`** | Draws straight to the screen with no desktop environment at all — the lightest-weight way to get HamClock on a physical display. | Yes (HDMI) | Optional | Dedicated always-on displays, lower-RAM boards (Zero 2 W with a screen) |

**Six images total**, named like `hamclock-raspios-<os>-<variant>-<arch>`:

- `trixie-web-64bit`
- `trixie-desktop-64bit`
- `trixie-fb0-32bit`
- `bookworm-web-64bit`
- `bookworm-desktop-64bit`
- `bookworm-fb0-32bit`

> **Why is `fb0` 32-bit and the others 64-bit?** The `fb0` build matches a confirmed-working community recipe for the legacy Linux framebuffer, which historically has more reliable driver support at 32-bit. `web` and `desktop` have no such constraint, so they run 64-bit for better performance.

**Don't know what board you have or what you're using it for?** Default to `desktop` if you have a spare monitor+mouse sitting around and want the "normal" experience. Default to `web` if you don't, or if you're on a Pi Zero 2 W (only 512MB RAM — `desktop`'s full X11 stack is a lot to ask of it).

---

## Flashing the image

1. Download and open [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. **Choose Device** → your Pi model
3. **Choose OS** → scroll to the bottom → **Use custom** → select the `.img.xz` file you downloaded (no need to unzip it further — Imager reads `.xz` directly)
4. **Choose Storage** → your SD card
5. Click **Next**, then **Edit Settings** when prompted:
   - Set a hostname, and your own username/password if you don't want to use the built-in `pi`/`pi`
   - Set your WiFi SSID/password and country (skip this if you'd rather use the on-device WiFi setup described below)
   - Enable SSH if you want remote access (it's already enabled by default in the image itself)
6. Save, confirm, and let it write

**Recommended card:** 32GB+ microSD, A1/A2 rated, from a reputable brand (SanDisk, Samsung, Kingston). Cheap/counterfeit cards are a common source of write failures — if Raspberry Pi Imager reports a "media error" partway through, try a different card before assuming the image itself is bad.

**For `desktop` builds specifically:** enable **auto-login** in Imager's OS customization options. HamClock's autostart only fires once a desktop session actually begins — without auto-login, nobody's ever logged in for it to start.

---

## First boot

### No WiFi configured yet?

Every image broadcasts a temporary hotspot called **`HamClock-Setup`** if it can't find a known network. Connect to it from your phone or laptop, and a setup page should pop up automatically (same as hotel/airport WiFi login pages) letting you pick your real network and enter its password. No monitor, keyboard, or Raspberry Pi Imager customization required.

### Finding the device

- **`web` variant**: open a browser to `http://<the Pi's IP address>`. Check your router's device list, or try `http://raspberrypi.local` if your network supports mDNS.
- **`desktop` / `fb0` variants**: HamClock should appear directly on the connected screen within about 10–15 seconds of boot.

### Default login

**Username:** `pi` **Password:** `pi`

This is a well-known default, printed on purpose so it's easy to remember and hand to non-technical users — but it means anyone who knows this repo exists knows how to log into any device built from it, and SSH is enabled by default. **Run `passwd` and change it** once you're set up, especially if the device is reachable from outside your home network.

### First-run setup

HamClock will ask for your callsign and other basic info the first time it runs. **Make sure your WiFi is actually connected before going past this screen** — HamClock does an NTP time check as part of setup, and running it before the network has fully settled can cause it to hang. If it does hang, SSH in and restart it:
```bash
# web / fb0 variants:
sudo systemctl restart hamclock.service

# desktop variant:
pkill hamclock
```
This is generally a one-time hiccup during the very first run, not a recurring issue.

---

## Display notes (`desktop` variant)

- HamClock renders at a **fixed 5:3 aspect ratio** (800x480, 1600x960, 2400x1440, or 3200x1920 — all the same shape, just bigger). Almost all modern monitors/TVs are 16:9, so unless your screen happens to support an exact 5:3 mode, you'll either see small black bars on the sides (aspect ratio preserved, no distortion) or need to scale the display to fill the screen (below).
- **Fullscreen is automatic** — no need to dig into HamClock's Setup menu.
- To eliminate black bars by having your monitor's own scaler fill the screen:
  ```bash
  xrandr --output HDMI-1 --scale-from 1600x960 --display :0
  ```
  (replace `1600x960` with whatever size you built, and `HDMI-1` with your actual output name from running `xrandr` with no arguments). This is already wired into the image as a system-wide session hook — it should apply automatically on every login without you needing to run it by hand.
- Chromium is pre-installed so HamClock's "open a web link" features work out of the box.

## Display notes (`fb0` variant)

- Draws straight to `/dev/fb0` — no desktop, no window manager, lowest overhead.
- Runs as a systemd service (`hamclock.service`) with automatic crash recovery.
- If colors look wrong or the picture doesn't display correctly, some displays need a specific framebuffer color depth — this can be tuned via the `HC_FB_DEPTH` build variable (see below).

---

## Building your own image

Go to **Actions → Build HamClock Raspberry Pi images → Run workflow**. Options:

| Input | What it does | Default |
|---|---|---|
| `hamclock_version` | Pin a specific HamClock release (e.g. `4.22`) | blank = latest |
| `hamclock_size` | Build size: `all`, `800x480`, `1600x960`, `2400x1440`, or `3200x1920`. `all` builds every size for every variant | `all` |
| `autostart` | Whether HamClock starts automatically on boot | `y` |
| `publish_release` | Attach the built images to a GitHub Release instead of just a temporary workflow artifact | off |

With `hamclock_size` set to `all` (the default), each of the six variants is built at all four sizes — 24 images from one run. Pick a single size to get just six. Jobs run in parallel, but GitHub limits concurrent jobs (about 20 on free plans), so some will queue. Build time is roughly 30–90 minutes per image (compiling C++ inside an emulated ARM environment isn't fast). Image filenames include the size, e.g. `hamclock-trixie-web-arm64-1600x960-...`.

**Downloading what you built:** Actions tab → your run → scroll to **Artifacts**. Files are `.img.xz` (flash directly, no need to decompress) plus a `.sha256` checksum.

---

## What's actually in these images

A quick tour of what gets baked in beyond "HamClock is installed":

- **Default login** `pi`/`pi` via the same mechanism Raspberry Pi Imager itself uses, so the interactive first-boot setup wizard is skipped entirely
- **A welcome banner** on login with a security reminder about the default password
- **`en_US.UTF-8`** locale instead of Raspberry Pi OS's stock `en_GB.UTF-8`
- **WiFi onboarding** via [Comitup](https://github.com/davesteele/comitup) — the `HamClock-Setup` hotspot described above
- **Automatic crash recovery** — `web` and `fb0` run HamClock as a supervised systemd service that restarts on failure and re-restarts once the network genuinely comes online (not just "connected," but confirmed internet-reachable)
- **SSH enabled by default**
- **A custom boot splash** (`desktop` variant only) replacing the default Raspberry Pi Software logo

---

## Troubleshooting

**"Media error detected" while flashing** — almost always the SD card, not the image. Try a different card or reader; counterfeit/cheap cards commonly misreport their real capacity.

**WiFi hotspot never appears** — check `nmcli device status`; the WiFi interface should show as `disconnected` (available), not `unavailable`. If it's `unavailable`, the radio itself isn't ready — check `rfkill list` and `journalctl -u wifi-on.service`.

**HamClock isn't responsive / frozen after WiFi setup** — this was a real bug in earlier builds (the process could start before the network was actually ready) and has since been fixed via automatic restart-on-connect. If you're still hitting it, restart the service manually:
```bash
sudo systemctl restart hamclock.service   # web / fb0
```

**`desktop` variant boots to a blank/black screen or the wrong session** — check whether it fell back to a minimal Openbox-only session (a sign the primary desktop session failed to start) vs. genuinely nothing rendering; these have different causes. Check `journalctl -b` around the display-manager/session-startup lines for specifics.

**No desktop icon** — this only affects accounts that existed *before* an image update added the icon fix. A genuinely fresh flash + first boot should have it automatically; if not, check `/etc/skel/Desktop/` exists in the image and that your account is actually new.

---

## Credits

- [HamClock](https://ohb.hamclock.app) by the original author, distributed via the [Open HamClock Backend](https://github.com/openhamclock/hamclock) project
- [`pguyot/arm-runner-action`](https://github.com/pguyot/arm-runner-action) for the qemu-based image build pipeline
- [Comitup](https://github.com/davesteele/comitup) for WiFi captive-portal onboarding
- [Raspberry Pi OS](https://www.raspberrypi.com/software/) images from the Raspberry Pi Foundation

## Security note

These images ship with a well-known default password and SSH enabled out of the box, by design, to keep setup simple. This is a reasonable tradeoff for personal use or devices you control — **change the password** (`passwd`) before deploying anywhere a stranger could reach the device, and don't publish built images somewhere untrusted people could grab one expecting that default to still be in place.
