"""Conversion options panel component."""

from dataclasses import dataclass

import flet as ft

from ..strings import Strings


@dataclass
class ConversionOptions:
    """Conversion options data class."""

    resample: bool = True
    optimize: bool = False
    normalize: bool = False
    prefix: str = ""
    thin_factor: int | None = None
    thin_max_interval: int | None = None


class OptionsPanel:
    """Options panel with checkboxes and text field."""

    def __init__(self, page: ft.Page):
        """Initialize options panel.

        Args:
            page: Flet page instance (for dialogs)
        """
        self.page = page

        # Checkboxes
        self.resample_cb = ft.Checkbox(
            label=Strings.RESAMPLE_48K,
            value=True,
        )
        self.optimize_cb = ft.Checkbox(
            label=Strings.OPTIMIZE_LOOPS,
            value=False,
        )
        self.normalize_cb = ft.Checkbox(
            label=Strings.NORMALIZE,
            value=False,
        )

        # Prefix field
        self.prefix_field = ft.TextField(
            label=Strings.PREFIX_LABEL,
            width=100,
            dense=True,
        )

        # Thinning controls
        self.thin_cb = ft.Checkbox(
            label=Strings.SAMPLE_THINNING,
            value=False,
            on_change=self._on_thin_toggle,
        )
        self.thin_factor_field = ft.TextField(
            label=Strings.THIN_FACTOR_LABEL,
            width=100,
            dense=True,
            disabled=True,
            input_filter=ft.NumbersOnlyInputFilter(),
        )
        self.thin_max_interval_field = ft.TextField(
            label=Strings.THIN_MAX_INTERVAL_LABEL,
            width=100,
            dense=True,
            disabled=True,
            input_filter=ft.NumbersOnlyInputFilter(),
        )

        # Options help button (for all options)
        self.options_help_btn = ft.IconButton(
            icon=ft.Icons.HELP_OUTLINE,
            icon_size=18,
            tooltip=Strings.OPTIONS_HELP_TITLE,
            on_click=self._show_options_help,
        )

        # Build container
        self.container = self._build()

    def _on_thin_toggle(self, e):
        """Handle thinning checkbox toggle."""
        enabled = self.thin_cb.value or False
        self.thin_factor_field.disabled = not enabled
        self.thin_max_interval_field.disabled = not enabled
        if not enabled:
            self.thin_factor_field.value = ""
            self.thin_max_interval_field.value = ""
        self.page.update()

    def _show_options_help(self, e):
        """Show options help dialog."""
        dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text(Strings.OPTIONS_HELP_TITLE),
            content=ft.Text(Strings.OPTIONS_HELP_TEXT),
            actions=[
                ft.TextButton("OK", on_click=lambda e: self.page.pop_dialog()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dialog)

    def _build(self) -> ft.Container:
        """Build the options panel container."""
        return ft.Container(
            content=ft.Column(
                [
                    # Header row with title and help button
                    ft.Row(
                        [
                            ft.Text(
                                Strings.OPTIONS,
                                weight=ft.FontWeight.BOLD,
                                size=12,
                            ),
                            self.options_help_btn,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    # Row 1: Resample, Optimize
                    ft.Row([self.resample_cb, self.optimize_cb]),
                    # Row 2: Normalize
                    ft.Row([self.normalize_cb]),
                    # Row 3: Thinning checkbox, Factor, Max
                    ft.Row(
                        [
                            self.thin_cb,
                            self.thin_factor_field,
                            self.thin_max_interval_field,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    # Row 4: Prefix
                    ft.Row([self.prefix_field]),
                ],
                spacing=8,
            ),
            padding=10,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=8,
        )

    def get_options(self) -> ConversionOptions:
        """Get current options as dataclass."""
        # Parse thin factor
        thin_factor = None
        if self.thin_cb.value and self.thin_factor_field.value:
            try:
                thin_factor = int(self.thin_factor_field.value)
            except ValueError:
                pass

        # Parse thin max interval
        thin_max_interval = None
        if self.thin_cb.value and self.thin_max_interval_field.value:
            try:
                thin_max_interval = int(self.thin_max_interval_field.value)
            except ValueError:
                pass

        return ConversionOptions(
            resample=self.resample_cb.value or False,
            optimize=self.optimize_cb.value or False,
            normalize=self.normalize_cb.value or False,
            prefix=self.prefix_field.value or "",
            thin_factor=thin_factor,
            thin_max_interval=thin_max_interval,
        )
