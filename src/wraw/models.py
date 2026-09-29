"""
Data models returned by :mod:`wraw`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True, slots=True)
class Calibration:
    """
    Calibration polynomial associated with an acquisition function.

    Parameters
    ----------
    coefficients : tuple of float
        Polynomial coefficients in ascending order.
    kind : str
        Waters calibration equation identifier, such as ``"T1"``.
    """

    coefficients: tuple[float, ...]
    kind: str


@dataclass(frozen=True, slots=True)
class Spectrum:
    """
    One mass spectrum from a RAW acquisition function.

    Parameters
    ----------
    function_number : int
        One-based acquisition function number.
    scan_index : int
        Zero-based scan index within the function.
    retention_time_min : float
        Scan retention time in minutes.
    mz : numpy.ndarray
        One-dimensional m/z array.
    intensity : numpy.ndarray
        One-dimensional intensity array corresponding to ``mz``.
    """

    function_number: int
    scan_index: int
    retention_time_min: float
    mz: npt.NDArray[np.float32]
    intensity: npt.NDArray[np.float32]

    def __post_init__(self):
        """
        Validate and freeze the spectrum arrays.

        Raises
        ------
        ValueError
            If the arrays are not one-dimensional or have different lengths.
        """

        if self.mz.ndim != 1 or self.intensity.ndim != 1:
            raise ValueError("spectrum arrays must be one-dimensional")
        if self.mz.shape != self.intensity.shape:
            raise ValueError("m/z and intensity arrays must have the same shape")
        self.mz.flags.writeable = False
        self.intensity.flags.writeable = False

    @property
    def tic(self):
        """
        Return the total ion current.

        Returns
        -------
        float
            Sum of all intensities using a float64 accumulator.
        """

        return float(self.intensity.sum(dtype=np.float64))

    @property
    def base_peak_index(self):
        """
        Return the index of the most intense point.

        Returns
        -------
        int or None
            Index of the first maximum, or ``None`` for an empty spectrum.
        """

        if self.intensity.size == 0:
            return None
        return int(np.argmax(self.intensity))
