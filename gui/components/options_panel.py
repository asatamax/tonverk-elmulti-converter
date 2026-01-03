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


class OptionsPanel:
    """Options panel with checkboxes and text field."""

    def __init__(self):
        """Initialize options panel."""
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
            hint_text=Strings.PREFIX_HINT,
            expand=True,
            dense=True,
        )

        # Build container
        self.container = self._build()

    def _build(self) -> ft.Container:
        """Build the options panel container."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        Strings.OPTIONS,
                        weight=ft.FontWeight.BOLD,
                        size=12,
                    ),
                    ft.Row(
                        [
                            self.resample_cb,
                            self.optimize_cb,
                            self.normalize_cb,
                        ],
                        wrap=True,
                    ),
                    self.prefix_field,
                ],
                spacing=8,
            ),
            padding=10,
            border=ft.Border.all(1, ft.Colors.GREY_300),
            border_radius=8,
        )

    def get_options(self) -> ConversionOptions:
        """Get current options as dataclass."""
        return ConversionOptions(
            resample=self.resample_cb.value or False,
            optimize=self.optimize_cb.value or False,
            normalize=self.normalize_cb.value or False,
            prefix=self.prefix_field.value or "",
        )
