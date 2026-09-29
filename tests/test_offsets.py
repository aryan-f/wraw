"""
Unit tests for scan-index offset handling.
"""

from __future__ import annotations

import unittest

import numpy as np

from wraw.reader import unwrap_offsets


class OffsetTests(unittest.TestCase):
    """
    Verify reconstruction of large DAT positions.
    """

    def test_unwraps_multiple_32bit_rollovers(self):
        """
        Add one 4-GiB epoch after every observed counter rollover.
        """

        raw = np.array(
            [0, 0xFFFFFFF8, 16, 0xFFFFFFF0, 32],
            dtype=np.uint32,
        )

        actual = unwrap_offsets(raw)

        np.testing.assert_array_equal(
            actual,
            [0, 0xFFFFFFF8, (1 << 32) + 16, (1 << 33) - 16, (1 << 33) + 32],
        )


if __name__ == "__main__":
    unittest.main()
