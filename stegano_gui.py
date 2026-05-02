#!/usr/bin/env python3
"""
Advanced Image Steganography Tool — Graphical User Interface
Requires: tkinter (stdlib), Pillow, numpy
Optional: pycryptodome, PyWavelets, scipy
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys

# Make sure stegano_tool is importable from the same directory
sys.path.insert(0, os.path.dirname(__file__))
import stegano_tool as st

from PIL import Image, ImageTk
import numpy as np


DARK_BG    = "#0d1117"
PANEL_BG   = "#161b22"
BORDER     = "#30363d"
ACCENT     = "#58a6ff"
ACCENT2    = "#3fb950"
WARNING    = "#f85149"
TEXT_MAIN  = "#e6edf3"
TEXT_DIM   = "#8b949e"
FONT_MONO  = ("Consolas", 10)
FONT_UI    = ("Segoe UI", 10)
FONT_HEAD  = ("Segoe UI Semibold", 11)


class SteganoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Advanced Steganography Tool")
        self.geometry("980x720")
        self.configure(bg=DARK_BG)
        self.resizable(True, True)

        self.cover_path  = tk.StringVar()
        self.stego_path  = tk.StringVar()
        self.out_path    = tk.StringVar()
        self.method      = tk.StringVar(value="lsb")
        self.lsb_bits    = tk.IntVar(value=1)
        self.alpha       = tk.DoubleVar(value=15.0)
        self.password    = tk.StringVar()
        self.show_metrics = tk.BooleanVar(value=True)

        self._build_ui()

    # ── UI CONSTRUCTION ──────────────────────────────────────────────────

    def _build_ui(self):
        # Header bar
        header = tk.Frame(self, bg=PANEL_BG, pady=12)
        header.pack(fill=tk.X)
        tk.Label(header, text="🔐  Advanced Image Steganography Tool",
                 bg=PANEL_BG, fg=ACCENT, font=("Segoe UI Semibold", 15)).pack(side=tk.LEFT, padx=18)
        tk.Label(header, text="LSB · DCT · DWT · AES",
                 bg=PANEL_BG, fg=TEXT_DIM, font=FONT_UI).pack(side=tk.RIGHT, padx=18)

        # Notebook
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook",       background=DARK_BG, borderwidth=0)
        style.configure("TNotebook.Tab",   background=PANEL_BG, foreground=TEXT_DIM,
                        padding=[14, 6], font=FONT_UI)
        style.map("TNotebook.Tab",
                  background=[("selected", DARK_BG)],
                  foreground=[("selected", ACCENT)])

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        self.enc_frame = tk.Frame(nb, bg=DARK_BG)
        self.dec_frame = tk.Frame(nb, bg=DARK_BG)
        self.cap_frame = tk.Frame(nb, bg=DARK_BG)
        nb.add(self.enc_frame, text="  Encode  ")
        nb.add(self.dec_frame, text="  Decode  ")
        nb.add(self.cap_frame, text="  Capacity  ")

        self._build_encode_tab()
        self._build_decode_tab()
        self._build_capacity_tab()

        # Log panel
        log_frame = tk.Frame(self, bg=PANEL_BG, pady=6)
        log_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(log_frame, text="  Output Log", bg=PANEL_BG, fg=TEXT_DIM,
                 font=FONT_HEAD).pack(anchor=tk.W, padx=8)
        self.log = scrolledtext.ScrolledText(log_frame, height=7, bg="#010409",
                                             fg=TEXT_MAIN, font=FONT_MONO,
                                             insertbackground=ACCENT,
                                             relief=tk.FLAT, borderwidth=0)
        self.log.pack(fill=tk.X, padx=8, pady=4)
        self._log("Ready. Select a tab to begin.", color=TEXT_DIM)

    def _section(self, parent, text):
        f = tk.LabelFrame(parent, text=f"  {text}  ",
                          bg=DARK_BG, fg=ACCENT,
                          font=FONT_HEAD, bd=1, relief=tk.SOLID,
                          labelanchor="nw")
        f.pack(fill=tk.X, padx=10, pady=6)
        return f

    def _row(self, parent, label, widget_fn, **kw):
        row = tk.Frame(parent, bg=DARK_BG)
        row.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(row, text=label, bg=DARK_BG, fg=TEXT_DIM,
                 font=FONT_UI, width=20, anchor=tk.W).pack(side=tk.LEFT)
        widget_fn(row, **kw)
        return row

    def _entry(self, parent, textvariable, **kw):
        e = tk.Entry(parent, textvariable=textvariable,
                     bg=PANEL_BG, fg=TEXT_MAIN, insertbackground=ACCENT,
                     relief=tk.FLAT, font=FONT_MONO, **kw)
        e.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 4))
        return e

    def _btn(self, parent, text, cmd, color=ACCENT, width=12):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=color, fg="#fff", font=FONT_UI,
                      activebackground=DARK_BG, activeforeground=color,
                      relief=tk.FLAT, cursor="hand2", width=width, pady=3)
        b.pack(side=tk.LEFT, padx=2)
        return b

    # ── ENCODE TAB ───────────────────────────────────────────────────────

    def _build_encode_tab(self):
        p = self.enc_frame

        s1 = self._section(p, "Input")
        self._row(s1, "Cover Image", lambda r: [
            self._entry(r, self.cover_path, width=55),
            self._btn(r, "Browse", self._browse_cover, width=8)
        ])

        s2 = self._section(p, "Secret Message")
        msg_frame = tk.Frame(s2, bg=DARK_BG)
        msg_frame.pack(fill=tk.BOTH, padx=10, pady=4)
        self.msg_text = tk.Text(msg_frame, height=5, bg=PANEL_BG, fg=TEXT_MAIN,
                                font=FONT_MONO, relief=tk.FLAT, insertbackground=ACCENT)
        self.msg_text.pack(fill=tk.BOTH)

        s3 = self._section(p, "Settings")
        self._row(s3, "Method", lambda r: [
            ttk.Combobox(r, textvariable=self.method, values=["lsb","dct","dwt"],
                         state="readonly", width=10, font=FONT_UI).pack(side=tk.LEFT, padx=4),
            tk.Label(r, text=" LSB bits:", bg=DARK_BG, fg=TEXT_DIM, font=FONT_UI).pack(side=tk.LEFT),
            ttk.Spinbox(r, from_=1, to=4, increment=1, textvariable=self.lsb_bits,
                        width=4, values=[1,2,4]).pack(side=tk.LEFT, padx=4),
            tk.Label(r, text=" DCT/DWT alpha:", bg=DARK_BG, fg=TEXT_DIM, font=FONT_UI).pack(side=tk.LEFT),
            tk.Entry(r, textvariable=self.alpha, width=6,
                     bg=PANEL_BG, fg=TEXT_MAIN, font=FONT_MONO, relief=tk.FLAT).pack(side=tk.LEFT)
        ])
        self._row(s3, "Password (AES)", lambda r: self._entry(r, self.password, show="●", width=30))
        self._row(s3, "Output Path", lambda r: [
            self._entry(r, self.out_path, width=45),
            self._btn(r, "Browse", self._browse_out_enc, width=8)
        ])
        tk.Checkbutton(s3, text=" Show quality metrics (PSNR / SSIM)",
                       variable=self.show_metrics,
                       bg=DARK_BG, fg=TEXT_DIM, selectcolor=PANEL_BG,
                       activebackground=DARK_BG, font=FONT_UI).pack(anchor=tk.W, padx=10)

        btn_row = tk.Frame(p, bg=DARK_BG)
        btn_row.pack(pady=10)
        self._btn(btn_row, "▶  Encode", self._run_encode, color=ACCENT2, width=18)

    # ── DECODE TAB ───────────────────────────────────────────────────────

    def _build_decode_tab(self):
        p = self.dec_frame

        s1 = self._section(p, "Stego Image")
        self._row(s1, "Stego Image", lambda r: [
            self._entry(r, self.stego_path, width=55),
            self._btn(r, "Browse", self._browse_stego, width=8)
        ])

        s2 = self._section(p, "Settings")
        self._row(s2, "Method", lambda r: [
            ttk.Combobox(r, textvariable=self.method, values=["lsb","dct","dwt"],
                         state="readonly", width=10, font=FONT_UI).pack(side=tk.LEFT, padx=4)
        ])
        self._row(s2, "LSB bits", lambda r:
            ttk.Spinbox(r, from_=1, to=4, increment=1, textvariable=self.lsb_bits,
                        width=4, values=[1,2,4]).pack(side=tk.LEFT, padx=4))
        self._row(s2, "Password (AES)", lambda r: self._entry(r, self.password, show="●", width=30))

        btn_row = tk.Frame(p, bg=DARK_BG)
        btn_row.pack(pady=10)
        self._btn(btn_row, "▶  Decode", self._run_decode, color=ACCENT, width=18)

        s3 = self._section(p, "Extracted Message")
        self.result_text = tk.Text(s3, height=8, bg=PANEL_BG, fg=ACCENT2,
                                   font=FONT_MONO, relief=tk.FLAT)
        self.result_text.pack(fill=tk.BOTH, padx=10, pady=6)

    # ── CAPACITY TAB ─────────────────────────────────────────────────────

    def _build_capacity_tab(self):
        p = self.cap_frame
        self.cap_img_path = tk.StringVar()

        s1 = self._section(p, "Image")
        self._row(s1, "Image Path", lambda r: [
            self._entry(r, self.cap_img_path, width=55),
            self._btn(r, "Browse", self._browse_cap, width=8)
        ])

        btn_row = tk.Frame(p, bg=DARK_BG)
        btn_row.pack(pady=8)
        self._btn(btn_row, "▶  Analyse", self._run_capacity, color="#d29922", width=18)

        s2 = self._section(p, "Results")
        self.cap_result = tk.Text(s2, height=10, bg=PANEL_BG, fg=TEXT_MAIN,
                                  font=FONT_MONO, relief=tk.FLAT)
        self.cap_result.pack(fill=tk.BOTH, padx=10, pady=6)

    # ── BROWSE HELPERS ───────────────────────────────────────────────────

    def _browse_cover(self):
        p = filedialog.askopenfilename(filetypes=[("Images","*.png *.bmp *.tiff *.jpg *.jpeg")])
        if p: self.cover_path.set(p)

    def _browse_stego(self):
        p = filedialog.askopenfilename(filetypes=[("Images","*.png *.bmp *.tiff *.jpg *.jpeg")])
        if p: self.stego_path.set(p)

    def _browse_out_enc(self):
        p = filedialog.asksaveasfilename(defaultextension=".png",
                                         filetypes=[("PNG","*.png"),("BMP","*.bmp")])
        if p: self.out_path.set(p)

    def _browse_cap(self):
        p = filedialog.askopenfilename(filetypes=[("Images","*.png *.bmp *.tiff *.jpg *.jpeg")])
        if p: self.cap_img_path.set(p)

    # ── ACTIONS ─────────────────────────────────────────────────────────

    def _run_encode(self):
        threading.Thread(target=self._encode_thread, daemon=True).start()

    def _encode_thread(self):
        try:
            cover = self.cover_path.get()
            msg   = self.msg_text.get("1.0", tk.END).strip()
            out   = self.out_path.get() or f"stego_{os.path.basename(cover)}"
            pwd   = self.password.get() or None
            meth  = self.method.get()

            if not cover:
                raise ValueError("Please select a cover image.")
            if not msg:
                raise ValueError("Please enter a secret message.")

            self._log(f"Loading cover image: {cover}")
            img = Image.open(cover)
            orig = img.copy()

            self._log(f"Encoding with {meth.upper()}...")
            if meth == 'lsb':
                result = st.lsb_encode(img, msg, pwd, bits=self.lsb_bits.get())
            elif meth == 'dct':
                result = st.dct_encode(img, msg, pwd, alpha=self.alpha.get())
            elif meth == 'dwt':
                result = st.dwt_encode(img, msg, pwd, alpha=self.alpha.get())

            result.save(out)
            self._log(f"✔ Stego image saved: {out}", color=ACCENT2)

            if self.show_metrics.get():
                psnr = st.compute_psnr(orig, result)
                ssim = st.compute_ssim(orig, result)
                self._log(f"  PSNR : {psnr:.2f} dB", color=ACCENT)
                self._log(f"  SSIM : {ssim:.6f}", color=ACCENT)

        except Exception as e:
            self._log(f"✖ Error: {e}", color=WARNING)

    def _run_decode(self):
        threading.Thread(target=self._decode_thread, daemon=True).start()

    def _decode_thread(self):
        try:
            stego = self.stego_path.get()
            pwd   = self.password.get() or None
            meth  = self.method.get()

            if not stego:
                raise ValueError("Please select a stego image.")

            self._log(f"Decoding {meth.upper()} from: {stego}")
            img = Image.open(stego)

            if meth == 'lsb':
                msg = st.lsb_decode(img, pwd, bits=self.lsb_bits.get())
            elif meth == 'dct':
                msg = st.dct_decode(img, pwd, alpha=self.alpha.get())
            elif meth == 'dwt':
                msg = st.dwt_decode(img, pwd, alpha=self.alpha.get())

            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, msg)
            self._log(f"✔ Message extracted ({len(msg)} chars)", color=ACCENT2)

        except Exception as e:
            self._log(f"✖ Error: {e}", color=WARNING)

    def _run_capacity(self):
        path = self.cap_img_path.get()
        if not path:
            messagebox.showwarning("No Image", "Please select an image first.")
            return
        try:
            img = Image.open(path)
            arr = np.array(img)
            h, w = arr.shape[:2]
            total = arr.size
            lsb1 = total // 8
            lsb2 = total // 4
            lsb4 = total // 2
            blocks = (h // 8) * (w // 8)
            dct_bytes = blocks // 8

            lines = [
                f"Image         : {os.path.basename(path)}",
                f"Dimensions    : {w} × {h}  ({img.mode})",
                f"Channel bytes : {total:,}",
                "",
                f"LSB-1 capacity : {lsb1:,} bytes  ({lsb1/1024:.1f} KB)",
                f"LSB-2 capacity : {lsb2:,} bytes  ({lsb2/1024:.1f} KB)",
                f"LSB-4 capacity : {lsb4:,} bytes  ({lsb4/1024:.1f} KB)",
                "",
                f"8×8 blocks     : {blocks:,}",
                f"DCT/DWT approx : {dct_bytes:,} bytes  ({dct_bytes/1024:.2f} KB)",
            ]
            self.cap_result.delete("1.0", tk.END)
            self.cap_result.insert(tk.END, "\n".join(lines))
        except Exception as e:
            self._log(f"✖ {e}", color=WARNING)

    # ── LOG HELPER ───────────────────────────────────────────────────────

    def _log(self, msg, color=TEXT_MAIN):
        self.log.configure(state=tk.NORMAL)
        tag = f"tag_{color}"
        self.log.tag_configure(tag, foreground=color)
        self.log.insert(tk.END, msg + "\n", tag)
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)


def main():
    app = SteganoApp()
    app.mainloop()


if __name__ == "__main__":
    main()
