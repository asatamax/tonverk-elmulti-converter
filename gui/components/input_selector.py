"""Input file/folder selection component."""

from pathlib import Path
from typing import Callable

import flet as ft

from ..strings import Strings


class InputSelector:
    """Input selection buttons (files and folder)."""

    def __init__(
        self,
        page: ft.Page,
        file_picker: ft.FilePicker,
        on_files_selected: Callable[[list[str]], None],
        log_callback: Callable[[str, str], None],
    ):
        """Initialize input selector.

        Args:
            page: Flet page instance
            file_picker: FilePicker service
            on_files_selected: Callback when files are selected
            log_callback: Callback for logging (message, level)
        """
        self.page = page
        self.file_picker = file_picker
        self.on_files_selected = on_files_selected
        self.log = log_callback

        # Remember last directory for better UX
        self._last_directory: str | None = None

        # Buttons (initially disabled)
        self.select_files_btn = ft.Button(
            Strings.SELECT_FILES,
            icon=ft.Icons.AUDIO_FILE,
            on_click=self._on_select_files,
            expand=True,
            disabled=True,
        )
        self.select_folder_btn = ft.Button(
            Strings.SELECT_FOLDER,
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._on_select_folder,
            expand=True,
            disabled=True,
        )

        # Build container
        self.container = self._build()

    def _build(self) -> ft.Container:
        """Build the input selector container."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        Strings.SELECT_INPUT,
                        weight=ft.FontWeight.BOLD,
                        size=12,
                    ),
                    ft.Row(
                        [self.select_files_btn, self.select_folder_btn],
                        spacing=10,
                    ),
                    ft.Text(
                        Strings.INPUT_HINT,
                        size=11,
                        color=ft.Colors.GREY_500,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=15,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=8,
        )

    def set_enabled(self, enabled: bool):
        """Enable or disable input buttons."""
        self.select_files_btn.disabled = not enabled
        self.select_folder_btn.disabled = not enabled
        self.page.update()

    async def _on_select_files(self, e):
        """Handle file selection."""
        results = await self.file_picker.pick_files(
            dialog_title=Strings.SELECT_FILES_TITLE,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["exs", "sfz"],
            allow_multiple=True,
            initial_directory=self._last_directory,
        )
        if results:
            paths = [f.path for f in results]
            # Remember directory for next time
            self._last_directory = str(Path(paths[0]).parent)
            await self.on_files_selected(paths)

    async def _on_select_folder(self, e):
        """Handle folder selection."""
        result = await self.file_picker.get_directory_path(
            dialog_title=Strings.SELECT_INPUT_FOLDER_TITLE,
            initial_directory=self._last_directory,
        )
        if result:
            folder = Path(result)
            # Remember directory for next time
            self._last_directory = str(folder)
            files = list(folder.glob("*.exs")) + list(folder.glob("*.sfz"))

            if files:
                paths = [str(f) for f in sorted(files)]
                self.log(
                    f"Found {len(paths)} file(s) in {folder.name}/",
                    "info",
                )
                await self.on_files_selected(paths)
            else:
                self.log(
                    Strings.NO_FILES_FOUND.format(folder=folder.name),
                    "warning",
                )
