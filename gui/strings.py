"""Localization strings for GUI.

All user-facing strings are centralized here for future localization.
"""


class Strings:
    """Centralized strings for the GUI."""

    # Window
    APP_TITLE = "Tonverk Elmulti Converter"

    # Output section
    OUTPUT_FOLDER = "OUTPUT FOLDER"
    OUTPUT_HINT = "Select output folder first"
    BROWSE = "Browse"
    OUTPUT_NOT_EMPTY_WARNING = (
        "Warning: Output folder is not empty. Existing files may be overwritten."
    )

    # Options section
    OPTIONS = "OPTIONS"
    RESAMPLE_48K = "Resample to 48 kHz"
    OPTIMIZE_LOOPS = "Optimize loop points"
    NORMALIZE = "Normalize"
    PREFIX_LABEL = "Prefix"
    PREFIX_HINT = "Optional prefix for output names"

    # Input section
    SELECT_INPUT = "SELECT INPUT"
    SELECT_FILES = "Select File(s)"
    SELECT_FOLDER = "Select Folder"
    INPUT_HINT = ".exs / .sfz files"

    # Log section
    CONVERSION_LOG = "CONVERSION LOG"
    COPY = "Copy"
    COPY_DEBUG = "Copy Debug"
    CLEAR = "Clear"
    LOG_COPIED = "Log copied to clipboard"
    DEBUG_LOG_COPIED = "Debug log copied to clipboard (detailed output)"
    READY_MESSAGE = "Ready. Select output folder to begin."

    # Dialogs
    SELECT_OUTPUT_TITLE = "Select Output Folder"
    SELECT_FILES_TITLE = "Select EXS/SFZ Files"
    SELECT_INPUT_FOLDER_TITLE = "Select Folder Containing EXS/SFZ Files"
    CONVERSION_COMPLETE = "Conversion Complete"
    OK = "OK"

    # Errors
    SELECT_OUTPUT_FIRST = "Please select output folder first"
    NO_FILES_FOUND = "No .exs or .sfz files found in {folder}"
    FFMPEG_NOT_FOUND = "ffmpeg is required but not found"

    # Progress
    STARTING_CONVERSION = "Starting conversion of {count} file(s)..."
    CONVERTING_FILE = "[{current}/{total}] Converting {filename}..."
    CONVERSION_DONE = "Done"
    CONVERSION_RESULT = "Successfully converted {success}/{total} file(s)."
