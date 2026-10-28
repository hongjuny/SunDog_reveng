"""Deterministic source-independent checks for the native image model."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from export_initial_ship import decode_image


class ShipScreenTests(unittest.TestCase):
    def test_repeats(self):
        encoded = bytes([1] + [127, 42]*64)
        page, consumed = decode_image(encoded)
        self.assertEqual(page, bytes([42])*8192)
        self.assertEqual(consumed, len(encoded))

    def test_literal_followed_by_repeats(self):
        encoded = bytes([1, 130, 10, 20, 30] + [127, 99]*64)
        page, consumed = decode_image(encoded)
        self.assertEqual(page[:3], bytes([10,20,30]))
        self.assertEqual(page[3:], bytes([99])*8189)
        self.assertEqual(consumed, len(encoded))

    def test_uneven_strided_columns(self):
        encoded = bytearray([3])
        expected = bytearray(8192)
        for column in range(3):
            positions = list(range(column,8192,3))
            for start in range(0,len(positions),128):
                count=min(128,len(positions)-start)
                encoded.extend((count-1, column+5))
            for position in positions:
                expected[position]=column+5
        page, consumed=decode_image(encoded)
        self.assertEqual(page,expected)
        self.assertEqual(consumed,len(encoded))

    def test_invalid_sources(self):
        for source in (b'',b'\x00',b'\x01\x00',b'\x01\x80'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                decode_image(source)


if __name__=='__main__':unittest.main()
