#!/usr/bin/env python3
"""
Unit tests for stegano_tool.py
Run with: python test_stegano.py
"""

import sys
import os
import unittest
import struct
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import stegano_tool as st


def make_image(w=256, h=256, mode='RGB', seed=42):
    rng = np.random.default_rng(seed)
    if mode == 'RGB':
        arr = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
    else:
        arr = rng.integers(0, 256, (h, w), dtype=np.uint8)
    return Image.fromarray(arr, mode)


class TestUtils(unittest.TestCase):
    def test_bits_round_trip(self):
        data = b"Hello, World!"
        bits = st.bytes_to_bits(data)
        self.assertEqual(st.bits_to_bytes(bits), data)

    def test_payload_build_parse(self):
        msg = "Unit test payload 🔐"
        raw = st.build_payload(msg)
        result = st.parse_payload(raw)
        self.assertEqual(result, msg)

    def test_magic_check(self):
        with self.assertRaises(ValueError):
            st.parse_payload(b'\x00\x00\x00\x00\x00\x00\x00\x00')


class TestLSB(unittest.TestCase):
    def _roundtrip(self, mode, bits, message):
        img = make_image(mode=mode)
        stego = st.lsb_encode(img, message, bits=bits)
        decoded = st.lsb_decode(stego, bits=bits)
        self.assertEqual(decoded, message)

    def test_lsb1_rgb(self):
        self._roundtrip('RGB', 1, "LSB-1 RGB test")

    def test_lsb2_rgb(self):
        self._roundtrip('RGB', 2, "LSB-2 round trip!")

    def test_lsb4_rgb(self):
        self._roundtrip('RGB', 4, "LSB-4 embedding test")

    def test_lsb_grayscale(self):
        self._roundtrip('L', 1, "Grayscale LSB test")

    def test_lsb_unicode(self):
        self._roundtrip('RGB', 1, "Unicode: 你好 мир 🌍")

    def test_lsb_long_message(self):
        msg = "A" * 500
        img = make_image(512, 512)
        stego = st.lsb_encode(img, msg)
        self.assertEqual(st.lsb_decode(stego), msg)

    def test_lsb_overflow(self):
        tiny = make_image(8, 8)
        with self.assertRaises(ValueError):
            st.lsb_encode(tiny, "This message is way too long for an 8x8 image, trust me.")

    def test_lsb_no_data(self):
        img = make_image()
        with self.assertRaises(ValueError):
            st.lsb_decode(img)

    def test_lsb_with_password(self):
        if not st.AES_AVAILABLE:
            self.skipTest("pycryptodome not installed")
        img = make_image()
        msg = "Super secret AES message"
        stego = st.lsb_encode(img, msg, password="hunter2")
        decoded = st.lsb_decode(stego, password="hunter2")
        self.assertEqual(decoded, msg)


class TestDCT(unittest.TestCase):
    def setUp(self):
        if not st.DCT_AVAILABLE:
            self.skipTest("scipy not installed")

    def test_dct_roundtrip(self):
        img = make_image(512, 512)
        msg = "DCT steganography test"
        stego = st.dct_encode(img, msg, alpha=20.0)
        decoded = st.dct_decode(stego, alpha=20.0)
        self.assertEqual(decoded, msg)


class TestDWT(unittest.TestCase):
    def setUp(self):
        if not st.DWT_AVAILABLE:
            self.skipTest("PyWavelets not installed")

    def test_dwt_roundtrip(self):
        img = make_image(256, 256)
        msg = "DWT wavelet test message"
        stego = st.dwt_encode(img, msg, alpha=0.2)
        decoded = st.dwt_decode(stego, alpha=0.2)
        self.assertEqual(decoded, msg)


class TestMetrics(unittest.TestCase):
    def test_psnr_identical(self):
        img = make_image()
        psnr = st.compute_psnr(img, img)
        self.assertEqual(psnr, float('inf'))

    def test_psnr_lsb1_high(self):
        img = make_image()
        stego = st.lsb_encode(img, "psnr test")
        psnr = st.compute_psnr(img, stego)
        self.assertGreater(psnr, 40.0)  # LSB-1 should be nearly invisible

    def test_ssim_range(self):
        img = make_image()
        stego = st.lsb_encode(img, "ssim test")
        ssim = st.compute_ssim(img, stego)
        self.assertGreater(ssim, 0.95)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
