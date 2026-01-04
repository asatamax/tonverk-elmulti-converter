"""Main Flet application."""

import flet as ft

from elmconv import __version__ as elmconv_version

from .components import InputSelector, LogView, OptionsPanel, OutputPicker
from .converter import ConverterBridge
from .strings import Strings


class ElmconvApp:
    """Main application class."""

    def __init__(self, page: ft.Page):
        """Initialize the application.

        Args:
            page: Flet page instance
        """
        self.page = page
        self._output_path: str | None = None

        # Setup page
        self._setup_page()

        # Setup services
        self._setup_services()

        # Create components
        self._create_components()

        # Build layout
        self._build_layout()

        # Initial state
        self._check_ffmpeg()
        self.log_view.add(Strings.READY_MESSAGE, "info")
        self.log_view.add(
            f"elmconv v{elmconv_version} (Flet {ft.version.__version__})", "info"
        )

    def _setup_page(self):
        """Configure page properties."""
        self.page.title = Strings.APP_TITLE
        self.page.window.width = 550
        self.page.window.height = 840
        self.page.padding = 20

    def _setup_services(self):
        """Register page services."""
        self.file_picker = ft.FilePicker()
        self.page.services.append(self.file_picker)

    def _create_components(self):
        """Create all GUI components."""
        # Converter bridge (created first for debug log callback)
        self.converter = ConverterBridge(self._gui_log)

        # Log view (with debug log callback)
        self.log_view = LogView(
            page=self.page,
            get_debug_log=self.converter.get_debug_log,
        )

        # Output picker
        self.output_picker = OutputPicker(
            page=self.page,
            file_picker=self.file_picker,
            on_selected=self._on_output_selected,
            log_callback=self._gui_log,
        )

        # Options panel
        self.options_panel = OptionsPanel(page=self.page)

        # Input selector
        self.input_selector = InputSelector(
            page=self.page,
            file_picker=self.file_picker,
            on_files_selected=self._on_input_selected,
            log_callback=self._gui_log,
        )

    def _build_layout(self):
        """Build the page layout."""
        self.page.add(
            ft.Text(
                Strings.APP_TITLE,
                size=20,
                weight=ft.FontWeight.BOLD,
            ),
            ft.Container(height=10),
            self.output_picker.container,
            ft.Container(height=10),
            self.options_panel.container,
            ft.Container(height=10),
            self.input_selector.container,
            ft.Container(height=10),
            self.log_view.container,
        )

    def _gui_log(self, message: str, level: str = "info"):
        """Log callback for GUI."""
        self.log_view.add(message, level)

    def _check_ffmpeg(self):
        """Check ffmpeg availability at startup."""
        available, error = self.converter.check_ffmpeg()
        if not available:
            self.log_view.add(error, "error")

    def _on_output_selected(self, path: str):
        """Handle output folder selection."""
        self._output_path = path
        self.input_selector.set_enabled(True)

    async def _on_input_selected(self, paths: list[str]):
        """Handle input file selection, start conversion."""
        if not self._output_path:
            self._gui_log(Strings.SELECT_OUTPUT_FIRST, "error")
            return

        # Get options
        options = self.options_panel.get_options()

        self._gui_log(
            Strings.STARTING_CONVERSION.format(count=len(paths)),
            "info",
        )

        # Disable input during conversion
        self.input_selector.set_enabled(False)

        try:
            # Run conversion
            success, total = await self.converter.convert_files(
                input_paths=paths,
                output_dir=self._output_path,
                resample=options.resample,
                optimize=options.optimize,
                normalize=options.normalize,
                prefix=options.prefix,
                thin_factor=options.thin_factor,
                thin_max_interval=options.thin_max_interval,
            )

            self._gui_log(
                Strings.CONVERSION_RESULT.format(success=success, total=total),
                "success" if success == total else "warning",
            )

            # Show completion dialog
            await self._show_completion_dialog(success, total)

        finally:
            # Re-enable input
            self.input_selector.set_enabled(True)

    async def _show_completion_dialog(self, success: int, total: int):
        """Show completion dialog."""
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(Strings.CONVERSION_COMPLETE),
            content=ft.Text(
                f"{Strings.CONVERSION_RESULT.format(success=success, total=total)}\n\n"
                f"Output: {self._output_path}"
            ),
            actions=[
                ft.TextButton(
                    Strings.OK,
                    on_click=lambda e: self.page.pop_dialog(),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)
