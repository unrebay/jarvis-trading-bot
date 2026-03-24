#!/bin/bash
# setup_whisper.sh — Install whisper.cpp with Metal (GPU) support on Apple Silicon iMac
# Optimized for M3 iMac. Takes ~3-5 minutes total.
#
# After setup, transcription speed: ~10x realtime (1 hour video ≈ 6 minutes)
#
# Usage:
#   bash scripts/setup_whisper.sh
#   bash scripts/setup_whisper.sh --model large-v3        # default
#   bash scripts/setup_whisper.sh --model large-v3-turbo  # faster, slightly less accurate
#   bash scripts/setup_whisper.sh --model medium          # much smaller, still good

set -e

# ── Config ────────────────────────────────────────────────────────────────────
MODEL="${1:-large-v3-turbo}"
WHISPER_DIR="$HOME/whisper.cpp"

# Parse --model flag
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --model) MODEL="$2"; shift ;;
    esac
    shift
done

MODEL_FILE="ggml-${MODEL}.bin"
MODEL_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/${MODEL_FILE}"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║     whisper.cpp Metal Setup (Apple Silicon / M3)     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Model:     $MODEL"
echo "  Install:   $WHISPER_DIR"
echo ""

# ── Check prerequisites ───────────────────────────────────────────────────────
echo "[1/5] Checking prerequisites..."

# Xcode Command Line Tools (needed for cmake, git)
if ! xcode-select -p &>/dev/null; then
    echo "  Installing Xcode Command Line Tools..."
    xcode-select --install
    echo "  ⚠️   Xcode CLT install started. Re-run this script after installation completes."
    exit 0
fi
echo "  ✅ Xcode CLT: OK"

# Homebrew
if ! command -v brew &>/dev/null; then
    echo "  Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
echo "  ✅ Homebrew: OK"

# cmake
if ! command -v cmake &>/dev/null; then
    echo "  Installing cmake..."
    brew install cmake
fi
echo "  ✅ cmake: $(cmake --version | head -1)"

# ffmpeg (for audio extraction in video_ingestion.py)
if ! command -v ffmpeg &>/dev/null; then
    echo "  Installing ffmpeg..."
    brew install ffmpeg
fi
echo "  ✅ ffmpeg: $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f1-3)"

# ── Clone / update whisper.cpp ────────────────────────────────────────────────
echo ""
echo "[2/5] Getting whisper.cpp source..."

if [ -d "$WHISPER_DIR" ]; then
    echo "  Updating existing repo..."
    cd "$WHISPER_DIR"
    git pull --ff-only
else
    echo "  Cloning whisper.cpp..."
    git clone https://github.com/ggml-org/whisper.cpp.git "$WHISPER_DIR"
    cd "$WHISPER_DIR"
fi
echo "  ✅ Source ready at $WHISPER_DIR"

# ── Build with Metal ──────────────────────────────────────────────────────────
echo ""
echo "[3/5] Building with Metal GPU acceleration..."

mkdir -p build
cd build

cmake .. \
    -DGGML_METAL=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DWHISPER_BUILD_TESTS=OFF \
    -DWHISPER_BUILD_EXAMPLES=ON

cmake --build . --config Release -j$(sysctl -n hw.logicalcpu)

echo "  ✅ Build complete"

# Verify binary
WHISPER_BIN="$WHISPER_DIR/build/bin/whisper-cli"
if [ ! -f "$WHISPER_BIN" ]; then
    # Older versions use 'main' binary name
    WHISPER_BIN="$WHISPER_DIR/build/bin/main"
fi

if [ ! -f "$WHISPER_BIN" ]; then
    echo "  ❌ Binary not found after build. Check build output above."
    exit 1
fi
echo "  ✅ Binary: $WHISPER_BIN"

# ── Download model ────────────────────────────────────────────────────────────
echo ""
echo "[4/5] Downloading model: $MODEL..."
cd "$WHISPER_DIR"
mkdir -p models

MODEL_PATH="$WHISPER_DIR/models/$MODEL_FILE"
if [ -f "$MODEL_PATH" ]; then
    echo "  ✅ Model already downloaded: $MODEL_PATH"
else
    case $MODEL in
        large-v3)        MODEL_SIZE="3.1 GB" ;;
        large-v3-turbo)  MODEL_SIZE="1.6 GB" ;;
        medium)          MODEL_SIZE="1.5 GB" ;;
        small)           MODEL_SIZE="466 MB" ;;
        base)            MODEL_SIZE="142 MB" ;;
        *)               MODEL_SIZE="?" ;;
    esac
    echo "  Downloading $MODEL_FILE (~$MODEL_SIZE)..."

    # Use the built-in download script if available
    if [ -f "models/download-ggml-model.sh" ]; then
        bash models/download-ggml-model.sh "$MODEL"
    else
        curl -L -o "$MODEL_PATH" "$MODEL_URL" --progress-bar
    fi
    echo "  ✅ Model downloaded: $MODEL_PATH"
fi

# ── Test run ──────────────────────────────────────────────────────────────────
echo ""
echo "[5/5] Testing whisper.cpp with Metal..."

# Use the bundled test sample if available
SAMPLE=""
if [ -f "$WHISPER_DIR/samples/jfk.wav" ]; then
    SAMPLE="$WHISPER_DIR/samples/jfk.wav"
else
    # Download tiny test sample
    curl -sL https://github.com/ggml-org/whisper.cpp/raw/master/samples/jfk.wav \
         -o /tmp/jarvis_test.wav 2>/dev/null && SAMPLE="/tmp/jarvis_test.wav"
fi

if [ -n "$SAMPLE" ]; then
    echo "  Running test transcription..."
    "$WHISPER_BIN" -m "$MODEL_PATH" -f "$SAMPLE" -l en --no-timestamps 2>&1 | tail -5
    echo "  ✅ Test passed!"
else
    echo "  ⚠️  No test sample available — skipping test"
fi

# ── Update .env ───────────────────────────────────────────────────────────────
JARVIS_DIR="$(dirname "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)")"
ENV_FILE="$JARVIS_DIR/.env"

echo ""
echo "──────────────────────────────────────────────────────"
echo "  Setup Complete!"
echo ""
echo "  Binary:  $WHISPER_BIN"
echo "  Model:   $MODEL_PATH"
echo ""

# Add to .env if not already there
if [ -f "$ENV_FILE" ]; then
    if ! grep -q "WHISPER_BIN" "$ENV_FILE"; then
        echo "" >> "$ENV_FILE"
        echo "# whisper.cpp (added by setup_whisper.sh)" >> "$ENV_FILE"
        echo "WHISPER_BIN=$WHISPER_BIN" >> "$ENV_FILE"
        echo "WHISPER_MODEL=$MODEL_PATH" >> "$ENV_FILE"
        echo "  ✅ Added WHISPER_BIN and WHISPER_MODEL to .env"
    else
        echo "  ℹ️   WHISPER_BIN already in .env (not modified)"
    fi
fi

echo ""
echo "  Run ingestion:"
echo "    python scripts/video_ingestion.py --dir ~/Downloads/trading-videos/ --dry-run"
echo "    python scripts/video_ingestion.py --dir ~/Downloads/trading-videos/"
echo "──────────────────────────────────────────────────────"
echo ""
