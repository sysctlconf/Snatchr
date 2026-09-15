"""
Snatchr - a video grabber with a face.
(c) 2026 MODDAXX. All rights reserved.
"""
import os
import sys
import threading
import queue
import math
import webbrowser

import customtkinter as ctk
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from core import downloader as dl

ASSETS = os.path.join(os.path.dirname(__file__), "assets")

ACCENTS = {
    "Violet":  "#7C3AED",
    "Pink":    "#EC4899",
    "Orange":  "#FB923C",
    "Cyan":    "#22D3EE",
    "Green":   "#4ADE80",
}

BG = "#121218"
PANEL = "#1B1B24"
PANEL_LIGHT = "#24242F"
TEXT_MUTED = "#8A8A99"

ctk.set_appearance_mode("dark")


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def lerp_color(c1, c2, t):
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return f"#{int(r1+(r2-r1)*t):02x}{int(g1+(g2-g1)*t):02x}{int(b1+(b2-b1)*t):02x}"


class SpinnerRing(ctk.CTkCanvas):
    """A small animated arc that spins while work happens in the background."""
    def __init__(self, master, size=28, color="#EC4899", **kwargs):
        super().__init__(master, width=size, height=size, bg=PANEL,
                          highlightthickness=0, **kwargs)
        self.size = size
        self.color = color
        self.angle = 0
        self._running = False

    def set_color(self, color):
        self.color = color

    def start(self):
        self._running = True
        self._animate()

    def stop(self):
        self._running = False
        self.delete("all")

    def _animate(self):
        if not self._running:
            return
        self.delete("all")
        pad = 3
        self.create_arc(pad, pad, self.size - pad, self.size - pad,
                         start=self.angle, extent=110,
                         style="arc", outline=self.color, width=3)
        self.angle = (self.angle - 12) % 360
        self.after(30, self._animate)


class FormatRow(ctk.CTkFrame):
    """One selectable quality row."""
    def __init__(self, master, fmt, on_select, accent, **kwargs):
        super().__init__(master, fg_color=PANEL_LIGHT, corner_radius=10,
                          cursor="hand2", **kwargs)
        self.fmt = fmt
        self.on_select = on_select
        self.accent = accent
        self.selected = False

        fps_txt = f" · {int(fmt['fps'])}fps" if fmt.get("fps") else ""
        audio_txt = "with audio" if fmt["has_audio"] else "video only (auto-merged)"

        self.res_label = ctk.CTkLabel(
            self, text=f"{fmt['resolution']}{fps_txt}",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w"
        )
        self.res_label.grid(row=0, column=0, sticky="w", padx=14, pady=(10, 0))

        self.sub_label = ctk.CTkLabel(
            self, text=f"{dl.format_size(fmt['filesize'])}  ·  {audio_txt}",
            font=ctk.CTkFont(size=12), text_color=TEXT_MUTED, anchor="w"
        )
        self.sub_label.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))

        self.grid_columnconfigure(0, weight=1)

        for widget in (self, self.res_label, self.sub_label):
            widget.bind("<Button-1>", lambda e: self.on_select(self))

    def set_selected(self, selected):
        self.selected = selected
        self.configure(fg_color=self.accent if selected else PANEL_LIGHT)
        text_color = "#FFFFFF" if selected else ("#FFFFFF")
        self.res_label.configure(text_color=text_color)


class Snatchr(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)  # borderless -> we draw our own title bar
        self.geometry("560x680+300+120")
        self.configure(fg_color=BG)
        self.attributes("-alpha", 0.0)  # fade in on launch

        self.accent_name = "Pink"
        self.accent = ACCENTS[self.accent_name]

        self.video_info = {}
        self.formats = []
        self.selected_row = None
        self.msg_queue = queue.Queue()

        self._build_title_bar()
        self._build_body()
        self._poll_queue()
        self._fade_in()

    # ---------- window chrome ----------
    def _build_title_bar(self):
        bar = ctk.CTkFrame(self, height=44, fg_color=PANEL, corner_radius=0)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        icon_img = ctk.CTkImage(Image.open(os.path.join(ASSETS, "logo_icon.png")),
                                 size=(22, 22))
        ctk.CTkLabel(bar, image=icon_img, text="").pack(side="left", padx=(14, 6))
        ctk.CTkLabel(bar, text="Snatchr", font=ctk.CTkFont(size=14, weight="bold")
                     ).pack(side="left")

        close_btn = ctk.CTkButton(bar, text="✕", width=32, height=28, fg_color="transparent",
                                   hover_color="#E11D48", command=self.destroy)
        close_btn.pack(side="right", padx=(0, 8))
        min_btn = ctk.CTkButton(bar, text="—", width=32, height=28, fg_color="transparent",
                                 hover_color=PANEL_LIGHT, command=self._minimize)
        min_btn.pack(side="right")

        # drag anywhere on the bar
        for widget in (bar,):
            widget.bind("<ButtonPress-1>", self._start_move)
            widget.bind("<B1-Motion>", self._do_move)

    def _minimize(self):
        self.overrideredirect(False)
        self.iconify()
        self.bind("<Map>", self._on_restore)

    def _on_restore(self, event):
        self.overrideredirect(True)
        self.unbind("<Map>")

    def _start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_move(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")

    def _fade_in(self, alpha=0.0):
        alpha = min(alpha + 0.08, 1.0)
        self.attributes("-alpha", alpha)
        if alpha < 1.0:
            self.after(15, lambda: self._fade_in(alpha))

    # ---------- body ----------
    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # banner
        banner_img = ctk.CTkImage(Image.open(os.path.join(ASSETS, "logo_banner.png")),
                                   size=(300, 79))
        ctk.CTkLabel(body, image=banner_img, text="").pack(anchor="w", pady=(0, 14))

        # accent color picker
        picker_row = ctk.CTkFrame(body, fg_color="transparent")
        picker_row.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(picker_row, text="Theme", font=ctk.CTkFont(size=12),
                     text_color=TEXT_MUTED).pack(side="left", padx=(0, 10))
        self.swatch_buttons = {}
        for name, color in ACCENTS.items():
            b = ctk.CTkButton(picker_row, text="", width=22, height=22, corner_radius=11,
                               fg_color=color, hover_color=color,
                               border_width=2 if name == self.accent_name else 0,
                               border_color="#FFFFFF",
                               command=lambda n=name: self._set_accent(n))
            b.pack(side="left", padx=4)
            self.swatch_buttons[name] = b

        # url entry row
        url_row = ctk.CTkFrame(body, fg_color="transparent")
        url_row.pack(fill="x", pady=(0, 10))
        self.url_entry = ctk.CTkEntry(url_row, placeholder_text="Paste a video URL...",
                                       height=42, corner_radius=10, fg_color=PANEL_LIGHT,
                                       border_width=0)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.url_entry.bind("<Return>", lambda e: self._fetch())
        self.fetch_btn = ctk.CTkButton(url_row, text="Fetch", width=90, height=42,
                                        corner_radius=10, fg_color=self.accent,
                                        hover_color=self._darken(self.accent),
                                        command=self._fetch)
        self.fetch_btn.pack(side="right")

        # status / spinner row
        status_row = ctk.CTkFrame(body, fg_color="transparent", height=30)
        status_row.pack(fill="x")
        self.spinner = SpinnerRing(status_row, size=20, color=self.accent)
        self.status_label = ctk.CTkLabel(status_row, text="Paste a link to get started.",
                                          font=ctk.CTkFont(size=12), text_color=TEXT_MUTED,
                                          anchor="w")
        self.status_label.pack(side="left", padx=(0, 6))

        # scrollable format list
        self.list_frame = ctk.CTkScrollableFrame(body, fg_color=PANEL, corner_radius=12)
        self.list_frame.pack(fill="both", expand=True, pady=(10, 10))
        self.empty_label = ctk.CTkLabel(self.list_frame, text="No video loaded yet",
                                         text_color=TEXT_MUTED)
        self.empty_label.pack(pady=30)

        # progress bar
        self.progress = ctk.CTkProgressBar(body, height=10, corner_radius=6,
                                            fg_color=PANEL_LIGHT, progress_color=self.accent)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 10))

        self.download_btn = ctk.CTkButton(body, text="Snatch it", height=46, corner_radius=12,
                                           font=ctk.CTkFont(size=15, weight="bold"),
                                           fg_color=self.accent, hover_color=self._darken(self.accent),
                                           state="disabled", command=self._start_download)
        self.download_btn.pack(fill="x")

        # footer / copyright
        footer = ctk.CTkLabel(body, text="Snatchr © 2026 MODDAXX. All rights reserved.",
                               font=ctk.CTkFont(size=10), text_color=TEXT_MUTED)
        footer.pack(pady=(10, 0))

    # ---------- accent theming ----------
    def _darken(self, hex_color, factor=0.8):
        r, g, b = hex_to_rgb(hex_color)
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

    def _set_accent(self, name):
        self.accent_name = name
        self.accent = ACCENTS[name]
        for n, btn in self.swatch_buttons.items():
            btn.configure(border_width=2 if n == name else 0)
        self.fetch_btn.configure(fg_color=self.accent, hover_color=self._darken(self.accent))
        self.download_btn.configure(fg_color=self.accent, hover_color=self._darken(self.accent))
        self.progress.configure(progress_color=self.accent)
        self.spinner.set_color(self.accent)
        if self.selected_row:
            self.selected_row.accent = self.accent
            self.selected_row.set_selected(True)

    # ---------- fetch ----------
    def _fetch(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        if not dl.has_ytdlp():
            self._set_status("yt-dlp isn't installed. Run: winget install yt-dlp", error=True)
            return

        self.fetch_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        self._clear_list()
        self._set_status("Fetching video info...")
        self.spinner.pack(side="left")
        self.spinner.start()

        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _fetch_worker(self, url):
        info, error = dl.get_video_info(url)
        self.msg_queue.put(("fetch_done", info, error))

    def _clear_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.selected_row = None

    def _set_status(self, text, error=False):
        self.status_label.configure(text=text, text_color="#F87171" if error else TEXT_MUTED)

    # ---------- selection ----------
    def _on_format_select(self, row: FormatRow):
        if self.selected_row and self.selected_row is not row:
            self.selected_row.set_selected(False)
        row.set_selected(True)
        self.selected_row = row
        self.download_btn.configure(state="normal")

    # ---------- download ----------
    def _start_download(self):
        if not self.selected_row:
            return
        fmt_id = self.selected_row.fmt["format_id"]
        url = self.url_entry.get().strip()
        out_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(out_dir, exist_ok=True)

        self.download_btn.configure(state="disabled", text="Snatching...")
        self.progress.set(0)
        self._set_status("Starting download...")

        threading.Thread(target=self._download_worker, args=(url, fmt_id, out_dir),
                          daemon=True).start()

    def _download_worker(self, url, fmt_id, out_dir):
        def on_progress(pct):
            self.msg_queue.put(("progress", pct))

        success, message = dl.download_video(url, fmt_id, out_dir, on_progress=on_progress)
        self.msg_queue.put(("download_done", success, message, out_dir))

    # ---------- message pump (keeps tkinter thread-safe) ----------
    def _poll_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                self._handle_msg(msg)
        except queue.Empty:
            pass
        self.after(50, self._poll_queue)

    def _handle_msg(self, msg):
        kind = msg[0]

        if kind == "fetch_done":
            _, info, error = msg
            self.spinner.stop()
            self.spinner.pack_forget()
            self.fetch_btn.configure(state="normal")

            if error:
                self._set_status(f"Error: {error}", error=True)
                return

            self.video_info = info
            formats = dl.get_mp4_formats(info)
            if not formats:
                self._set_status("No mp4 formats found for that URL.", error=True)
                return

            title = info.get("title", "video")
            self._set_status(f"Loaded: {title[:48]}")
            self._populate_formats(formats)

        elif kind == "progress":
            pct = msg[1]
            self.progress.set(pct / 100)
            self._set_status(f"Downloading... {pct:.0f}%")

        elif kind == "download_done":
            _, success, message, out_dir = msg
            self.download_btn.configure(state="normal", text="Snatch it")
            if success:
                self.progress.set(1.0)
                self._set_status(f"Saved to {out_dir}")
            else:
                self._set_status(f"Failed: {message}", error=True)

    def _populate_formats(self, formats):
        self.empty_label.pack_forget()
        for f in formats:
            row = FormatRow(self.list_frame, f, self._on_format_select, self.accent)
            row.pack(fill="x", padx=8, pady=5)


if __name__ == "__main__":
    app = Snatchr()
    app.mainloop()
