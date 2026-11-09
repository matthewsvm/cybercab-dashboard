"""file_signature changes when file bytes change, including across a preserved mtime."""
import os
import tempfile
import unittest
from pathlib import Path

from data_signature import file_signature


class FileSignatureTests(unittest.TestCase):
    def test_missing_file_has_a_stable_empty_signature(self):
        missing = Path(tempfile.gettempdir()) / "cybercab-missing-data.csv"
        self.assertFalse(missing.exists())
        self.assertEqual(file_signature(missing), (str(missing), 0, 0, ""))

    def test_same_bytes_keep_the_same_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.csv"
            path.write_bytes(b"date,model\n2026-11-09,Cybercab\n")
            first = file_signature(path)
            second = file_signature(path)
            self.assertEqual(first, second)
            self.assertEqual(first[3], second[3])
            self.assertNotEqual(first[3], "")

    def test_new_bytes_change_the_signature_even_if_mtime_is_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.csv"
            path.write_bytes(b"Tesla,(all models),1282\n")
            before = file_signature(path)
            stamp = path.stat().st_mtime_ns
            path.write_bytes(b"Tesla,Model Y,709\nTesla,Cybercab,573\n")
            os.utime(path, ns=(stamp, stamp))
            after = file_signature(path)
            self.assertEqual(after[1], before[1])
            self.assertNotEqual(after[3], before[3])
            self.assertNotEqual(after, before)


if __name__ == "__main__":
    unittest.main()
