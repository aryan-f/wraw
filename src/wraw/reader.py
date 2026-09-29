"""
Lazy, high-level access to Waters RAW directories.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .decode import decode_bitpacked8, decode_bitpacked8_mz
from .errors import CorruptRawFileError, InvalidRawDirectoryError, UnsupportedFormatError
from .metadata import (
    FunctionDescriptor,
    parse_extern,
    parse_function_descriptors,
    parse_header,
)
from .models import Calibration, Spectrum


# Public cross-check for the independently reverse-engineered 30-byte index layout and field offsets:
# https://sigilweaver.app/openwraw/docs/format/func-idx/
INDEX_RECORD_SIZE = 30
INDEX_DTYPE = np.dtype(
    {
        "names": ["tic", "retention_time", "dat_offset"],
        "formats": ["<f4", "<f4", "<u4"],
        "offsets": [0x08, 0x0C, 0x16],
        "itemsize": INDEX_RECORD_SIZE,
    }
)


def unwrap_offsets(offsets):
    """
    Expand rolling 32-bit DAT offsets into monotonic 64-bit positions.

    Parameters
    ----------
    offsets : array-like
        One-dimensional sequence of unsigned 32-bit offsets in scan order.

    Returns
    -------
    numpy.ndarray
        Unsigned 64-bit offsets with one 4-GiB increment added after every
        rollover.

    Raises
    ------
    ValueError
        If ``offsets`` is not one-dimensional.
    """

    raw = np.asarray(offsets, dtype=np.uint32)
    if raw.ndim != 1:
        raise ValueError("offsets must be one-dimensional")
    if raw.size == 0:
        return raw.astype(np.uint64)

    rollovers = np.concatenate(
        (
            np.zeros(1, dtype=np.uint64),
            np.cumsum(raw[1:] < raw[:-1], dtype=np.uint64),
        )
    )
    return raw.astype(np.uint64) + rollovers * np.uint64(1 << 32)


class RawFunction:
    """
    One acquisition function with lazy random-access spectrum reads.

    Parameters
    ----------
    parent : RawFile
        Parent RAW directory reader.
    descriptor : FunctionDescriptor
        Parsed binary function descriptor.
    dat_path : pathlib.Path
        Function DAT path.
    idx_path : pathlib.Path
        Function IDX path.
    calibration : Calibration or None
        Function calibration when present.
    metadata : collections.abc.Mapping
        Human-readable function metadata.
    """

    def __init__(self, parent, descriptor, dat_path, idx_path, calibration, metadata):
        """
        Initialize a function reader and validate its scan index.
        """

        self.parent = parent
        self.descriptor = descriptor
        self.dat_path = dat_path
        self.idx_path = idx_path
        self.calibration = calibration
        self.metadata = dict(metadata)

        idx_size = idx_path.stat().st_size
        if idx_size == 0 or idx_size % INDEX_RECORD_SIZE:
            raise UnsupportedFormatError(
                f"{idx_path.name}: expected non-empty {INDEX_RECORD_SIZE}-byte records"
            )
        self.index = np.fromfile(idx_path, dtype=INDEX_DTYPE)
        self.offsets = unwrap_offsets(self.index["dat_offset"])
        self.validate_offsets()
        self.encoding = self.detect_encoding()

    @property
    def number(self):
        """
        Return the one-based function number.

        Returns
        -------
        int
            Function number corresponding to `_FUNCnnn.*`.
        """

        return self.descriptor.number

    @property
    def description(self):
        """
        Return the human-readable function description.

        Returns
        -------
        str or None
            Description from `_extern.inf`, when present.
        """

        return self.metadata.get("Description")

    @property
    def scan_count(self):
        """
        Return the number of indexed scans.

        Returns
        -------
        int
            Number of IDX records.
        """

        return int(self.index.size)

    @property
    def scan_time_s(self):
        """
        Return the nominal scan duration in seconds.

        Returns
        -------
        float
            Scan duration from `_FUNCTNS.INF`.
        """

        return self.descriptor.scan_time_s

    @property
    def interscan_time_s(self):
        """
        Return the nominal interscan delay in seconds.

        Returns
        -------
        float
            Interscan delay from `_FUNCTNS.INF`.
        """

        return self.descriptor.interscan_time_s

    @property
    def mass_range(self):
        """
        Return the nominal acquisition mass range.

        Returns
        -------
        tuple of float
            Lower and upper masses from `_FUNCTNS.INF`.
        """

        return self.descriptor.mass_low, self.descriptor.mass_high

    @property
    def polarity(self):
        """
        Return the acquisition polarity.

        Returns
        -------
        str or None
            Run polarity from `_extern.inf`.
        """

        return self.parent.polarity

    @property
    def data_format(self):
        """
        Return the human-readable acquisition data mode.

        Returns
        -------
        str or None
            Value such as ``"Continuum"`` when present.
        """

        return self.metadata.get("Data Format")

    @property
    def retention_times(self):
        """
        Return a read-only copy of all scan retention times.

        Returns
        -------
        numpy.ndarray
            Float32 retention times in minutes.
        """

        result = np.asarray(self.index["retention_time"], dtype=np.float32).copy()
        result.flags.writeable = False
        return result

    @property
    def tic(self):
        """
        Return the total ion current recorded for every scan.

        Returns
        -------
        numpy.ndarray
            Float32 total ion current values in scan order.
        """

        result = np.asarray(self.index["tic"], dtype=np.float32).copy()
        result.flags.writeable = False
        return result

    def read_spectrum(self, scan_index):
        """
        Decode one zero-based scan.

        Parameters
        ----------
        scan_index : int
            Zero-based scan index within this function.

        Returns
        -------
        Spectrum
            Decoded m/z and intensity arrays with scan metadata.

        Raises
        ------
        TypeError
            If ``scan_index`` is not an integer.
        IndexError
            If ``scan_index`` is outside this function.
        """

        if not isinstance(scan_index, int):
            raise TypeError("scan_index must be an integer")
        if scan_index < 0 or scan_index >= self.scan_count:
            raise IndexError(
                f"scan index {scan_index} is outside 0..{self.scan_count - 1} "
                f"for function {self.number}"
            )

        start, stop = self.scan_byte_range(scan_index)
        words = np.memmap(
            self.dat_path,
            dtype="<u8",
            mode="r",
            offset=start,
            shape=((stop - start) // 8,),
        )
        mz, intensity = decode_bitpacked8(words, self.calibration)
        return Spectrum(
            function_number=self.number,
            scan_index=scan_index,
            retention_time_min=float(self.index["retention_time"][scan_index]),
            mz=mz,
            intensity=intensity,
        )

    def iter_spectra(self):
        """
        Iterate over spectra in scan order.

        Yields
        ------
        Spectrum
            One lazily decoded spectrum at a time.
        """

        for scan_index in range(self.scan_count):
            yield self.read_spectrum(scan_index)

    def scan_byte_range(self, scan_index):
        """
        Return the DAT byte range occupied by one scan.

        Parameters
        ----------
        scan_index : int
            Valid zero-based scan index.

        Returns
        -------
        tuple of int
            Start-inclusive and stop-exclusive DAT offsets.
        """

        start = int(self.offsets[scan_index])
        if scan_index + 1 < self.scan_count:
            stop = int(self.offsets[scan_index + 1])
        else:
            stop = self.dat_path.stat().st_size
        return start, stop

    def validate_offsets(self):
        """
        Validate reconstructed DAT offsets and eight-byte scan boundaries.

        Raises
        ------
        CorruptRawFileError
            If offsets are empty, decreasing, or outside the DAT file.
        UnsupportedFormatError
            If indexed scan sizes are not divisible by eight.
        """

        dat_size = self.dat_path.stat().st_size
        if self.offsets.size == 0:
            raise CorruptRawFileError(f"{self.idx_path.name} contains no scans")
        if np.any(self.offsets[1:] < self.offsets[:-1]):
            raise CorruptRawFileError(
                f"{self.idx_path.name} contains decreasing DAT offsets"
            )
        if int(self.offsets[-1]) > dat_size:
            raise CorruptRawFileError(
                f"{self.idx_path.name} points beyond {self.dat_path.name}"
            )

        boundaries = np.concatenate(
            (self.offsets, np.array([dat_size], dtype=np.uint64))
        )
        if np.any(np.diff(boundaries) % 8):
            raise UnsupportedFormatError(
                f"{self.dat_path.name}: scan sizes do not match eight-byte records"
            )

    def detect_encoding(self):
        """
        Identify the validated DAT record encoding from scan boundaries.

        Returns
        -------
        str
            ``"bitpacked8"`` for the supported representation.

        Raises
        ------
        UnsupportedFormatError
            If representative scan boundaries do not match the declared mass
            range under the validated decoder.
        """

        expected = np.asarray(self.mass_range, dtype=np.float64)
        tolerance = np.maximum(1.0, np.abs(expected) * 0.01)

        for scan_index in range(min(self.scan_count, 64)):
            start, stop = self.scan_byte_range(scan_index)
            if stop - start < 16:
                continue
            words = np.memmap(
                self.dat_path,
                dtype="<u8",
                mode="r",
                offset=start,
                shape=((stop - start) // 8,),
            )
            boundary_mz = decode_bitpacked8_mz(words[[0, -1]])
            if np.all(np.isfinite(boundary_mz)) and np.all(
                np.abs(boundary_mz - expected) <= tolerance
            ):
                return "bitpacked8"

        raise UnsupportedFormatError(
            f"{self.dat_path.name}: records do not match the validated "
            "eight-byte representation"
        )

    def __repr__(self):
        """
        Return a concise diagnostic representation.

        Returns
        -------
        str
            Function number and scan count.
        """

        return f"RawFunction(number={self.number}, scan_count={self.scan_count})"


class RawFile:
    """
    Reader for a Waters MassLynx RAW directory.

    Parameters
    ----------
    path : pathlib.Path
        Path to a `.raw` directory.
    """

    def __init__(self, path):
        """
        Parse run metadata and initialize all acquisition functions.

        Raises
        ------
        InvalidRawDirectoryError
            If ``path`` is not a directory or required files are missing.
        """

        self.path = Path(path).expanduser()
        if not self.path.is_dir():
            raise InvalidRawDirectoryError(f"not a RAW directory: {self.path}")

        self.files = {
            child.name.upper(): child
            for child in self.path.iterdir()
            if child.is_file()
        }
        header_path = self.require_file("_HEADER.TXT")
        functions_path = self.require_file("_FUNCTNS.INF")

        metadata, calibrations = parse_header(header_path)
        self.metadata = metadata
        self.calibrations = calibrations

        extern_path = self.files.get("_EXTERN.INF")
        if extern_path is None:
            self.polarity = None
            external_functions = {}
        else:
            self.polarity, external_metadata, external_functions = parse_extern(extern_path)
            self.metadata.update(external_metadata)

        descriptors = parse_function_descriptors(functions_path)
        self.functions = tuple(
            RawFunction(
                parent=self,
                descriptor=descriptor,
                dat_path=self.require_file(f"_FUNC{descriptor.number:03d}.DAT"),
                idx_path=self.require_file(f"_FUNC{descriptor.number:03d}.IDX"),
                calibration=calibrations.get(descriptor.number),
                metadata=external_functions.get(descriptor.number, {}),
            )
            for descriptor in descriptors
        )

    def function(self, number):
        """
        Return an acquisition function by one-based number.

        Parameters
        ----------
        number : int
            One-based function number.

        Returns
        -------
        RawFunction
            Requested acquisition function.

        Raises
        ------
        KeyError
            If the function is not present.
        """

        for function in self.functions:
            if function.number == number:
                return function
        raise KeyError(f"RAW directory has no function {number}")

    def read_spectrum(self, function_number, scan_index):
        """
        Decode one spectrum selected by function and scan.

        Parameters
        ----------
        function_number : int
            One-based acquisition function number.
        scan_index : int
            Zero-based scan index within the function.

        Returns
        -------
        Spectrum
            Decoded spectrum.
        """

        return self.function(function_number).read_spectrum(scan_index)

    def require_file(self, name):
        """
        Return a required file using case-insensitive name matching.

        Parameters
        ----------
        name : str
            Required base name.

        Returns
        -------
        pathlib.Path
            Existing file path.

        Raises
        ------
        InvalidRawDirectoryError
            If the file is absent.
        """

        path = self.files.get(name.upper())
        if path is None:
            raise InvalidRawDirectoryError(f"{self.path} is missing {name}")
        return path

    def __repr__(self):
        """
        Return a concise diagnostic representation.

        Returns
        -------
        str
            RAW path and function count.
        """

        return f"RawFile(path={str(self.path)!r}, functions={len(self.functions)})"


def read(path):
    """
    Open a Waters MassLynx RAW directory.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to a `.raw` directory.

    Returns
    -------
    RawFile
        Parsed, lazy RAW reader.
    """
    path = Path(path).expanduser()
    return RawFile(path)
