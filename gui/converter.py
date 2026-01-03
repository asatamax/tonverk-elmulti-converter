"""Bridge between GUI and elmconv.py conversion functions."""

import asyncio
import io
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable

# Import from elmconv (after Phase 1 refactoring)
from elmconv import (
    ConversionError,
    ConversionStats,
    ValidationError,
    check_ffmpeg_for_gui,
    convert_to_elmulti,
)


class ConverterBridge:
    """Bridges GUI to elmconv.py conversion functions."""

    def __init__(self, log_callback: Callable[[str, str], None]):
        """Initialize bridge with log callback.

        Args:
            log_callback: Function(message, level) for logging
        """
        self.log = log_callback
        self._cancel_requested = False
        self._debug_log: list[str] = []

    def get_debug_log(self) -> str:
        """Get the detailed debug log from last conversion.

        Returns:
            str: Full stdout output from conversion
        """
        return "\n".join(self._debug_log)

    def clear_debug_log(self):
        """Clear the debug log."""
        self._debug_log.clear()

    def check_ffmpeg(self) -> tuple[bool, str]:
        """Check if ffmpeg is available.

        Returns:
            tuple: (is_available, error_message)
        """
        available, soxr, error = check_ffmpeg_for_gui()
        if not available or not soxr:
            return False, error
        return True, ""

    async def convert_files(
        self,
        input_paths: list[str],
        output_dir: str,
        resample: bool = True,
        optimize: bool = True,
        normalize: bool = False,
        prefix: str = "",
    ) -> tuple[int, int]:
        """Convert multiple files asynchronously.

        Args:
            input_paths: List of input file paths
            output_dir: Output directory
            resample: Enable 48kHz resampling
            optimize: Enable loop optimization
            normalize: Enable normalization
            prefix: Output name prefix

        Returns:
            tuple: (success_count, total_count)
        """
        self._cancel_requested = False
        self.clear_debug_log()
        total = len(input_paths)
        success = 0

        # Create shared stats instance
        stats = ConversionStats()

        for i, path in enumerate(input_paths, 1):
            if self._cancel_requested:
                self.log("Conversion cancelled by user", "warning")
                break

            filename = Path(path).name
            self.log(f"[{i}/{total}] Converting {filename}...", "info")

            try:
                # Run conversion in thread to avoid blocking UI
                await asyncio.to_thread(
                    self._convert_single,
                    path,
                    output_dir,
                    resample,
                    optimize,
                    normalize,
                    prefix,
                    stats,
                )
                self.log("  -> Done", "success")
                success += 1

            except ConversionError as e:
                self.log(f"  -> Error: {e}", "error")
            except ValidationError as e:
                self.log(f"  -> Validation error: {e}", "error")
            except Exception as e:
                self.log(f"  -> Unexpected error: {e}", "error")

        return success, total

    def _convert_single(
        self,
        input_path: str,
        output_dir: str,
        resample: bool,
        optimize: bool,
        normalize: bool,
        prefix: str,
        stats: ConversionStats,
    ):
        """Convert a single file (runs in thread).

        Captures stdout for debug log.
        """
        # Capture stdout for debug log
        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            convert_to_elmulti(
                input_path=input_path,
                output_dir=output_dir,
                target_rate=48000 if resample else None,
                optimize_loops=optimize,
                normalize_db=0.0 if normalize else None,
                prefix=prefix,
            )

        # Store captured output
        captured = stdout_capture.getvalue()
        if captured:
            self._debug_log.append(captured)

    def cancel(self):
        """Request cancellation of ongoing conversion."""
        self._cancel_requested = True
