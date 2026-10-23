import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from boot_regions import pages
from disk_analysis import DOS_TO_PHYSICAL
from export_splash import normalize_hgr, row_offset


class SplashAssetTests(unittest.TestCase):
    def test_all_visible_bytes_preserved_and_holes_zero(self):
        raw = bytes((i * 17 + 3) & 255 for i in range(8192))
        page = normalize_hgr(raw)
        visible = set()
        for row in range(192):
            start = row_offset(row)
            self.assertEqual(page[start:start + 40], raw[start:start + 40])
            visible.update(range(start, start + 40))
        self.assertEqual(len(visible), 7680)
        self.assertEqual(sum(page[i] != 0 for i in range(8192) if i not in visible), 0)
        self.assertEqual(normalize_hgr(page), page)

    def test_bad_sizes_and_rows_rejected(self):
        for size in (0, 8191, 8193):
            with self.assertRaises(ValueError):
                normalize_hgr(bytes(size))
        for row in (-1, 192):
            with self.assertRaises(ValueError):
                row_offset(row)

    def test_original_loader_order_is_not_disk_image_adjacency(self):
        disk = b''.join(bytes([track, sector]) * 128 for track in range(35) for sector in range(16))
        raw, locations = pages(203, 32, disk)
        for index, source in enumerate(locations):
            logical_page = 406 + index
            physical = (logical_page % 16) * 2 if logical_page % 16 < 8 else (logical_page % 16 - 8) * 2 + 1
            self.assertEqual(source['track'], logical_page // 16)
            self.assertEqual(source['physical_sector'], physical)
            self.assertEqual(source['sector'], DOS_TO_PHYSICAL.index(physical))
            self.assertEqual(raw[index * 256:index * 256 + 256], bytes([source['track'], source['sector']]) * 128)
        self.assertNotEqual(raw, disk[203 * 512:219 * 512])


if __name__ == '__main__':
    unittest.main()
