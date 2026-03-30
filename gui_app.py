#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web Crawler GUI Application - Desktop Pro style layout.
"""

import os
import platform
import sys

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

# Ensure src directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Configure DPI awareness for Windows
if platform.system() == "Windows":
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from crawler.gui.theme import Theme
from crawler.gui.view_model import MainViewModel
from crawler.utils.proxy_config import ProxyConfig
from crawler.utils.url_validator import URLValidator


class ModernButton(tk.Canvas):
    """Canvas button with rounded corners and hover state."""

    def __init__(
        self,
        parent,
        text,
        command,
        bg_color="#137FEC",
        hover_color="#2A8CF2",
        fg_color="#FFFFFF",
        disabled_bg="#2A3643",
        width=120,
        height=36,
        radius=10,
        **kwargs,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent["bg"],
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.command = command
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.fg_color = fg_color
        self.disabled_bg = disabled_bg
        self.text = text
        self.radius = radius
        self.enabled = True

        self.rect = self._round_rectangle(0, 0, width, height, radius=radius, fill=bg_color, outline="")
        self.text_item = self.create_text(
            width / 2,
            height / 2,
            text=text,
            fill=fg_color,
            font=Theme.FONTS["button"],
            tags="label",
        )

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _round_rectangle(self, x1, y1, x2, y2, radius=10, **kwargs):
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_enter(self, _event):
        if self.enabled:
            self.itemconfig(self.rect, fill=self.hover_color)

    def _on_leave(self, _event):
        if self.enabled:
            self.itemconfig(self.rect, fill=self.bg_color)

    def _on_click(self, _event):
        if self.enabled and self.command:
            self.command()

    def set_state(self, state):
        self.enabled = state == "normal"
        if self.enabled:
            self.itemconfig(self.rect, fill=self.bg_color)
            self.itemconfig("label", fill=self.fg_color)
        else:
            self.itemconfig(self.rect, fill=self.disabled_bg)
            self.itemconfig("label", fill=Theme.COLORS["text_muted"])


class CrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()  # Hide window during UI construction to prevent flickering
        self.root.title("Content Extractor - Desktop Pro")
        self.root.geometry("1160x780")
        self.root.minsize(980, 640)
        self.root.configure(bg=Theme.COLORS["bg"])

        self.view_model = MainViewModel()
        self.view_model.on_property_changed = self.on_property_changed
        self.view_model.on_extraction_finished = self.on_extraction_finished

        self.status_var = tk.StringVar(value="Paste a URL and run extraction.")
        self.content_length_var = tk.StringVar(value="Character Count: 0")
        self.badge_var = tk.StringVar(value="SYSTEM READY")
        self.settings_dropdown = None

        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

        self._configure_styles()
        self.setup_ui()

        # Finalize all pending layout calculations, then show the fully-rendered window
        self.root.update_idletasks()
        self._center_window()
        self.root.deiconify()

    def _center_window(self):
        """Center the window on screen after layout is finalized."""
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _on_window_close(self):
        self.view_model.on_property_changed = lambda _prop: None
        self.view_model.on_extraction_finished = lambda _success: None
        self.root.destroy()

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Extraction.Horizontal.TProgressbar",
            troughcolor=Theme.COLORS["card_alt"],
            background=Theme.COLORS["primary"],
            bordercolor=Theme.COLORS["border"],
            lightcolor=Theme.COLORS["primary"],
            darkcolor=Theme.COLORS["primary"],
            thickness=6,
        )

    def setup_ui(self):
        self.main = tk.Frame(self.root, bg=Theme.COLORS["bg"])
        self.main.pack(fill=tk.BOTH, expand=True)

        self._create_header(self.main)
        self._create_results_panel(self.main)
        self._create_footer(self.main)

    def _create_header(self, parent):
        header = tk.Frame(parent, bg=Theme.COLORS["bg"])
        header.pack(fill=tk.X, padx=28, pady=(24, 14))

        top_row = tk.Frame(header, bg=Theme.COLORS["bg"])
        top_row.pack(fill=tk.X)

        title_wrap = tk.Frame(top_row, bg=Theme.COLORS["bg"])
        title_wrap.pack(side=tk.LEFT, fill=tk.X, expand=True)

        title = tk.Label(
            title_wrap,
            text="Extract Content",
            bg=Theme.COLORS["bg"],
            fg=Theme.COLORS["text_dark"],
            font=Theme.FONTS["header"],
        )
        title.pack(anchor=tk.W)

        subtitle = tk.Label(
            title_wrap,
            text="Paste any web URL to pull text, metadata, and media information instantly.",
            bg=Theme.COLORS["bg"],
            fg=Theme.COLORS["text_light"],
            font=Theme.FONTS["subheader"],
        )
        subtitle.pack(anchor=tk.W, pady=(4, 0))

        self.settings_btn = tk.Button(
            top_row,
            text="Settings v",
            command=self._show_settings_menu,
            bg=Theme.COLORS["card"],
            fg=Theme.COLORS["text_dark"],
            activebackground="#252B33",
            activeforeground=Theme.COLORS["text_dark"],
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=5,
            font=Theme.FONTS["label"],
            cursor="hand2",
        )
        self.settings_btn.pack(side=tk.RIGHT, anchor=tk.N, pady=4)

        self._create_extract_input(header)

    def _create_extract_input(self, parent):
        input_card = tk.Frame(
            parent,
            bg=Theme.COLORS["card"],
            highlightbackground=Theme.COLORS["border"],
            highlightthickness=1,
            bd=0,
        )
        input_card.pack(fill=tk.X, pady=(18, 0))

        inner = tk.Frame(input_card, bg=Theme.COLORS["card"])
        inner.pack(fill=tk.X, padx=16, pady=16)

        input_row = tk.Frame(inner, bg=Theme.COLORS["card"])
        input_row.pack(fill=tk.X)

        input_label = tk.Label(
            input_row,
            text="SOURCE URL",
            bg=Theme.COLORS["card"],
            fg=Theme.COLORS["text_muted"],
            font=Theme.FONTS["section"],
        )
        input_label.pack(anchor=tk.W)

        action_row = tk.Frame(inner, bg=Theme.COLORS["card"])
        action_row.pack(fill=tk.X, pady=(8, 0))

        entry_shell = tk.Frame(
            action_row,
            bg=Theme.COLORS["card_alt"],
            highlightbackground=Theme.COLORS["border"],
            highlightthickness=1,
        )
        entry_shell.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))

        entry_icon = tk.Label(
            entry_shell,
            text="URL",
            bg=Theme.COLORS["card_alt"],
            fg=Theme.COLORS["text_muted"],
            font=Theme.FONTS["label_bold"],
            width=4,
        )
        entry_icon.pack(side=tk.LEFT, padx=(10, 4))

        self.url_entry = tk.Entry(
            entry_shell,
            font=Theme.FONTS["label"],
            relief=tk.FLAT,
            bg=Theme.COLORS_ENTRY_BG,
            fg=Theme.COLORS["text_dark"],
            insertbackground=Theme.COLORS["text_dark"],
            disabledbackground=Theme.COLORS["card_alt"],
            disabledforeground=Theme.COLORS["text_muted"],
        )
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=10, padx=(0, 12))
        self.url_entry.bind("<Return>", lambda _e: self.start_extraction())
        self.url_entry.bind(
            "<FocusIn>",
            lambda _e: entry_shell.configure(highlightbackground=Theme.COLORS["primary"], highlightthickness=2),
        )
        self.url_entry.bind(
            "<FocusOut>",
            lambda _e: entry_shell.configure(highlightbackground=Theme.COLORS["border"], highlightthickness=1),
        )

        self.extract_btn = ModernButton(
            action_row,
            "Extract Content",
            self.start_extraction,
            bg_color=Theme.COLORS["primary"],
            hover_color=Theme.COLORS["primary_hover"],
            width=180,
            height=46,
            radius=12,
        )
        self.extract_btn.pack(side=tk.RIGHT)

    def _create_results_panel(self, parent):
        section = tk.Frame(parent, bg=Theme.COLORS["bg"])
        section.pack(fill=tk.BOTH, expand=True, padx=28, pady=(4, 12))

        section_head = tk.Frame(section, bg=Theme.COLORS["bg"])
        section_head.pack(fill=tk.X, pady=(0, 8))

        left_meta = tk.Frame(section_head, bg=Theme.COLORS["bg"])
        left_meta.pack(side=tk.LEFT)

        title = tk.Label(
            left_meta,
            text="EXTRACTED RESULTS",
            bg=Theme.COLORS["bg"],
            fg=Theme.COLORS["text_light"],
            font=Theme.FONTS["section"],
        )
        title.pack(side=tk.LEFT)

        self.badge_frame = tk.Frame(left_meta, bg=Theme.COLORS["badge_ready_bg"], padx=8, pady=2)
        self.badge_frame.pack(side=tk.LEFT, padx=(10, 0))

        self.badge_dot = tk.Label(
            self.badge_frame,
            text="o",
            bg=Theme.COLORS["badge_ready_bg"],
            fg=Theme.COLORS["success"],
            font=Theme.FONTS["footer"],
        )
        self.badge_dot.pack(side=tk.LEFT, padx=(0, 4))

        self.badge_label = tk.Label(
            self.badge_frame,
            textvariable=self.badge_var,
            bg=Theme.COLORS["badge_ready_bg"],
            fg=Theme.COLORS["success"],
            font=Theme.FONTS["footer"],
        )
        self.badge_label.pack(side=tk.LEFT)

        action_wrap = tk.Frame(section_head, bg=Theme.COLORS["bg"])
        action_wrap.pack(side=tk.RIGHT)

        self.copy_btn = ModernButton(
            action_wrap,
            "Copy All",
            self.copy_to_clipboard,
            bg_color=Theme.COLORS["secondary"],
            hover_color=Theme.COLORS["secondary_hover"],
            width=90,
            height=30,
            radius=8,
        )
        self.copy_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.copy_btn.set_state("disabled")

        self.clear_btn = ModernButton(
            action_wrap,
            "Clear",
            self.clear_result,
            bg_color=Theme.COLORS["secondary"],
            hover_color=Theme.COLORS["secondary_hover"],
            width=78,
            height=30,
            radius=8,
        )
        self.clear_btn.pack(side=tk.LEFT)

        status_row = tk.Frame(section, bg=Theme.COLORS["bg"])
        status_row.pack(fill=tk.X, pady=(0, 8))

        self.status_label = tk.Label(
            status_row,
            textvariable=self.status_var,
            bg=Theme.COLORS["bg"],
            fg=Theme.COLORS["text_muted"],
            font=Theme.FONTS["label"],
        )
        self.status_label.pack(side=tk.LEFT)

        self.progress_bar = ttk.Progressbar(
            status_row,
            mode="indeterminate",
            length=180,
            style="Extraction.Horizontal.TProgressbar",
        )

        viewer = tk.Frame(
            section,
            bg=Theme.COLORS["card_alt"],
            highlightbackground=Theme.COLORS["border"],
            highlightthickness=1,
        )
        viewer.pack(fill=tk.BOTH, expand=True)

        text_body = tk.Frame(viewer, bg=Theme.COLORS["card_alt"])
        text_body.pack(fill=tk.BOTH, expand=True, padx=1, pady=(1, 0))

        self.result_text = scrolledtext.ScrolledText(
            text_body,
            wrap=tk.WORD,
            font=Theme.FONTS["code"],
            relief=tk.FLAT,
            bg=Theme.COLORS["card_alt"],
            fg=Theme.COLORS["text_dark"],
            insertbackground=Theme.COLORS["text_dark"],
            padx=14,
            pady=14,
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        count_bar = tk.Frame(
            viewer,
            bg=Theme.COLORS["card"],
            height=24,
            highlightbackground=Theme.COLORS["border"],
            highlightthickness=1,
        )
        count_bar.pack(fill=tk.X, side=tk.BOTTOM)
        count_bar.pack_propagate(False)

        char_count_label = tk.Label(
            count_bar,
            textvariable=self.content_length_var,
            bg=Theme.COLORS["card"],
            fg=Theme.COLORS["text_muted"],
            font=Theme.FONTS["footer"],
        )
        char_count_label.pack(side=tk.RIGHT, padx=10, pady=5)

    def _create_footer(self, parent):
        footer = tk.Frame(
            parent,
            bg=Theme.COLORS["card_alt"],
            height=6,
            highlightbackground=Theme.COLORS["border"],
            highlightthickness=1,
        )
        footer.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)
        footer.pack_propagate(False)

    def _show_settings_menu(self):
        if self.settings_dropdown and self.settings_dropdown.winfo_exists():
            self._close_settings_menu()
            return

        menu_width = 160
        menu_height = 62
        self.settings_dropdown = tk.Toplevel(self.root)
        self.settings_dropdown.overrideredirect(True)
        self.settings_dropdown.configure(bg=Theme.COLORS["border"])

        x = self.settings_btn.winfo_rootx() + self.settings_btn.winfo_width() - menu_width
        y = self.settings_btn.winfo_rooty() + self.settings_btn.winfo_height() + 2
        x = max(4, min(x, self.root.winfo_screenwidth() - menu_width - 4))
        self.settings_dropdown.geometry(f"{menu_width}x{menu_height}+{x}+{y}")

        panel = tk.Frame(self.settings_dropdown, bg=Theme.COLORS["card"])
        panel.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        def add_menu_item(label_text, callback):
            item = tk.Button(
                panel,
                text=label_text,
                anchor=tk.W,
                command=lambda: self._run_settings_action(callback),
                bg=Theme.COLORS["card"],
                fg=Theme.COLORS["text_light"],
                activebackground="#1A3D66",
                activeforeground=Theme.COLORS["text_dark"],
                relief=tk.FLAT,
                bd=0,
                padx=10,
                pady=5,
                font=Theme.FONTS["dialog_small"],
                cursor="hand2",
            )
            item.pack(fill=tk.X)

        add_menu_item("Proxy Settings", self.show_proxy_settings)
        add_menu_item("About", self.show_about)

        self.settings_dropdown.focus_force()
        self.settings_dropdown.bind("<FocusOut>", lambda _e: self._close_settings_menu())
        self.settings_dropdown.bind("<Escape>", lambda _e: self._close_settings_menu())

    def _run_settings_action(self, callback):
        self._close_settings_menu()
        callback()

    def _close_settings_menu(self):
        if self.settings_dropdown and self.settings_dropdown.winfo_exists():
            self.settings_dropdown.destroy()
        self.settings_dropdown = None

    def _set_badge(self, text, color, bg_color):
        self.badge_var.set(text)
        self.badge_frame.configure(bg=bg_color)
        self.badge_dot.configure(bg=bg_color, fg=color)
        self.badge_label.configure(bg=bg_color, fg=color)

    def _set_footer_status(self, text, color):
        _ = text
        _ = color

    def _update_content_length(self):
        text = self.result_text.get("1.0", "end-1c")
        self.content_length_var.set(f"Character Count: {len(text):,}")

    def show_proxy_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Proxy Settings")
        dialog.geometry("560x300")
        dialog.resizable(False, False)
        dialog.configure(bg=Theme.COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        container = tk.Frame(
            dialog,
            bg=Theme.COLORS["card"],
            highlightbackground=Theme.COLORS["border"],
            highlightthickness=1,
        )
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        title = tk.Label(
            container,
            text="Proxy Configuration",
            bg=Theme.COLORS["card"],
            fg=Theme.COLORS["text_dark"],
            font=Theme.FONTS["dialog_title"],
        )
        title.pack(anchor=tk.W, padx=16, pady=(14, 10))

        current_proxy = ProxyConfig.get_proxy_info()
        status = tk.Label(
            container,
            text=f"Current: {current_proxy}",
            bg=Theme.COLORS["card"],
            fg=Theme.COLORS["text_light"],
            font=Theme.FONTS["dialog_small"],
        )
        status.pack(anchor=tk.W, padx=16, pady=(0, 10))

        def _make_field(row_text):
            row = tk.Frame(container, bg=Theme.COLORS["card"])
            row.pack(fill=tk.X, padx=16, pady=5)
            label = tk.Label(
                row,
                text=row_text,
                width=10,
                anchor=tk.W,
                bg=Theme.COLORS["card"],
                fg=Theme.COLORS["text_dark"],
                font=Theme.FONTS["dialog_label"],
            )
            label.pack(side=tk.LEFT)
            shell = tk.Frame(
                row,
                bg=Theme.COLORS["card_alt"],
                highlightbackground=Theme.COLORS["border"],
                highlightthickness=1,
            )
            shell.pack(side=tk.LEFT, fill=tk.X, expand=True)
            entry = tk.Entry(
                shell,
                relief=tk.FLAT,
                bg=Theme.COLORS_ENTRY_BG,
                fg=Theme.COLORS["text_dark"],
                insertbackground=Theme.COLORS["text_dark"],
                font=Theme.FONTS["dialog_label"],
            )
            entry.pack(fill=tk.X, padx=8, ipady=6)
            return entry

        http_entry = _make_field("HTTP Proxy")
        https_entry = _make_field("HTTPS Proxy")

        current_proxies = ProxyConfig.get_proxies()
        if current_proxies and "http" in current_proxies:
            http_entry.insert(0, current_proxies["http"])
        if current_proxies and "https" in current_proxies:
            https_entry.insert(0, current_proxies["https"])

        help_label = tk.Label(
            container,
            text="Example: http://proxy.company.com:8080",
            bg=Theme.COLORS["card"],
            fg=Theme.COLORS["text_muted"],
            font=Theme.FONTS["dialog_help"],
        )
        help_label.pack(anchor=tk.W, padx=16, pady=(8, 8))

        btn_row = tk.Frame(container, bg=Theme.COLORS["card"])
        btn_row.pack(fill=tk.X, padx=16, pady=(0, 14))

        def save_proxy():
            http_proxy = http_entry.get().strip()
            https_proxy = https_entry.get().strip()
            if not http_proxy and not https_proxy:
                ProxyConfig.clear_proxy()
                messagebox.showinfo("Proxy Settings", "Proxy disabled")
            else:
                ProxyConfig.set_proxy(
                    http_proxy=http_proxy if http_proxy else None,
                    https_proxy=https_proxy if https_proxy else None,
                )
                messagebox.showinfo("Proxy Settings", "Proxy settings saved")
            dialog.destroy()

        def clear_proxy():
            http_entry.delete(0, tk.END)
            https_entry.delete(0, tk.END)
            ProxyConfig.clear_proxy()
            messagebox.showinfo("Proxy Settings", "Proxy cleared")

        save_btn = ModernButton(
            btn_row,
            "Save",
            save_proxy,
            bg_color=Theme.COLORS["primary"],
            hover_color=Theme.COLORS["primary_hover"],
            width=92,
            height=34,
            radius=8,
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 8))

        clear_btn = ModernButton(
            btn_row,
            "Clear",
            clear_proxy,
            bg_color=Theme.COLORS["danger"],
            hover_color="#F87171",
            width=92,
            height=34,
            radius=8,
        )
        clear_btn.pack(side=tk.LEFT, padx=(0, 8))

        cancel_btn = ModernButton(
            btn_row,
            "Cancel",
            dialog.destroy,
            bg_color=Theme.COLORS["secondary"],
            hover_color=Theme.COLORS["secondary_hover"],
            width=92,
            height=34,
            radius=8,
        )
        cancel_btn.pack(side=tk.LEFT)

    def show_about(self):
        about_text = """Web Content Extractor

Version: 2.0.0

Supports 44+ platforms including Reddit, Naver, Tech media, and research blogs.

Features:
- Proxy support
- Auto platform detection
- Clean text extraction
- Multi-parser architecture"""
        messagebox.showinfo("About", about_text)

    def start_extraction(self):
        url = self.url_entry.get().strip()
        is_valid, error_msg = URLValidator.validate(url)
        if not is_valid:
            messagebox.showwarning("Warning", error_msg)
            return

        self.result_text.delete("1.0", tk.END)
        self._update_content_length()
        self.view_model.start_extraction(url)

    def on_property_changed(self, property_name):
        self.root.after(0, lambda p=property_name: self._update_ui(p))

    def _update_ui(self, property_name):
        if property_name == "status_message":
            self.status_var.set(self.view_model.status_message)

        elif property_name == "is_extracting":
            if self.view_model.is_extracting:
                self.extract_btn.set_state("disabled")
                self.copy_btn.set_state("disabled")
                self.url_entry.config(state="disabled")
                self._set_badge("EXTRACTING", Theme.COLORS["warning"], Theme.COLORS["badge_busy_bg"])
                self._set_footer_status("Working", Theme.COLORS["warning"])
                self.progress_bar.pack(side=tk.RIGHT, padx=(8, 0))
                self.progress_bar.start(10)
            else:
                self.extract_btn.set_state("normal")
                self.url_entry.config(state="normal")
                self.progress_bar.stop()
                self.progress_bar.pack_forget()

        elif property_name == "result_text":
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert("1.0", self.view_model.result_text)
            self._update_content_length()

    def on_extraction_finished(self, success):
        self.root.after(0, lambda s=success: self._handle_finished(s))

    def _handle_finished(self, success):
        has_text = bool(self.view_model.result_text.strip())
        self.copy_btn.set_state("normal" if has_text else "disabled")
        if success:
            self._set_badge("SYSTEM READY", Theme.COLORS["success"], Theme.COLORS["badge_ready_bg"])
            self._set_footer_status("Ready", Theme.COLORS["success"])
        else:
            self._set_badge("FAILED", Theme.COLORS["danger"], Theme.COLORS["badge_error_bg"])
            self._set_footer_status("Error", Theme.COLORS["danger"])
            self.root.after(3500, self._reset_status)

    def _reset_status(self):
        if not self.view_model.is_extracting:
            self.status_var.set("Ready to extract content")
            self._set_badge("SYSTEM READY", Theme.COLORS["success"], Theme.COLORS["badge_ready_bg"])
            self._set_footer_status("Ready", Theme.COLORS["success"])

    def copy_to_clipboard(self):
        text = self.result_text.get("1.0", tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status_var.set("Content copied to clipboard.")

    def clear_result(self):
        self.result_text.delete("1.0", tk.END)
        self.url_entry.delete(0, tk.END)
        self.copy_btn.set_state("disabled")
        self._update_content_length()
        self._reset_status()


def main():
    root = tk.Tk()
    CrawlerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

