import tempfile
import unittest
from pathlib import Path

from cyberscope.collectors.usb import collect_usb_sysfs, parse_lsusb


class UsbCollectorTests(unittest.TestCase):
    def test_parse_lsusb_is_sorted_and_extracts_ids(self) -> None:
        rows = parse_lsusb(
            "Bus 002 Device 003: ID 0781:5591 SanDisk Corp. Ultra\n"
            "Bus 001 Device 002: ID 1d6b:0002 Linux Foundation 2.0 root hub\n"
        )
        self.assertEqual(rows[0]["vendor_id"], "0781")
        self.assertEqual(rows[0]["product_id"], "5591")
        self.assertEqual(rows[1]["vendor_id"], "1d6b")

    def test_sysfs_collection_uses_stable_identity_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            device = Path(directory) / "1-1"
            device.mkdir()
            (device / "idVendor").write_text("0781\n")
            (device / "idProduct").write_text("5591\n")
            (device / "manufacturer").write_text("SanDisk\n")
            (device / "product").write_text("Ultra\n")
            (device / "serial").write_text("ABC123\n")
            devices = collect_usb_sysfs(Path(directory))
        self.assertEqual(
            devices,
            [{"vendor_id": "0781", "product_id": "5591", "manufacturer": "SanDisk", "product": "Ultra", "serial": "ABC123"}],
        )


if __name__ == "__main__":
    unittest.main()
