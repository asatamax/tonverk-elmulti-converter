#!/usr/bin/env python3
"""Tonverk Elmulti Converter - GUI Entry Point.

Usage: python elmconv_gui.py

Requires: flet[all]>=0.80.0
"""

import flet as ft

from gui.app import ElmconvApp


def main(page: ft.Page):
    """Main entry point for Flet application."""
    ElmconvApp(page)


if __name__ == "__main__":
    ft.run(main)
