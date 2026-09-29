"""
Exceptions raised by :mod:`wraw`.
"""


class WRawError(Exception):
    """
    Base exception for errors raised by wraw.
    """


class InvalidRawDirectoryError(WRawError):
    """
    Raised when a path is not a recognizable RAW directory.
    """


class UnsupportedFormatError(WRawError):
    """
    Raised when a RAW layout has not been implemented or validated.
    """


class CorruptRawFileError(WRawError):
    """
    Raised when files in a RAW directory are internally inconsistent.
    """
