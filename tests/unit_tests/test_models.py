import unittest

from cyberscope.models import Measurement


class MeasurementTests(unittest.TestCase):
    def test_unsupported_measurement_has_required_shape(self) -> None:
        self.assertEqual(
            Measurement.unsupported("not a Pi").to_dict(),
            {"supported": False, "value": None, "reason": "not a Pi"},
        )

    def test_supported_measurement_retains_json_value(self) -> None:
        self.assertEqual(
            Measurement.supported_value(["spi0", "i2c-1"]).to_dict(),
            {"supported": True, "value": ["spi0", "i2c-1"], "reason": None},
        )


if __name__ == "__main__":
    unittest.main()
