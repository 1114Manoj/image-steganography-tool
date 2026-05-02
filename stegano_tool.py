#!/usr/bin/env python3
"""
Advanced Image Steganography Tool
Supports LSB, DCT, and DWT-based steganography with optional AES encryption.
"""

import argparse
import sys
import os
import struct
import hashlib
import numpy as np
from PIL import Image

# Optional imports for advanced features
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    AES_AVAILABLE = True
except ImportError:
    AES_AVAILABLE = False

try:
    import pywt
    DWT_AVAILABLE = True
except ImportError:
    DWT_AVAILABLE = False

try:
    from scipy.fftpack import dct, idct
    DCT_AVAILABLE = True
except ImportError:
    DCT_AVAILABLE = False


# ─────────────────────────────────────────────
#  UTILITY FUNCTIONS
# ─────────────────────────────────────────────

MAGIC = b'\xDE\xAD\xBE\xEF'   # 4-byte marker written before every payload

def text_to_bits(text: str) -> list:
    data = text.encode('utf-8')
    return bytes_to_bits(data)

def bytes_to_bits(data: bytes) -> list:
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits

def bits_to_bytes(bits: list) -> bytes:
    result = bytearray()
    for i in range(0, len(bits), 8):
        byte_bits = bits[i:i+8]
        if len(byte_bits) < 8:
            break
        byte = 0
        for bit in byte_bits:
            byte = (byte << 1) | bit
        result.append(byte)
    return bytes(result)

def build_payload(message: str, password: str = None) -> bytes:
    """Build payload: MAGIC + 4-byte length + data (optionally AES-encrypted)."""
    data = message.encode('utf-8')
    if password and AES_AVAILABLE:
        data = aes_encrypt(data, password)
    payload = MAGIC + struct.pack('>I', len(data)) + data
    return payload

def parse_payload(raw: bytes, password: str = None) -> str:
    """Validate magic, strip header, decrypt if needed, return string."""
    if raw[:4] != MAGIC:
        raise ValueError("Magic header not found — image may not contain hidden data or is corrupted.")
    length = struct.unpack('>I', raw[4:8])[0]
    data = raw[8:8 + length]
    if password and AES_AVAILABLE:
        data = aes_decrypt(data, password)
    return data.decode('utf-8')

def aes_encrypt(data: bytes, password: str) -> bytes:
    key = hashlib.sha256(password.encode()).digest()
    cipher = AES.new(key, AES.MODE_CBC)
    ct = cipher.encrypt(pad(data, AES.block_size))
    return cipher.iv + ct

def aes_decrypt(data: bytes, password: str) -> bytes:
    key = hashlib.sha256(password.encode()).digest()
    iv, ct = data[:16], data[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    return unpad(cipher.decrypt(ct), AES.block_size)


# ─────────────────────────────────────────────
#  LSB STEGANOGRAPHY
# ─────────────────────────────────────────────

def lsb_capacity(img: Image.Image) -> int:
    arr = np.array(img)
    return arr.size  # 1 bit per channel byte → n_bytes = arr.size // 8

def lsb_encode(img: Image.Image, message: str, password: str = None, bits: int = 1) -> Image.Image:
    if bits not in (1, 2, 4):
        raise ValueError("bits must be 1, 2, or 4")
    payload = build_payload(message, password)
    bit_list = bytes_to_bits(payload)
    arr = np.array(img, dtype=np.uint8).flatten()
    capacity_bits = len(arr) * bits
    if len(bit_list) > capacity_bits:
        raise ValueError(f"Message too large: needs {len(bit_list)} bits, image holds {capacity_bits} bits")
    mask = 0xFF ^ ((1 << bits) - 1)
    for i, chunk_start in enumerate(range(0, len(bit_list), bits)):
        chunk = bit_list[chunk_start:chunk_start + bits]
        while len(chunk) < bits:
            chunk.append(0)
        value = 0
        for b in chunk:
            value = (value << 1) | b
        arr[i] = (arr[i] & mask) | value
    result = arr.reshape(np.array(img).shape)
    return Image.fromarray(result.astype(np.uint8), img.mode)

def lsb_decode(img: Image.Image, password: str = None, bits: int = 1) -> str:
    arr = np.array(img, dtype=np.uint8).flatten()
    mask = (1 << bits) - 1
    raw_bits = []
    for val in arr:
        extracted = val & mask
        for shift in range(bits - 1, -1, -1):
            raw_bits.append((extracted >> shift) & 1)
    # Read header (magic + length = 8 bytes = 64 bits)
    header_bits = raw_bits[:64]
    header_bytes = bits_to_bytes(header_bits)
    if header_bytes[:4] != MAGIC:
        raise ValueError("No hidden data found in this image.")
    total_length = struct.unpack('>I', header_bytes[4:8])[0]
    total_bits = (8 + total_length) * 8
    payload_bytes = bits_to_bytes(raw_bits[:total_bits])
    return parse_payload(payload_bytes, password)


# ─────────────────────────────────────────────
#  DCT STEGANOGRAPHY (JPEG-style, grayscale Y)
# ─────────────────────────────────────────────

def _dct2(block):
    return dct(dct(block.T, norm='ortho').T, norm='ortho')

def _idct2(block):
    return idct(idct(block.T, norm='ortho').T, norm='ortho')

def _get_work_channel(img: Image.Image) -> np.ndarray:
    """Return the float64 channel we embed into (R for RGB, the array itself for L)."""
    if img.mode == 'RGB':
        return np.array(img)[:, :, 0].astype(np.float64)
    return np.array(img.convert('L')).astype(np.float64)

def _put_work_channel(original_img: Image.Image, modified_channel: np.ndarray) -> Image.Image:
    """Write the modified channel back into a copy of original_img."""
    clipped = np.clip(modified_channel, 0, 255).astype(np.uint8)
    if original_img.mode == 'RGB':
        rgb = np.array(original_img).copy()
        rgb[:clipped.shape[0], :clipped.shape[1], 0] = clipped
        return Image.fromarray(rgb, 'RGB')
    return Image.fromarray(clipped, 'L')

def dct_encode(img: Image.Image, message: str, password: str = None, alpha: float = 15.0) -> Image.Image:
    """
    Embed bits by forcing the mid-frequency DCT coefficient d[4][5] to be
    positive (bit=1) or negative (bit=0), with a minimum magnitude of alpha.
    """
    if not DCT_AVAILABLE:
        raise RuntimeError("scipy is required for DCT steganography. Install it with: pip install scipy")
    payload = build_payload(message, password)
    bit_list = bytes_to_bits(payload)
    gray = _get_work_channel(img)
    h, w = gray.shape
    idx = 0
    for row in range(0, h - 7, 8):
        for col in range(0, w - 7, 8):
            if idx >= len(bit_list):
                break
            block = gray[row:row + 8, col:col + 8]
            dct_block = _dct2(block)
            magnitude = max(abs(dct_block[4][5]), alpha)
            dct_block[4][5] = magnitude if bit_list[idx] == 1 else -magnitude
            gray[row:row + 8, col:col + 8] = _idct2(dct_block)
            idx += 1
    return _put_work_channel(img, gray)

def dct_decode(img: Image.Image, password: str = None, alpha: float = 15.0) -> str:
    """Decode: positive coefficient → 1, negative → 0."""
    if not DCT_AVAILABLE:
        raise RuntimeError("scipy is required for DCT steganography.")
    gray = _get_work_channel(img)
    h, w = gray.shape
    bits = []
    for row in range(0, h - 7, 8):
        for col in range(0, w - 7, 8):
            block = gray[row:row + 8, col:col + 8]
            dct_block = _dct2(block)
            bits.append(1 if dct_block[4][5] >= 0 else 0)

    if len(bits) < 64:
        raise ValueError("Image too small for DCT decode.")
    header = bits_to_bytes(bits[:64])
    if header[:4] != MAGIC:
        raise ValueError("No hidden data found via DCT method.")
    total_len = struct.unpack('>I', header[4:8])[0]
    needed = (8 + total_len) * 8
    if len(bits) < needed:
        raise ValueError("Stego image does not contain enough DCT blocks for the payload.")
    payload = bits_to_bytes(bits[:needed])
    return parse_payload(payload, password)


# ─────────────────────────────────────────────
#  DWT STEGANOGRAPHY
# ─────────────────────────────────────────────

def dwt_encode(img: Image.Image, message: str, password: str = None, alpha: float = 0.1) -> Image.Image:
    if not DWT_AVAILABLE:
        raise RuntimeError("PyWavelets is required for DWT steganography. Install: pip install PyWavelets")
    payload = build_payload(message, password)
    bit_list = bytes_to_bits(payload)
    gray = np.array(img.convert('L'), dtype=np.float64)
    coeffs = pywt.dwt2(gray, 'haar')
    cA, (cH, cV, cD) = coeffs
    flat = cH.flatten().copy()
    if len(bit_list) > len(flat):
        raise ValueError(f"Message too large for DWT. Capacity: {len(flat)//8} bytes.")
    for i, bit in enumerate(bit_list):
        flat[i] = abs(flat[i]) + alpha if bit == 1 else abs(flat[i])
        if flat[i - 1] < 0:
            flat[i] = -flat[i]
    cH_new = flat.reshape(cH.shape)
    reconstructed = pywt.idwt2((cA, (cH_new, cV, cD)), 'haar')
    result = np.clip(reconstructed, 0, 255).astype(np.uint8)
    if img.mode == 'RGB':
        rgb = np.array(img)
        rgb[:, :, 0] = result[:rgb.shape[0], :rgb.shape[1]]
        return Image.fromarray(rgb, 'RGB')
    return Image.fromarray(result[:gray.shape[0], :gray.shape[1]], 'L')

def dwt_decode(img: Image.Image, password: str = None, alpha: float = 0.1) -> str:
    if not DWT_AVAILABLE:
        raise RuntimeError("PyWavelets is required for DWT steganography.")
    gray = np.array(img.convert('L'), dtype=np.float64)
    coeffs = pywt.dwt2(gray, 'haar')
    _, (cH, _, _) = coeffs
    flat = cH.flatten()
    bits = [1 if abs(v) > alpha / 2 else 0 for v in flat]
    # Read just enough to get length, then full payload
    if len(bits) < 64:
        raise ValueError("Image too small for DWT decode.")
    header = bits_to_bytes(bits[:64])
    if header[:4] != MAGIC:
        raise ValueError("No hidden data found via DWT method.")
    total_len = struct.unpack('>I', header[4:8])[0]
    needed = (8 + total_len) * 8
    payload = bits_to_bytes(bits[:needed])
    return parse_payload(payload, password)


# ─────────────────────────────────────────────
#  QUALITY METRICS
# ─────────────────────────────────────────────

def compute_psnr(original: Image.Image, modified: Image.Image) -> float:
    orig = np.array(original.convert('RGB'), dtype=np.float64)
    mod  = np.array(modified.convert('RGB'), dtype=np.float64)
    mse = np.mean((orig - mod) ** 2)
    if mse == 0:
        return float('inf')
    return 10 * np.log10((255.0 ** 2) / mse)

def compute_ssim(original: Image.Image, modified: Image.Image) -> float:
    orig = np.array(original.convert('L'), dtype=np.float64)
    mod  = np.array(modified.convert('L'), dtype=np.float64)
    c1, c2 = 6.5025, 58.5225
    mu1, mu2 = orig.mean(), mod.mean()
    sigma1_sq = orig.var()
    sigma2_sq = mod.var()
    sigma12 = np.mean((orig - mu1) * (mod - mu2))
    num = (2*mu1*mu2 + c1) * (2*sigma12 + c2)
    den = (mu1**2 + mu2**2 + c1) * (sigma1_sq + sigma2_sq + c2)
    return num / den


# ─────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────

def encode_cmd(args):
    img = Image.open(args.input)
    original = img.copy()
    method = args.method.lower()
    print(f"[+] Encoding using {method.upper()} method...")

    if method == 'lsb':
        out = lsb_encode(img, args.message, args.password, bits=args.lsb_bits)
    elif method == 'dct':
        out = dct_encode(img, args.message, args.password, alpha=args.alpha)
    elif method == 'dwt':
        out = dwt_encode(img, args.message, args.password, alpha=args.alpha)
    else:
        print(f"[-] Unknown method: {method}")
        sys.exit(1)

    out_path = args.output or f"stego_{os.path.basename(args.input)}"
    out.save(out_path)
    print(f"[+] Stego image saved: {out_path}")

    if args.metrics:
        psnr = compute_psnr(original, out)
        ssim = compute_ssim(original, out)
        print(f"[+] PSNR: {psnr:.2f} dB  |  SSIM: {ssim:.6f}")

def decode_cmd(args):
    img = Image.open(args.input)
    method = args.method.lower()
    print(f"[+] Decoding using {method.upper()} method...")

    if method == 'lsb':
        msg = lsb_decode(img, args.password, bits=args.lsb_bits)
    elif method == 'dct':
        msg = dct_decode(img, args.password, alpha=args.alpha)
    elif method == 'dwt':
        msg = dwt_decode(img, args.password, alpha=args.alpha)
    else:
        print(f"[-] Unknown method: {method}")
        sys.exit(1)

    print(f"[+] Hidden message:\n{msg}")

def capacity_cmd(args):
    img = Image.open(args.input)
    arr = np.array(img)
    lsb1 = arr.size // 8
    lsb2 = arr.size // 4
    lsb4 = arr.size // 2
    print(f"[+] Image: {img.size[0]}x{img.size[1]} {img.mode}  ({arr.size} channel bytes)")
    print(f"    LSB-1 capacity : {lsb1} bytes  ({lsb1/1024:.1f} KB)")
    print(f"    LSB-2 capacity : {lsb2} bytes  ({lsb2/1024:.1f} KB)")
    print(f"    LSB-4 capacity : {lsb4} bytes  ({lsb4/1024:.1f} KB)")
    h, w = arr.shape[:2]
    dct_blocks = (h // 8) * (w // 8)
    print(f"    DCT/DWT approx : {dct_blocks // 8} bytes  ({dct_blocks//8/1024:.2f} KB)")

def main():
    parser = argparse.ArgumentParser(
        description="Advanced Image Steganography Tool — LSB, DCT, DWT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Encode with LSB-1
  python stegano_tool.py encode -i cover.png -m "Secret!" -o stego.png

  # Encode with LSB-2 and AES encryption
  python stegano_tool.py encode -i cover.png -m "Secret!" -p mypassword --lsb-bits 2

  # Encode with DCT method
  python stegano_tool.py encode -i cover.png -m "Secret!" --method dct --alpha 20

  # Decode
  python stegano_tool.py decode -i stego.png -p mypassword

  # Check image capacity
  python stegano_tool.py capacity -i cover.png
        """
    )
    sub = parser.add_subparsers(dest='command')

    # encode
    enc = sub.add_parser('encode', help='Hide a message in an image')
    enc.add_argument('-i', '--input',   required=True, help='Cover image path')
    enc.add_argument('-m', '--message', required=True, help='Secret message')
    enc.add_argument('-o', '--output',  help='Output stego image path')
    enc.add_argument('-p', '--password', help='AES encryption password')
    enc.add_argument('--method', default='lsb', choices=['lsb','dct','dwt'], help='Steganography method')
    enc.add_argument('--lsb-bits', type=int, default=1, choices=[1,2,4], help='Bits per channel for LSB (default: 1)')
    enc.add_argument('--alpha', type=float, default=15.0, help='Embedding strength for DCT/DWT (default: 15.0)')
    enc.add_argument('--metrics', action='store_true', help='Print PSNR/SSIM quality metrics')

    # decode
    dec = sub.add_parser('decode', help='Extract a message from a stego image')
    dec.add_argument('-i', '--input',   required=True, help='Stego image path')
    dec.add_argument('-p', '--password', help='AES decryption password')
    dec.add_argument('--method', default='lsb', choices=['lsb','dct','dwt'])
    dec.add_argument('--lsb-bits', type=int, default=1, choices=[1,2,4])
    dec.add_argument('--alpha', type=float, default=15.0)

    # capacity
    cap = sub.add_parser('capacity', help='Show how much data a cover image can hold')
    cap.add_argument('-i', '--input', required=True, help='Image path')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == 'encode':
            encode_cmd(args)
        elif args.command == 'decode':
            decode_cmd(args)
        elif args.command == 'capacity':
            capacity_cmd(args)
    except Exception as e:
        print(f"[-] Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
