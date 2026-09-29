"""
Decoders for validated Waters spectrum records.
"""

from __future__ import annotations

import numpy as np
from .errors import UnsupportedFormatError
from .models import Calibration


# Public format reference for the independently reverse-engineered eight-byte bit layout:
# https://rainbow-api.readthedocs.io/en/latest/waters/funcdat8.html
LOW_28_BITS = np.uint64(0x0FFFFFFF)


def low_bits_mask(bit_count):
    """
    Construct integer masks containing a requested number of low bits.

    Parameters
    ----------
    bit_count
        Number of one-bits required in each mask.

    Returns
    -------
    numpy.ndarray
        Unsigned 64-bit masks with the same shape as ``bit_count``.
    """

    return np.left_shift(np.uint64(1), bit_count) - np.uint64(1)


def apply_calibration(mz, calibration):
    """
    Apply a validated function calibration to raw mass values.

    Parameters
    ----------
    mz : numpy.ndarray
        Uncalibrated mass values.
    calibration : Calibration or None
        Function calibration, or ``None`` to leave the masses unchanged.

    Returns
    -------
    numpy.ndarray
        Calibrated float64 mass values.

    Raises
    ------
    UnsupportedFormatError
        If the calibration equation has not been validated.
    """

    # Public cross-check for the independently documented T1 square-root-mass polynomial:
    # https://sigilweaver.app/openwraw/docs/format/overview/#mz-decoding-summary
    if calibration is None:
        return mz
    if calibration.kind.upper() != "T1":
        raise UnsupportedFormatError(
            f"calibration equation {calibration.kind!r} is not supported"
        )

    root_mz = np.sqrt(mz)
    calibrated_root = np.zeros_like(root_mz)
    for coefficient in reversed(calibration.coefficients):
        calibrated_root *= root_mz
        calibrated_root += coefficient
    return calibrated_root * calibrated_root


def decode_bitpacked8(words, calibration=None):
    """
    Decode eight-byte variable-precision m/z-intensity records.

    Parameters
    ----------
    words : array-like
        One-dimensional array-like object containing little-endian unsigned
        64-bit records.
    calibration : Calibration or None, optional
        Optional function calibration.

    Returns
    -------
    mz
        Decoded float32 m/z values.
    intensity
        Decoded float32 intensity values.
    """

    raw = np.asarray(words, dtype="<u8")

    key_bits = raw >> np.uint64(28)
    integer_bits = key_bits >> np.uint64(31)
    fractional_bits = np.uint64(31) - integer_bits
    integer_mask = low_bits_mask(integer_bits)
    fractional_mask = low_bits_mask(fractional_bits)

    mz = ((key_bits >> fractional_bits) & integer_mask).astype(np.float64)
    mz += np.ldexp(
        (key_bits & fractional_mask).astype(np.float64),
        -fractional_bits.astype(np.int32),
    )

    value_bits = raw & LOW_28_BITS
    declared_integer_bits = value_bits >> np.uint64(22)
    left_shift = np.maximum(
        declared_integer_bits.astype(np.int16) - 21,
        0,
    ).astype(np.uint64)
    stored_integer_bits = np.minimum(declared_integer_bits, np.uint64(21))
    value_fractional_bits = np.uint64(21) - stored_integer_bits
    value_integer_mask = low_bits_mask(stored_integer_bits)
    value_fractional_mask = low_bits_mask(value_fractional_bits)

    intensity = np.left_shift(
        (value_bits >> value_fractional_bits) & value_integer_mask,
        left_shift,
    ).astype(np.float64)
    intensity += np.ldexp(
        (value_bits & value_fractional_mask).astype(np.float64),
        -value_fractional_bits.astype(np.int32),
    )

    mz = apply_calibration(mz, calibration)
    return mz.astype(np.float32), intensity.astype(np.float32)


def decode_bitpacked8_mz(words):
    """
    Decode only the uncalibrated m/z component of eight-byte records.

    Parameters
    ----------
    words : array-like
        One-dimensional array-like object containing little-endian unsigned
        64-bit records.

    Returns
    -------
    numpy.ndarray
        Uncalibrated float64 m/z values.
    """

    raw = np.asarray(words, dtype="<u8")
    key_bits = raw >> np.uint64(28)
    integer_bits = key_bits >> np.uint64(31)
    fractional_bits = np.uint64(31) - integer_bits
    integer_mask = low_bits_mask(integer_bits)
    fractional_mask = low_bits_mask(fractional_bits)
    result = ((key_bits >> fractional_bits) & integer_mask).astype(np.float64)
    result += np.ldexp(
        (key_bits & fractional_mask).astype(np.float64),
        -fractional_bits.astype(np.int32),
    )
    return result
