"""Conversion log display component."""

from typing import Callable

import flet as ft

from ..strings import Strings


class LogView:
    """Log view with copy and clear functionality."""

    def __init__(
        self,
        page: ft.Page,
        get_debug_log: Callable[[], str] | None = None,
    ):
        """Initialize log view.

        Args:
            page: Flet page instance for updates
            get_debug_log: Callback to get detailed debug log
        """
        self.page = page
        self._log_entries: list[str] = []
        self._get_debug_log = get_debug_log

        # Create ListView for log entries
        self.log_list = ft.ListView(
            expand=True,
            spacing=2,
            auto_scroll=True,
        )

        # Build container
        self.container = self._build()

    def _build(self) -> ft.Container:
        """Build the log view container."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text(
                                Strings.CONVERSION_LOG,
                                weight=ft.FontWeight.BOLD,
                                size=12,
                            ),
                            ft.Row(
                                [
                                    ft.TextButton(
                                        Strings.COPY,
                                        on_click=self._on_copy_click,
                                    ),
                                    ft.TextButton(
                                        Strings.COPY_DEBUG,
                                        on_click=self._on_copy_debug_click,
                                    ),
                                    ft.TextButton(
                                        Strings.CLEAR,
                                        on_click=self._on_clear_click,
                                    ),
                                ],
                                spacing=0,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(
                        content=self.log_list,
                        border=ft.Border.all(1, ft.Colors.GREY_300),
                        border_radius=5,
                        padding=10,
                        expand=True,
                    ),
                ],
                spacing=5,
                expand=True,
            ),
            expand=True,
        )

    def add(self, message: str, level: str = "info"):
        """Add a log entry.

        Args:
            message: Log message
            level: "info", "warning", "error", or "success"
        """
        color_map = {
            "info": None,
            "warning": ft.Colors.ORANGE,
            "error": ft.Colors.RED,
            "success": ft.Colors.GREEN,
        }
        color = color_map.get(level)

        text = ft.Text(message, color=color, size=12)
        self.log_list.controls.append(text)
        self._log_entries.append(message)
        if self.page.controls:
            self.page.update()

    def clear(self):
        """Clear all log entries."""
        self.log_list.controls.clear()
        self._log_entries.clear()
        self.page.update()

    def get_text(self) -> str:
        """Get all log text as single string."""
        return "\n".join(self._log_entries)

    async def _on_copy_click(self, e):
        """Handle copy button click."""
        log_content = self.get_text()
        await ft.Clipboard().set(log_content)
        self.add(Strings.LOG_COPIED, level="info")

    async def _on_copy_debug_click(self, e):
        """Handle copy debug button click."""
        if self._get_debug_log:
            debug_content = self._get_debug_log()
            if debug_content:
                await ft.Clipboard().set(debug_content)
                self.add(Strings.DEBUG_LOG_COPIED, level="info")
            else:
                self.add("No debug log available yet", level="warning")
        else:
            self.add("Debug log not available", level="warning")

    def _on_clear_click(self, e):
        """Handle clear button click."""
        self.clear()
