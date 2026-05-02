# 🔐 Advanced Image Steganography Tool

A production-ready Python tool for hiding secret messages inside images using **LSB**, **DCT**, and **DWT** steganography, with optional **AES-256 encryption**.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| **LSB** | 1, 2, or 4 bits-per-channel; lossless PNG/BMP |
| **DCT** | Frequency-domain embedding; JPEG-resilient |
| **DWT** | Haar-wavelet embedding; balanced capacity/robustness |
| **AES-256-CBC** | Optional password-based encryption before embedding |
| **Quality Metrics** | PSNR and SSIM computed after encoding |
| **Capacity Analyser** | Shows exact byte capacity for any image |
| **CLI** | Full command-line interface |
| **GUI** | Tkinter desktop GUI (`stegano_gui.py`) |
| **Tests** | 15+ unit tests covering all methods |

---

## 📦 Installation

### Prerequisites
- Python 3.9+
- pip

### Install dependencies
```bash
pip install -r source_code/requirements.txt
```

### Core only (LSB method, no encryption)
```bash
pip install Pillow numpy
```

### All features
```bash
pip install Pillow numpy pycryptodome scipy PyWavelets
```

---

## 🚀 Quick Start

### Using the GUI
```bash
python source_code/stegano_gui.py
```

### Using the CLI

#### Encode a message (LSB-1, no password)
```bash
python source_code/stegano_tool.py encode \
    -i cover.png \
    -m "My secret message" \
    -o stego.png
```

#### Encode with AES encryption
```bash
python source_code/stegano_tool.py encode \
    -i cover.png \
    -m "Encrypted secret" \
    -p "mypassword" \
    -o stego.png \
    --metrics
```

#### Encode using DCT method
```bash
python source_code/stegano_tool.py encode \
    -i cover.png \
    -m "DCT embedded data" \
    --method dct \
    --alpha 20.0 \
    -o stego_dct.png
```

#### Decode (LSB)
```bash
python source_code/stegano_tool.py decode \
    -i stego.png \
    -p "mypassword"
```

#### Decode (DCT)
```bash
python source_code/stegano_tool.py decode \
    -i stego_dct.png \
    --method dct \
    --alpha 20.0
```

#### Check image capacity
```bash
python source_code/stegano_tool.py capacity -i cover.png
```

---

## 📐 Method Comparison

| Method | Capacity | Imperceptibility | JPEG-Resilient | Speed |
|--------|----------|-----------------|----------------|-------|
| **LSB-1** | High | Excellent (PSNR > 51 dB) | ❌ | Fast |
| **LSB-2** | Very High | Good (PSNR ≈ 44 dB) | ❌ | Fast |
| **LSB-4** | Max | Visible artefacts | ❌ | Fast |
| **DCT** | Medium | Very Good | ✅ | Medium |
| **DWT** | Medium | Good | Partial | Medium |

**Recommendation:** Use LSB-1 with AES for maximum security in lossless images (PNG/BMP). Use DCT for JPEG workflows where images may be re-saved.

---

## 🔒 Security Notes

- AES-256-CBC encryption is applied **before** embedding. An attacker who discovers hidden data cannot read it without the password.
- Without encryption, a steganalysis tool may detect the presence of hidden data in LSB-modified images.
- DCT embedding is more resistant to statistical steganalysis than raw LSB.
- Always use a strong, unique password when `-p` / `--password` is specified.

---

## 📋 CLI Reference

```
usage: stegano_tool.py {encode,decode,capacity} [options]

Subcommands:
  encode      Hide a message in an image
  decode      Extract a message from a stego image
  capacity    Show data capacity of a cover image

Encode options:
  -i PATH          Cover image (PNG, BMP, TIFF recommended)
  -m MESSAGE       The secret message text
  -o PATH          Output stego image path
  -p PASSWORD      AES-256 encryption password
  --method         lsb | dct | dwt  (default: lsb)
  --lsb-bits       1, 2, or 4  (default: 1)
  --alpha FLOAT    Embedding strength for DCT/DWT (default: 15.0)
  --metrics        Print PSNR and SSIM after encoding

Decode options:
  -i PATH          Stego image path
  -p PASSWORD      AES-256 decryption password (if used during encode)
  --method         lsb | dct | dwt  (default: lsb)
  --lsb-bits       1, 2, or 4  (default: 1)
  --alpha FLOAT    Same value used during encoding
```

---

## 🧪 Running Tests

```bash
python source_code/test_stegano.py
```

---

## 🏗️ Building the Executable

```bash
pip install pyinstaller
python build.py
```

This generates `stegano_tool_v1.0.zip` containing the executable, source code, README, and LICENSE.

To skip PyInstaller and only re-package:
```bash
python build.py --zip
```

---

## 📁 Project Structure

```
stegano_tool_v1.0.zip
├── source_code/
│   ├── stegano_tool.py      # Core CLI + steganography engine
│   ├── stegano_gui.py       # Tkinter GUI frontend
│   ├── test_stegano.py      # Unit tests
│   └── requirements.txt     # Python dependencies
├── stegano_tool[.exe]       # Standalone executable (Windows/Linux)
├── README.md                # This file
└── LICENSE                  # MIT License
```

---

## 🛠️ Supported Image Formats

| Format | Encode | Decode | Notes |
|--------|--------|--------|-------|
| PNG | ✅ | ✅ | **Recommended** — lossless |
| BMP | ✅ | ✅ | Lossless, large file size |
| TIFF | ✅ | ✅ | Lossless |
| JPEG/JPG | ⚠️ | ⚠️ | Lossy — use DCT method only |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for full text.
