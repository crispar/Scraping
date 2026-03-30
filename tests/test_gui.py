"""
Tests for GUI initialization and flickering fix.

These tests verify:
1. Anti-flicker pattern (withdraw/deiconify) is correctly applied in source code
2. GUI initialization sequence is correct
3. All widget attributes and default states are preserved (backward compatibility)
4. Core operations (clear, copy, badge, etc.) work correctly

Strategy: Since tkinter may not be available in CI/headless environments,
we use a two-tier approach:
- Tier 1: Source code analysis tests (always run, no tkinter needed)
- Tier 2: Live widget tests (skip if tkinter unavailable)
"""

import ast
import os
import re
import sys
import textwrap

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

# Check if tkinter is available
try:
    import tkinter as tk

    HAS_TKINTER = True
except (ImportError, ModuleNotFoundError):
    HAS_TKINTER = False

# Check if display is available (headless environment)
HAS_DISPLAY = False
if HAS_TKINTER:
    try:
        _test_root = tk.Tk()
        _test_root.destroy()
        HAS_DISPLAY = True
    except tk.TclError:
        HAS_DISPLAY = False

requires_tkinter = pytest.mark.skipif(
    not (HAS_TKINTER and HAS_DISPLAY),
    reason="Requires tkinter and display server",
)


# =============================================================================
# Helper: Read gui_app.py source
# =============================================================================

def _read_gui_source():
    with open(GUI_APP_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _parse_gui_ast():
    source = _read_gui_source()
    return ast.parse(source, filename="gui_app.py")


def _get_class_method_source(class_name, method_name):
    """Extract the source lines of a specific method from a class."""
    source = _read_gui_source()
    tree = ast.parse(source)
    source_lines = source.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == method_name:
                        start = item.lineno - 1
                        end = item.end_lineno
                        return "\n".join(source_lines[start:end])
    return None


# =============================================================================
# Tier 1: Source Code Analysis Tests (no tkinter required)
# =============================================================================


class TestAntiFlickerSourceCode:
    """Verify anti-flicker pattern exists in source code via static analysis."""

    def test_gui_app_file_exists(self):
        assert os.path.isfile(GUI_APP_PATH), f"gui_app.py not found at {GUI_APP_PATH}"

    def test_withdraw_called_in_init(self):
        """CrawlerGUI.__init__ must call self.root.withdraw() before setup_ui()."""
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None, "CrawlerGUI.__init__ not found"

        withdraw_pos = init_source.find("withdraw()")
        setup_pos = init_source.find("setup_ui()")
        assert withdraw_pos != -1, "self.root.withdraw() not found in __init__"
        assert setup_pos != -1, "self.setup_ui() not found in __init__"
        assert withdraw_pos < setup_pos, (
            "withdraw() must be called BEFORE setup_ui() to prevent flickering"
        )

    def test_deiconify_called_in_init(self):
        """CrawlerGUI.__init__ must call self.root.deiconify() after setup_ui()."""
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None

        deiconify_pos = init_source.find("deiconify()")
        setup_pos = init_source.find("setup_ui()")
        assert deiconify_pos != -1, "self.root.deiconify() not found in __init__"
        assert deiconify_pos > setup_pos, (
            "deiconify() must be called AFTER setup_ui()"
        )

    def test_update_idletasks_before_deiconify(self):
        """update_idletasks() must be called before deiconify() to finalize layout."""
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None

        update_pos = init_source.find("update_idletasks()")
        deiconify_pos = init_source.find("deiconify()")
        assert update_pos != -1, "update_idletasks() not found in __init__"
        assert update_pos < deiconify_pos, (
            "update_idletasks() must be called BEFORE deiconify()"
        )

    def test_correct_initialization_sequence(self):
        """Verify the full anti-flicker sequence: withdraw → configure → setup_ui → update_idletasks → deiconify."""
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None

        steps = {
            "withdraw": init_source.find("withdraw()"),
            "configure_styles": init_source.find("_configure_styles()"),
            "setup_ui": init_source.find("setup_ui()"),
            "update_idletasks": init_source.find("update_idletasks()"),
            "deiconify": init_source.find("deiconify()"),
        }

        for step_name, pos in steps.items():
            assert pos != -1, f"{step_name} not found in __init__"

        # Verify order
        assert steps["withdraw"] < steps["configure_styles"], "withdraw must precede _configure_styles"
        assert steps["configure_styles"] < steps["setup_ui"], "_configure_styles must precede setup_ui"
        assert steps["setup_ui"] < steps["update_idletasks"], "setup_ui must precede update_idletasks"
        assert steps["update_idletasks"] < steps["deiconify"], "update_idletasks must precede deiconify"

    def test_no_premature_update_or_mainloop_in_init(self):
        """__init__ should not call update() or mainloop() which would show window prematurely."""
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None

        # update() without idletasks would show the window
        lines = init_source.splitlines()
        for line in lines:
            stripped = line.strip()
            if "update()" in stripped and "update_idletasks" not in stripped:
                # Make sure it's not a comment
                if not stripped.startswith("#"):
                    pytest.fail(f"Found premature update() call: {stripped}")

        assert "mainloop()" not in init_source, (
            "mainloop() should not be in __init__, it belongs in main()"
        )


class TestCenterWindowSourceCode:
    """Verify _center_window method exists and is called correctly."""

    def test_center_window_method_exists(self):
        source = _read_gui_source()
        assert "def _center_window(self)" in source, (
            "_center_window method not found in CrawlerGUI"
        )

    def test_center_window_called_in_init(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert "_center_window()" in init_source, (
            "_center_window() not called in __init__"
        )

    def test_center_window_uses_screen_dimensions(self):
        method_source = _get_class_method_source("CrawlerGUI", "_center_window")
        assert method_source is not None, "_center_window method not found"
        assert "winfo_screenwidth" in method_source, "Must use screen width for centering"
        assert "winfo_screenheight" in method_source, "Must use screen height for centering"

    def test_center_window_between_update_and_deiconify(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None

        update_pos = init_source.find("update_idletasks()")
        center_pos = init_source.find("_center_window()")
        deiconify_pos = init_source.find("deiconify()")

        assert center_pos != -1, "_center_window() not found in __init__"
        assert update_pos < center_pos < deiconify_pos, (
            "Sequence must be: update_idletasks → _center_window → deiconify"
        )


class TestWidgetCreationSourceCode:
    """Verify all required widgets are created in source code (backward compatibility)."""

    def test_setup_ui_creates_header(self):
        source = _get_class_method_source("CrawlerGUI", "setup_ui")
        assert source is not None
        assert "_create_header" in source

    def test_setup_ui_creates_results_panel(self):
        source = _get_class_method_source("CrawlerGUI", "setup_ui")
        assert source is not None
        assert "_create_results_panel" in source

    def test_setup_ui_creates_footer(self):
        source = _get_class_method_source("CrawlerGUI", "setup_ui")
        assert source is not None
        assert "_create_footer" in source

    def test_extract_button_created(self):
        source = _read_gui_source()
        assert "self.extract_btn" in source
        assert 'ModernButton' in source

    def test_copy_button_created(self):
        source = _read_gui_source()
        assert "self.copy_btn" in source

    def test_clear_button_created(self):
        source = _read_gui_source()
        assert "self.clear_btn" in source

    def test_url_entry_created(self):
        source = _read_gui_source()
        assert "self.url_entry" in source
        assert "tk.Entry" in source

    def test_result_text_created(self):
        source = _read_gui_source()
        assert "self.result_text" in source
        assert "ScrolledText" in source

    def test_status_label_created(self):
        source = _read_gui_source()
        assert "self.status_label" in source

    def test_progress_bar_created(self):
        source = _read_gui_source()
        assert "self.progress_bar" in source
        assert "Progressbar" in source

    def test_badge_components_created(self):
        source = _read_gui_source()
        assert "self.badge_frame" in source
        assert "self.badge_label" in source
        assert "self.badge_dot" in source

    def test_settings_button_created(self):
        source = _read_gui_source()
        assert "self.settings_btn" in source


class TestDefaultValuesSourceCode:
    """Verify default values are preserved in source code."""

    def test_initial_status_message(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert "Paste a URL and run extraction." in init_source

    def test_initial_content_length(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert "Character Count: 0" in init_source

    def test_initial_badge(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert "SYSTEM READY" in init_source

    def test_copy_button_starts_disabled(self):
        source = _read_gui_source()
        # Find copy_btn creation and subsequent set_state("disabled")
        copy_btn_pos = source.find("self.copy_btn = ModernButton")
        disabled_pos = source.find('self.copy_btn.set_state("disabled")', copy_btn_pos)
        assert disabled_pos != -1, "copy_btn must be disabled after creation"

    def test_window_geometry(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert "1160x780" in init_source

    def test_window_min_size(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert "minsize(980, 640)" in init_source

    def test_window_title(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert "Content Extractor - Desktop Pro" in init_source


class TestModernButtonSourceCode:
    """Verify ModernButton class structure is intact."""

    def test_modern_button_class_exists(self):
        source = _read_gui_source()
        assert "class ModernButton(tk.Canvas)" in source

    def test_modern_button_has_set_state(self):
        method = _get_class_method_source("ModernButton", "set_state")
        assert method is not None, "ModernButton.set_state() method not found"

    def test_modern_button_has_round_rectangle(self):
        method = _get_class_method_source("ModernButton", "_round_rectangle")
        assert method is not None, "ModernButton._round_rectangle() method not found"

    def test_modern_button_has_hover_events(self):
        init_source = _get_class_method_source("ModernButton", "__init__")
        assert init_source is not None
        assert "<Enter>" in init_source
        assert "<Leave>" in init_source
        assert "<Button-1>" in init_source


class TestCallbackWiringSourceCode:
    """Verify ViewModel callbacks are properly wired."""

    def test_on_property_changed_bound(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert "on_property_changed" in init_source

    def test_on_extraction_finished_bound(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert "on_extraction_finished" in init_source

    def test_window_close_protocol(self):
        init_source = _get_class_method_source("CrawlerGUI", "__init__")
        assert init_source is not None
        assert "WM_DELETE_WINDOW" in init_source


class TestMainFunctionSourceCode:
    """Verify main() function structure."""

    def test_main_function_exists(self):
        source = _read_gui_source()
        assert "def main():" in source

    def test_main_creates_tk_root(self):
        source = _read_gui_source()
        # Find the main function body
        main_start = source.find("def main():")
        main_body = source[main_start:]
        assert "tk.Tk()" in main_body

    def test_main_creates_crawler_gui(self):
        source = _read_gui_source()
        main_start = source.find("def main():")
        main_body = source[main_start:]
        assert "CrawlerGUI(root)" in main_body

    def test_main_calls_mainloop(self):
        source = _read_gui_source()
        main_start = source.find("def main():")
        main_body = source[main_start:]
        assert "mainloop()" in main_body

    def test_main_does_not_call_withdraw(self):
        """main() should NOT call withdraw — that's CrawlerGUI.__init__'s job."""
        source = _read_gui_source()
        main_start = source.find("def main():")
        # Find the next def or class or end of file
        next_def = source.find("\ndef ", main_start + 1)
        next_class = source.find("\nclass ", main_start + 1)
        end = len(source)
        if next_def != -1:
            end = min(end, next_def)
        if next_class != -1:
            end = min(end, next_class)
        main_body = source[main_start:end]
        assert "withdraw" not in main_body, (
            "main() should not call withdraw — CrawlerGUI.__init__ handles it"
        )


class TestCoreMethodsExist:
    """Verify all core GUI methods still exist (backward compatibility)."""

    @pytest.mark.parametrize(
        "method_name",
        [
            "__init__",
            "_center_window",
            "_on_window_close",
            "_configure_styles",
            "setup_ui",
            "_create_header",
            "_create_extract_input",
            "_create_results_panel",
            "_create_footer",
            "_show_settings_menu",
            "_run_settings_action",
            "_close_settings_menu",
            "_set_badge",
            "_set_footer_status",
            "_update_content_length",
            "show_proxy_settings",
            "show_about",
            "start_extraction",
            "on_property_changed",
            "_update_ui",
            "on_extraction_finished",
            "_handle_finished",
            "_reset_status",
            "copy_to_clipboard",
            "clear_result",
        ],
    )
    def test_method_exists(self, method_name):
        source = _get_class_method_source("CrawlerGUI", method_name)
        assert source is not None, f"CrawlerGUI.{method_name}() method not found"


# =============================================================================
# Tier 2: Live Widget Tests (require tkinter + display)
# =============================================================================


@requires_tkinter
class TestLiveAntiFlicker:
    """Live tests verifying the anti-flicker pattern with real tkinter."""

    @pytest.fixture(autouse=True)
    def setup_root(self):
        self.root = tk.Tk()
        self.root.withdraw()
        yield
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def test_window_visible_after_init(self):
        from gui_app import CrawlerGUI

        gui = CrawlerGUI(self.root)
        state = gui.root.state()
        assert state == "normal", f"Window should be 'normal' after init, got '{state}'"

    def test_withdraw_then_deiconify_sequence(self):
        call_order = []
        original_withdraw = self.root.withdraw
        original_deiconify = self.root.deiconify

        def mock_withdraw():
            call_order.append("withdraw")
            return original_withdraw()

        def mock_deiconify():
            call_order.append("deiconify")
            return original_deiconify()

        self.root.withdraw = mock_withdraw
        self.root.deiconify = mock_deiconify

        from gui_app import CrawlerGUI

        CrawlerGUI(self.root)

        assert "withdraw" in call_order
        assert "deiconify" in call_order
        assert call_order.index("withdraw") < call_order.index("deiconify")


@requires_tkinter
class TestLiveWidgetDefaults:
    """Live tests verifying widget default states with real tkinter."""

    @pytest.fixture(autouse=True)
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.withdraw()
        from gui_app import CrawlerGUI

        self.gui = CrawlerGUI(self.root)
        yield
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def test_initial_status_message(self):
        assert self.gui.status_var.get() == "Paste a URL and run extraction."

    def test_initial_badge(self):
        assert self.gui.badge_var.get() == "SYSTEM READY"

    def test_copy_button_disabled(self):
        assert self.gui.copy_btn.enabled is False

    def test_extract_button_enabled(self):
        assert self.gui.extract_btn.enabled is True

    def test_result_text_empty(self):
        content = self.gui.result_text.get("1.0", "end-1c")
        assert content == ""

    def test_progress_bar_not_packed(self):
        with pytest.raises(tk.TclError):
            self.gui.progress_bar.pack_info()


@requires_tkinter
class TestLiveCoreOperations:
    """Live tests for core GUI operations."""

    @pytest.fixture(autouse=True)
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.withdraw()
        from gui_app import CrawlerGUI

        self.gui = CrawlerGUI(self.root)
        yield
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def test_clear_result(self):
        self.gui.result_text.insert("1.0", "Some content")
        self.gui.url_entry.insert(0, "https://example.com")
        self.gui.clear_result()

        assert self.gui.result_text.get("1.0", "end-1c") == ""
        assert self.gui.url_entry.get() == ""
        assert self.gui.copy_btn.enabled is False

    def test_copy_to_clipboard(self):
        self.gui.result_text.insert("1.0", "Test content")
        self.gui.copy_to_clipboard()
        assert self.gui.status_var.get() == "Content copied to clipboard."

    def test_content_length_update(self):
        self.gui.result_text.insert("1.0", "Hello World")
        self.gui._update_content_length()
        assert self.gui.content_length_var.get() == "Character Count: 11"

    def test_handle_finished_success(self):
        self.gui.view_model.result_text = "Extracted content"
        self.gui._handle_finished(True)
        assert self.gui.badge_var.get() == "SYSTEM READY"
        assert self.gui.copy_btn.enabled is True

    def test_handle_finished_failure(self):
        self.gui.view_model.result_text = ""
        self.gui._handle_finished(False)
        assert self.gui.badge_var.get() == "FAILED"
        assert self.gui.copy_btn.enabled is False

    def test_reset_status(self):
        self.gui._reset_status()
        assert self.gui.status_var.get() == "Ready to extract content"
        assert self.gui.badge_var.get() == "SYSTEM READY"


@requires_tkinter
class TestLiveModernButton:
    """Live tests for ModernButton widget."""

    @pytest.fixture(autouse=True)
    def setup_root(self):
        self.root = tk.Tk()
        self.root.withdraw()
        yield
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def test_button_creation(self):
        from gui_app import ModernButton

        frame = tk.Frame(self.root, bg="#000000")
        btn = ModernButton(frame, "Test", lambda: None, width=100, height=30)
        assert btn.enabled is True
        assert btn.text == "Test"

    def test_disable_enable_cycle(self):
        from gui_app import ModernButton

        frame = tk.Frame(self.root, bg="#000000")
        btn = ModernButton(frame, "Test", lambda: None, width=100, height=30)

        btn.set_state("disabled")
        assert btn.enabled is False

        btn.set_state("normal")
        assert btn.enabled is True

    def test_click_only_when_enabled(self):
        from gui_app import ModernButton

        clicks = []
        frame = tk.Frame(self.root, bg="#000000")
        btn = ModernButton(frame, "Test", lambda: clicks.append(1), width=100, height=30)

        btn._on_click(None)
        assert len(clicks) == 1

        btn.set_state("disabled")
        btn._on_click(None)
        assert len(clicks) == 1  # No additional click
