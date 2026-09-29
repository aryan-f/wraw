"""
Unit tests for high-level RAW directory access.
"""

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

import numpy as np

import wraw
from test_decode import encode_bitpacked8


def make_raw_directory(root):
    """
    Construct a minimal synthetic RAW directory.

    Parameters
    ----------
    root
        Temporary parent directory.

    Returns
    -------
    pathlib.Path
        Synthetic RAW directory path.
    """

    raw = root / "example.RAW"
    raw.mkdir()
    (raw / "_HEADER.TXT").write_text(
        "$$ Instrument: Test QTof\r\n"
        "$$ Acquired Name: synthetic\r\n"
        "$$ Cal Function 1: 0.0,1.0,T1\r\n",
        encoding="ascii",
    )
    (raw / "_extern.inf").write_text(
        "Polarity\t\t\tES-\r\n"
        "DesiXLength\t\t\t2.0\r\n"
        "DesiXStep\t\t\t0.5\r\n"
        "Function Parameters - Function 1 - TOF MS FUNCTION\r\n"
        "Data Format\t\t\tContinuum\r\n",
        encoding="ascii",
    )

    descriptor = bytearray(416)
    struct.pack_into("<f", descriptor, 0x01C, 0.014)
    struct.pack_into("<f", descriptor, 0x020, 1.0)
    struct.pack_into("<f", descriptor, 0x0A0, 100.0)
    struct.pack_into("<f", descriptor, 0x120, 1200.0)
    (raw / "_FUNCTNS.INF").write_bytes(descriptor)

    scan0 = [
        encode_bitpacked8(100.0, 0.0),
        encode_bitpacked8(500.5, 10.0),
        encode_bitpacked8(1200.0, 0.0),
    ]
    scan1 = [
        encode_bitpacked8(100.0, 0.0),
        encode_bitpacked8(750.25, 20.0),
        encode_bitpacked8(1200.0, 0.0),
    ]
    (raw / "_FUNC001.DAT").write_bytes(
        np.array(scan0 + scan1, dtype="<u8").tobytes()
    )

    index = bytearray(60)
    struct.pack_into("<f", index, 0x08, 10.0)
    struct.pack_into("<f", index, 0x0C, 0.1)
    struct.pack_into("<I", index, 0x16, 0)
    struct.pack_into("<f", index, 30 + 0x08, 20.0)
    struct.pack_into("<f", index, 30 + 0x0C, 0.2)
    struct.pack_into("<I", index, 30 + 0x16, 24)
    (raw / "_FUNC001.IDX").write_bytes(index)
    return raw


class RawFileTests(unittest.TestCase):
    """
    Verify the public reader using a synthetic RAW directory.
    """

    def test_opens_metadata_and_reads_spectra(self):
        """
        Read metadata and a randomly selected spectrum.
        """

        with tempfile.TemporaryDirectory() as directory:
            raw = wraw.read(make_raw_directory(Path(directory)))

            self.assertEqual(raw.metadata["Instrument"], "Test QTof")
            self.assertEqual(raw.polarity, "ES-")
            self.assertEqual(raw.metadata["DesiXLength"], "2.0")
            self.assertEqual(len(raw.functions), 1)

            function = raw.function(1)
            self.assertEqual(function.scan_count, 2)
            self.assertEqual(function.encoding, "bitpacked8")
            self.assertEqual(function.description, "TOF MS FUNCTION")
            np.testing.assert_allclose(function.retention_times, [0.1, 0.2])
            np.testing.assert_allclose(function.tic, [10.0, 20.0])

            spectrum = raw.read_spectrum(1, 1)
            self.assertEqual(spectrum.function_number, 1)
            self.assertEqual(spectrum.scan_index, 1)
            self.assertAlmostEqual(spectrum.retention_time_min, 0.2, places=6)
            np.testing.assert_allclose(spectrum.mz, [100.0, 750.25, 1200.0])
            np.testing.assert_allclose(spectrum.intensity, [0.0, 20.0, 0.0])
            self.assertEqual(spectrum.tic, 20.0)
            self.assertEqual(spectrum.base_peak_index, 1)

    def test_rejects_unknown_function_and_scan(self):
        """
        Reject function numbers and scan indices outside the acquisition.
        """

        with tempfile.TemporaryDirectory() as directory:
            raw = wraw.read(make_raw_directory(Path(directory)))
            with self.assertRaises(KeyError):
                raw.function(2)
            with self.assertRaises(IndexError):
                raw.function(1).read_spectrum(2)


if __name__ == "__main__":
    unittest.main()
