# Snatchr

*grab it. don't ask.*

A desktop video downloader with a custom-drawn window: draggable borderless title bar, live-switchable accent colors, an animated loading ring, and a real generated logo — built on top of `yt-dlp`.

**© 2026 MODDAXX. All rights reserved.**

---

## Running it (development)

```bash
pip install -r requirements.txt
```

You also need two things `yt-dlp` itself depends on:

- **yt-dlp binary** (not just the Python package) — `winget install yt-dlp`
- **ffmpeg** — `winget install ffmpeg` (needed to merge video-only + audio streams into one file)

Then run:

```bash
python app.py
```

## Project structure

```
Snatchr/
├── app.py              # GUI - window, theming, format list, progress
├── core/
│   └── downloader.py   # yt-dlp wrapper - fetch info, list formats, download
├── generate_assets.py  # Regenerates the logo/icon/banner if you want to restyle them
├── assets/
│   ├── logo_icon.png   # Square app icon (also used as the .ico source)
│   ├── logo_banner.png # Header wordmark shown inside the app
│   └── icon.ico         # Windows icon (multi-resolution)
├── requirements.txt
├── build_exe.bat        # Packages everything into dist\Snatchr.exe
└── README.md
```

## Packaging as a sellable .exe

```bash
pip install -r requirements.txt
build_exe.bat
```

This uses PyInstaller to produce a single `Snatchr.exe` in `dist\` with your icon baked in, so it can be handed to a customer without them installing Python. **They will still need `yt-dlp` and `ffmpeg` on their system** (or you bundle those binaries alongside the exe — see below).

### Bundling yt-dlp/ffmpeg so customers don't install anything

Right now the app shells out to `yt-dlp` and `ffmpeg` on the system PATH. For a fully self-contained product:

1. Download `yt-dlp.exe` and `ffmpeg.exe` and drop them in the project folder.
2. Add them to `build_exe.bat` with extra `--add-binary "yt-dlp.exe;."` flags.
3. In `core/downloader.py`, change the subprocess calls from `"yt-dlp"` to the bundled path (e.g. resolve it relative to `sys.executable` when frozen).

Happy to wire this up for you if you want the fully self-contained version.

## Customizing the brand

Edit the constants at the top of `generate_assets.py` (`BRAND_STOPS` for the gradient) and re-run:

```bash
python generate_assets.py
```

Accent color swatches shown in-app live in `ACCENTS` at the top of `app.py`.

## A note before you sell this

- `yt-dlp` is released under **The Unlicense** (public domain) — no restriction on using it inside a commercial tool.
- Downloading from YouTube may conflict with YouTube's Terms of Service depending on what's downloaded and how it's used — that's between you, your customers, and YouTube; this tool doesn't circumvent DRM or paywalled content.
- You own everything in `app.py`, `core/`, and the generated assets — attach whatever license/EULA you want for Snatchr itself.
# Snatchr
