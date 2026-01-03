"""Output folder selection component."""

from pathlib import Path
from typing import Callable

import flet as ft

from ..strings import Strings


class OutputPicker:
    """Output folder picker with path display."""

    def __init__(
        self,
        page: ft.Page,
        file_picker: ft.FilePicker,
        on_selected: Callable[[str], None],
        log_callback: Callable[[str, str], None],
    ):
        """Initialize output picker.

        Args:
            page: Flet page instance
            file_picker: FilePicker service
            on_selected: Callback when folder is selected
            log_callback: Callback for logging (message, level)
        """
        self.page = page
        self.file_picker = file_picker
        self.on_selected = on_selected
        self.log = log_callback
        self.selected_path: str | None = None

        # Path text field
        self.path_field = ft.TextField(
            label=Strings.OUTPUT_FOLDER,
            read_only=True,
            expand=True,
            hint_text=Strings.OUTPUT_HINT,
        )

        # Build container
        self.container = self._build()

    def _build(self) -> ft.Container:
        """Build the output picker container."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        Strings.OUTPUT_FOLDER,
                        weight=ft.FontWeight.BOLD,
                        size=12,
                    ),
                    ft.Row(
                        [
                            self.path_field,
                            ft.Button(
                                Strings.BROWSE,
                                on_click=self._on_browse,
                            ),
                        ],
                    ),
                ],
                spacing=5,
            ),
            padding=10,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=8,
        )

    def _is_folder_empty(self, path: str) -> bool:
        """Check if folder is empty (ignoring hidden files)."""
        folder = Path(path)
        if not folder.exists():
            return True
        visible_files = [f for f in folder.iterdir() if not f.name.startswith(".")]
        return len(visible_files) == 0

    async def _on_browse(self, e):
        """Handle browse button click."""
        result = await self.file_picker.get_directory_path(
            dialog_title=Strings.SELECT_OUTPUT_TITLE
        )
        if result:
            self.path_field.value = result
            self.selected_path = result
            self.log(f"Output folder: {result}", "info")

            # Warn if not empty
            if not self._is_folder_empty(result):
                self.log(Strings.OUTPUT_NOT_EMPTY_WARNING, "warning")

            self.on_selected(result)
            self.path_field.update()
