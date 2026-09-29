"""
Read Waters MassLynx RAW directories without vendor runtime dependencies.
"""

from .errors import (
    CorruptRawFileError,
    InvalidRawDirectoryError,
    UnsupportedFormatError,
    WRawError,
)
from .models import Calibration, Spectrum
from .reader import RawFile, RawFunction, read
