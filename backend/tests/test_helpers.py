import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import safe_name, ass_time, ass_escape

class TestServerHelpers(unittest.TestCase):
    def test_safe_name_clean(self):
        self.assertEqual(safe_name('simple_video.mp4'), 'simple_video.mp4')

    def test_safe_name_special_characters(self):
        name = safe_name('my video & test (1) [HD]!.mov')
        self.assertTrue('my_video' in name)
        self.assertTrue(name.endswith('.mov'))

    def test_safe_name_empty(self):
        self.assertEqual(safe_name(''), 'video.mp4')

    def test_ass_time(self):
        self.assertEqual(ass_time(0), '0:00:00.00')
        self.assertEqual(ass_time(65.5), '0:01:05.50')
        self.assertEqual(ass_time(3661.125), '1:01:01.12')

    def test_ass_escape(self):
        self.assertEqual(ass_escape('Hello {world}'), 'Hello (world)')
        self.assertEqual(ass_escape('Line 1\nLine 2'), 'Line 1 Line 2')

if __name__ == '__main__':
    unittest.main()
