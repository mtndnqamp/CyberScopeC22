import unittest

from cyberscope.integrity.hashing import canonical_json, sha256_digest


class HashingTests(unittest.TestCase):
    def test_hash_is_deterministic_for_nested_key_order(self) -> None:
        left = {"software": {"kernel": "6", "os": "Linux"}, "usb": ["b", "a"]}
        right = {"usb": ["b", "a"], "software": {"os": "Linux", "kernel": "6"}}
        self.assertEqual(sha256_digest(left), sha256_digest(right))

    def test_canonical_json_uses_compact_sorted_utf8(self) -> None:
        self.assertEqual(canonical_json({"z": "π", "a": 1}), '{"a":1,"z":"π"}')

    def test_non_finite_float_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            canonical_json({"voltage": float("nan")})

    def test_non_json_value_is_rejected_with_path(self) -> None:
        with self.assertRaisesRegex(TypeError, r"software\.bad"):
            canonical_json({"software": {"bad": object()}})


if __name__ == "__main__":
    unittest.main()
