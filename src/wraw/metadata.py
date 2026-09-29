"""
Parsers for metadata files found in Waters RAW directories.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass

from .errors import UnsupportedFormatError
from .models import Calibration


# Public cross-check for the independently reverse-engineered 416-byte record layout and field offsets:
# https://sigilweaver.app/openwraw/docs/format/functns-inf/
FUNCTION_RECORD_SIZE = 416
CALIBRATION_KEY = re.compile(r"^Cal Function (\d+)$", re.IGNORECASE)
FUNCTION_HEADING = re.compile(
    r"^Function Parameters\s*-\s*Function\s+(\d+)\s*-\s*(.+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class FunctionDescriptor:
    """
    Binary acquisition-function descriptor.

    Parameters
    ----------
    number : int
        One-based function number.
    interscan_time_s : float
        Interscan delay in seconds.
    scan_time_s : float
        Scan duration in seconds.
    mass_low : float
        Lower acquisition mass.
    mass_high : float
        Upper acquisition mass.
    """

    number: int
    interscan_time_s: float
    scan_time_s: float
    mass_low: float
    mass_high: float


def clean_text(value):
    """
    Remove non-printing characters from decoded metadata text.

    Parameters
    ----------
    value : str
        Text to clean.

    Returns
    -------
    str
        Stripped printable text, preserving tabs.
    """

    return "".join(
        character for character in value if character >= " " or character == "\t"
    ).strip()


def parse_header(path):
    """
    Parse `_HEADER.TXT` metadata and function calibrations.

    Parameters
    ----------
    path : pathlib.Path
        Header file path.

    Returns
    -------
    metadata
        Header fields keyed by their textual names.
    calibrations
        Calibrations keyed by one-based function number.
    """

    metadata = {}
    calibrations = {}
    text = path.read_text(encoding="latin-1", errors="replace")

    for line in text.splitlines():
        if not line.startswith("$$ ") or ":" not in line:
            continue
        key, value = line[3:].split(":", 1)
        key = clean_text(key)
        value = clean_text(value)
        metadata[key] = value

        match = CALIBRATION_KEY.match(key)
        if match is None or not value:
            continue
        parts = [part.strip() for part in value.split(",")]
        if len(parts) < 2 or not re.fullmatch(r"T\d+", parts[-1], re.IGNORECASE):
            continue
        try:
            coefficients = tuple(float(part) for part in parts[:-1] if part)
        except ValueError:
            continue
        if coefficients:
            calibrations[int(match.group(1))] = Calibration(
                coefficients=coefficients,
                kind=parts[-1].upper(),
            )

    return metadata, calibrations


def split_metadata_line(line):
    """
    Split a human-readable method line into a key and value.

    Parameters
    ----------
    line : str
        One line from `_extern.inf`.

    Returns
    -------
    tuple of str or None
        Parsed key and value, or ``None`` when the line is not a field.
    """

    parts = re.split(r"\t+|\s{2,}", line.strip(), maxsplit=1)
    if len(parts) != 2:
        return None
    key, value = (clean_text(part) for part in parts)
    if not key or not value:
        return None
    return key, value


def parse_extern(path):
    """
    Parse `_extern.inf` polarity and per-function metadata.

    Parameters
    ----------
    path : pathlib.Path
        External method-information file path.

    Returns
    -------
    polarity
        Ionization polarity string when present.
    metadata
        Global method fields found before the function sections.
    functions
        Per-function metadata keyed by one-based function number.
    """

    polarity = None
    metadata = {}
    functions = {}
    current_function = None
    text = path.read_text(encoding="latin-1", errors="replace")

    for raw_line in text.splitlines():
        line = clean_text(raw_line)
        heading = FUNCTION_HEADING.match(line)
        if heading is not None:
            current_function = int(heading.group(1))
            functions[current_function] = {"Description": clean_text(heading.group(2))}
            continue

        field = split_metadata_line(line)
        if field is None:
            continue
        key, value = field
        if key == "Polarity" and polarity is None:
            polarity = value
        if current_function is None:
            metadata[key] = value
        else:
            functions[current_function][key] = value

    return polarity, metadata, functions


def parse_function_descriptors(path):
    """
    Parse the validated 416-byte `_FUNCTNS.INF` record layout.

    Parameters
    ----------
    path : pathlib.Path
        Function table path.

    Returns
    -------
    tuple of FunctionDescriptor
        Function descriptors in file order.

    Raises
    ------
    UnsupportedFormatError
        If the file does not consist of 416-byte records.
    """

    data = path.read_bytes()
    if not data or len(data) % FUNCTION_RECORD_SIZE:
        raise UnsupportedFormatError(
            f"{path.name}: expected one or more {FUNCTION_RECORD_SIZE}-byte records"
        )

    descriptors = []
    for index in range(len(data) // FUNCTION_RECORD_SIZE):
        record = memoryview(data)[
            index * FUNCTION_RECORD_SIZE : (index + 1) * FUNCTION_RECORD_SIZE
        ]
        descriptors.append(
            FunctionDescriptor(
                number=index + 1,
                interscan_time_s=struct.unpack_from("<f", record, 0x01C)[0],
                scan_time_s=struct.unpack_from("<f", record, 0x020)[0],
                mass_low=struct.unpack_from("<f", record, 0x0A0)[0],
                mass_high=struct.unpack_from("<f", record, 0x120)[0],
            )
        )
    return tuple(descriptors)
