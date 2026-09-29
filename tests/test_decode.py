"""
Unit tests for the validated eight-byte spectrum decoder.
"""

from __future__ import annotations

import unittest

import numpy as np

from wraw.decode import decode_bitpacked8
from wraw.models import Calibration


def encode_bitpacked8(mz, intensity):
    """
    Encode a value pair for synthetic decoder tests.

    Parameters
    ----------
    mz
        Non-negative m/z value representable by the test encoder.
    intensity
        Non-negative intensity below ``2**21``.

    Returns
    -------
    numpy.uint64
        Packed synthetic record.
    """

    mz_integer_bits = max(1, int(mz).bit_length())
    mz_fractional_bits = 31 - mz_integer_bits
    mz_integer = int(mz)
    mz_fraction = round((mz - mz_integer) * (1 << mz_fractional_bits))
    key = (
        (mz_integer_bits << 31)
        | (mz_integer << mz_fractional_bits)
        | mz_fraction
    )

    intensity_integer_bits = max(1, int(intensity).bit_length())
    if intensity_integer_bits > 21:
        raise ValueError("test encoder only supports intensities below 2**21")
    intensity_fractional_bits = 21 - intensity_integer_bits
    intensity_integer = int(intensity)
    intensity_fraction = round(
        (intensity - intensity_integer) * (1 << intensity_fractional_bits)
    )
    value = (
        (intensity_integer_bits << 22)
        | (intensity_integer << intensity_fractional_bits)
        | intensity_fraction
    )
    return np.uint64((key << 28) | value)


class DecodeBitpacked8Tests(unittest.TestCase):
    """
    Verify decoding independently from RAW directory parsing.
    """

    def test_decodes_integer_and_fractional_values(self):
        """
        Decode representative m/z and intensity fractions.
        """

        words = np.array(
            [
                encode_bitpacked8(100.5, 42.25),
                encode_bitpacked8(1200.0, 0.0),
            ],
            dtype="<u8",
        )

        mz, intensity = decode_bitpacked8(words)

        np.testing.assert_allclose(mz, [100.5, 1200.0])
        np.testing.assert_allclose(intensity, [42.25, 0.0])

    def test_applies_t1_calibration_to_square_root_mass(self):
        """
        Apply T1 coefficients to the square root of raw mass.
        """

        words = np.array([encode_bitpacked8(400.0, 1.0)], dtype="<u8")
        calibration = Calibration((1.0, 1.0), "T1")

        mz, _ = decode_bitpacked8(words, calibration)

        self.assertAlmostEqual(float(mz[0]), 441.0)


if __name__ == "__main__":
    unittest.main()
