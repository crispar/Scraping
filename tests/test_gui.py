"""
Tests for GUI initialization and flickering fix.

Verifies:
1. Anti-flicker pattern (withdraw/deiconify) via source code analysis
2. GUI initialization sequence correctness
3. Widget attributes and default states (backward compatibility)
4. Core operations (clear, copy, badge, etc.)

Tier 1 tests use static source analysis (no tkinter needed).
Tier 2 tests use live widgets (skipped if tkinter/display unavailable).
"""

import ast
import os
import sys
from functools import lru_cache

import pytest

# Ensure project directories are in path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(current_dir)
src_dir = os.path.join(project_dir, "src")
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

GUI_APP_PATH = os.path.join(project_dir, "gui_app.py")

# Check if tkinter + display are available
try:
    import tkinter as tk

    _test_root = tk.Tk()
    _test_root.destroy()
    HAS_TKINTER = True
except Exception:
    HAS_TKINTER = False

requires_tkinter = pytest.mark.skipif(
    not HAS_TKINTER,
    reason="Requires tkinter and display server",
)


# =============================================================================
# Cached helpers — file is read and parsed once per test session
# =============================================================================

@lru_cache(maxsize=1)
def _read_gui_source():
    with open(GUI_APP_PATH, "r", encoding="utf-8") as f:
        return f.read()


@lru_cache(maxsize=1)
def _parsed_gui_ast():
    return ast.parse(_read_gui_source(), filename="gui_app.py")


@lru_cache(maxsize=None)
def _get_class_method_source(class_name, method_name):
    """Extract the source lines of a specific method from a class."""
    source = _read_gui_source()
    source_lines = source.splitlines()

    for node in ast.walk(_parsed_gui_ast()):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == method_name:
                        start = item.lineno - 1
                        end = item.end_lineno
                        return "\n".join(source_lines[start:end])
    return None


def _assert_source_order(source, *items):
    """Assert items appear in source in the given order."""
    positions = {}
    for item in items:
        pos = source.find(item)
        assert pos != -1, f"{item} not found in source"
        positions[item] = pos
    for a, b in zip(items, items[1:]):
        assert positions[a] < positions[b], f"{a} must appear before {b}"


# =============================================================================
# Shared fixture for Tier 2 live tests
# =============================================================================

if HAS_TKINTER:
    @pytest.fixture
    def tk_root():
        root = tk.Tk()
        root.withdraw()
        yield root
        try:
            root.destroy()
        except tk.TclError:
            pass

    @pytest.fixture
    def gui(tk_root):
        from gui_app import CrawlerGUI
        return CrawlerGUI(tk_root)


# =============================================================================
# Tier 1: Source Code Analysis Tests (no tkinter required)
# =============================================================================


class TestAntiFlickerSourceCode:
    """Verify anti-flicker pattern exists in source code via static analysis."""

    def test_gui_app_file_exists(self):
        assert os.path.isfile(GUI_APP_PATH), f"gui_app.py not found at {GUI_APP_PATH}"

    def test_withdraw_before_setup_ui(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None, "CrawlerGUI.__init__ not found"
        _assert_source_order(init_source, "withdraw()", "setup_ui()")

    def test_deiconify_after_setup_ui(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        _assert_source_order(init_source, "setup_ui()", "deiconify()")

    def test_update_idletasks_before_deiconify(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        _assert_source_order(init_source, "update_idletasks()", "deiconify()")

    def test_correct_initialization_sequence(self):
        """Full sequence: withdraw -> configure -> setup_ui -> update_idletasks -> deiconify."""
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        _assert_source_order(
            init_source,
            "withdraw()",
            "_configure_styles()",
            "setup_ui()",
            "update_idletasks()",
            "deiconify()",
        )

    def test_no_premature_update_or_mainloop_in_init(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None

        for line in init_source.splitlines():
            stripped = line.strip()
            if "update()" in stripped and "update_idletasks" not in stripped:
                if not stripped.startswith("#"):
                    pytest.fail(f"Found premature update() call: {stripped}")

        assert "mainloop()" not in init_source, (
            "mainloop() should not be in __init__, it belongs in main()"
        )


class TestCenterWindowSourceCode:
    """Verify _center_window method exists and is called correctly."""

    def test_center_window_method_exists(self):
        assert "def _center_window(self)" in _read_gui_source()

    def test_center_window_called_in_init(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert "_center_window()" in init_source

    def test_center_window_uses_screen_dimensions(self):
        method_source = _get_class_method_source("CrawlerGUI", "_center_window")
        assert method_source is not None
        assert "winfo_screenwidth" in method_source
        assert "winfo_screenheight" in method_source

    def test_center_window_between_update_and_deiconify(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        _assert_source_order(init_source, "update_idletasks()", "_center_window()", "deiconify()")


class TestWidgetCreationSourceCode:
    """Verify all required widgets are created in source code."""

    def test_setup_ui_creates_header(self):
        assert "_create_header" in _get_class_method_source("CrawlerGUI", "setup_ui")

    def test_setup_ui_creates_results_panel(self):
        assert "_create_results_panel" in _get_class_method_source("CrawlerGUI", "setup_ui")

    def test_setup_ui_creates_footer(self):
        assert "_create_footer" in _get_class_method_source("CrawlerGUI", "setup_ui")

    @pytest.mark.parametrize("widget", [
        "self.extract_btn", "self.copy_btn", "self.clear_btn",
        "self.url_entry", "self.result_text", "self.status_label",
        "self.progress_bar", "self.badge_frame", "self.badge_label",
        "self.badge_dot", "self.settings_btn",
    ])
    def test_widget_created(self, widget):
        assert widget in _read_gui_source()


class TestDefaultValuesSourceCode:
    """Verify default values are preserved in source code."""

    @pytest.mark.parametrize("expected", [
        "Paste a URL and run extraction.",
        "Character Count: 0",
        "SYSTEM READY",
        "1160x780",
        "minsize(980, 640)",
        "Content Extractor - Desktop Pro",
    ])
    def test_default_value_in_init(self, expected):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert expected in init_source

    def test_copy_button_starts_disabled(self):
        source = _read_gui_source()
        copy_btn_pos = source.find("self.copy_btn = ModernButton")
        disabled_pos = source.find('self.copy_btn.set_state("disabled")', copy_btn_pos)
        assert disabled_pos != -1, "copy_btn must be disabled after creation"


class TestModernButtonSourceCode:
    """Verify ModernButton class structure is intact."""

    def test_modern_button_class_exists(self):
        assert "class ModernButton(tk.Canvas)" in _read_gui_source()

    @pytest.mark.parametrize("method", ["set_state", "_round_rectangle"])
    def test_method_exists(self, method):
        assert _get_class_method_source("ModernButton", method) is not None

    def test_hover_events_bound(self):
        init_source = _get_class_method_source("ModernButton", "__init__")
        assert init_source is not None
        for event in ("<Enter>", "<Leave>", "<Button-1>"):
            assert event in init_source


class TestCallbackWiringSourceCode:
    """Verify ViewModel callbacks are properly wired."""

    @pytest.mark.parametrize("expected", [
        "on_property_changed", "on_extraction_finished", "WM_DELETE_WINDOW",
    ])
    def test_callback_in_init(self, expected):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert expected in init_source


class TestMainFunctionSourceCode:
    """Verify main() function structure."""

    def _get_main_body(self):
        source = _read_gui_source()
        main_start = source.find("def main():")
        assert main_start != -1
        # Find scope boundary
        next_def = source.find("\ndef ", main_start + 1)
        next_class = source.find("\nclass ", main_start + 1)
        candidates = [pos for pos in (next_def, next_class) if pos != -1]
        end = min(candidates) if candidates else len(source)
        return source[main_start:end]

    @pytest.mark.parametrize("expected", ["tk.Tk()", "CrawlerGUI(root)", "mainloop()"])
    def test_main_contains(self, expected):
        assert expected in self._get_main_body()

    def test_main_does_not_call_withdraw(self):
        assert "withdraw" not in self._get_main_body()


class TestCoreMethodsExist:
    """Verify all core GUI methods still exist (backward compatibility)."""

    @pytest.mark.parametrize("method_name", [
        "__init__", "_center_window", "_on_window_close", "_configure_styles",
        "setup_ui", "_create_header", "_create_extract_input",
        "_create_results_panel", "_create_footer", "_show_settings_menu",
        "_run_settings_action", "_close_settings_menu", "_set_badge",
        "_set_footer_status", "_update_content_length", "show_proxy_settings",
        "show_about", "start_extraction", "on_property_changed", "_update_ui",
        "on_extraction_finished", "_handle_finished", "_reset_status",
        "copy_to_clipboard", "clear_result",
    ])
    def test_method_exists(self, method_name):
        assert _get_class_method_source("CrawlerGUI", method_name) is not None, (
            f"CrawlerGUI.{method_name}() not found"
        )


# =============================================================================
# Tier 2: Live Widget Tests (require tkinter + display)
# =============================================================================


@requires_tkinter
class TestLiveAntiFlicker:
    """Live tests verifying the anti-flicker pattern with real tkinter."""

    def test_window_visible_after_init(self, gui):
        state = gui.root.state()
        assert state == "normal", f"Window should be 'normal' after init, got '{state}'"

    def test_withdraw_then_deiconify_sequence(self, tk_root):
        call_order = []
        original_withdraw = tk_root.withdraw
        original_deiconify = tk_root.deiconify

        tk_root.withdraw = lambda: (call_order.append("withdraw"), original_withdraw())[-1]
        tk_root.deiconify = lambda: (call_order.append("deiconify"), original_deiconify())[-1]

        from gui_app import CrawlerGUI
        CrawlerGUI(tk_root)

        assert "withdraw" in call_order
        assert "deiconify" in call_order
        assert call_order.index("withdraw") < call_order.index("deiconify")


@requires_tkinter
class TestLiveWidgetDefaults:
    """Live tests verifying widget default states with real tkinter."""

    def test_initial_status_message(self, gui):
        assert gui.status_var.get() == "Paste a URL and run extraction."

    def test_initial_badge(self, gui):
        assert gui.badge_var.get() == "SYSTEM READY"

    def test_copy_button_disabled(self, gui):
        assert gui.copy_btn.enabled is False

    def test_extract_button_enabled(self, gui):
        assert gui.extract_btn.enabled is True

    def test_result_text_empty(self, gui):
        assert gui.result_text.get("1.0", "end-1c") == ""

    def test_progress_bar_not_packed(self, gui):
        with pytest.raises(tk.TclError):
            gui.progress_bar.pack_info()


@requires_tkinter
class TestLiveCoreOperations:
    """Live tests for core GUI operations."""

    def test_clear_result(self, gui):
        gui.result_text.insert("1.0", "Some content")
        gui.url_entry.insert(0, "https://example.com")
        gui.clear_result()

        assert gui.result_text.get("1.0", "end-1c") == ""
        assert gui.url_entry.get() == ""
        assert gui.copy_btn.enabled is False

    def test_copy_to_clipboard(self, gui):
        gui.result_text.insert("1.0", "Test content")
        gui.copy_to_clipboard()
        assert gui.status_var.get() == "Content copied to clipboard."

    def test_content_length_update(self, gui):
        gui.result_text.insert("1.0", "Hello World")
        gui._update_content_length()
        assert gui.content_length_var.get() == "Character Count: 11"

    def test_handle_finished_success(self, gui):
        gui.view_model.result_text = "Extracted content"
        gui._handle_finished(True)
        assert gui.badge_var.get() == "SYSTEM READY"
        assert gui.copy_btn.enabled is True

    def test_handle_finished_failure(self, gui):
        gui.view_model.result_text = ""
        gui._handle_finished(False)
        assert gui.badge_var.get() == "FAILED"
        assert gui.copy_btn.enabled is False

    def test_reset_status(self, gui):
        gui._reset_status()
        assert gui.status_var.get() == "Ready to extract content"
        assert gui.badge_var.get() == "SYSTEM READY"


@requires_tkinter
class TestLiveModernButton:
    """Live tests for ModernButton widget."""

    def test_button_creation(self, tk_root):
        from gui_app import ModernButton
        frame = tk.Frame(tk_root, bg="#000000")
        btn = ModernButton(frame, "Test", lambda: None, width=100, height=30)
        assert btn.enabled is True
        assert btn.text == "Test"

    def test_disable_enable_cycle(self, tk_root):
        from gui_app import ModernButton
        frame = tk.Frame(tk_root, bg="#000000")
        btn = ModernButton(frame, "Test", lambda: None, width=100, height=30)

        btn.set_state("disabled")
        assert btn.enabled is False
        btn.set_state("normal")
        assert btn.enabled is True

    def test_click_only_when_enabled(self, tk_root):
        from gui_app import ModernButton
        clicks = []
        frame = tk.Frame(tk_root, bg="#000000")
        btn = ModernButton(frame, "Test", lambda: clicks.append(1), width=100, height=30)

        btn._on_click(None)
        assert len(clicks) == 1

        btn.set_state("disabled")
        btn._on_click(None)
        assert len(clicks) == 1
