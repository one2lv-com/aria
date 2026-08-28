#!/bin/bash

# ARIA Agent APK Build Script
# This script builds the Android APK using Buildozer

set -e

echo "=================================="
echo "ARIA Agent - APK Builder"
echo "=================================="
echo ""

# Check if running in a build environment
if [ ! -f "buildozer.spec" ]; then
    echo "ERROR: buildozer.spec not found!"
    echo "Please run this script from the agent directory."
    exit 1
fi

# Check for buildozer
if ! command -v buildozer &> /dev/null; then
    echo "Buildozer not found. Installing..."

    # Install dependencies
    echo "Installing system dependencies..."
    sudo apt-get update
    sudo apt-get install -y \
        python3-pip \
        build-essential \
        git \
        ffmpeg \
        libsdl2-dev \
        libsdl2-image-dev \
        libsdl2-mixer-dev \
        libsdl2-ttf-dev \
        libportmidi-dev \
        libswscale-dev \
        libavformat-dev \
        libavcodec-dev \
        zlib1g-dev \
        libgstreamer1.0-dev \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        openjdk-11-jdk \
        unzip \
        zip

    # Install buildozer
    echo "Installing buildozer..."
    pip3 install --upgrade buildozer
    pip3 install --upgrade cython
fi

# Check for Android SDK/NDK (buildozer will download if missing)
echo ""
echo "Preparing build environment..."
echo "Note: First build may take 30-60 minutes as it downloads Android SDK/NDK"
echo ""

# Clean previous builds (optional)
read -p "Clean previous builds? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleaning build directories..."
    rm -rf .buildozer
    rm -rf bin
fi

# Build the APK
echo ""
echo "Building APK..."
echo "=================================="

buildozer -v android debug

# Check if build succeeded
if [ -f "bin/*.apk" ]; then
    echo ""
    echo "=================================="
    echo "✓ Build completed successfully!"
    echo "=================================="
    echo ""
    echo "APK location: bin/*.apk"
    echo ""
    echo "To install on device:"
    echo "  adb install bin/ariaagent-1.0.0-arm64-v8a-debug.apk"
    echo ""
    echo "Or transfer the APK to your device and install manually."
else
    echo ""
    echo "=================================="
    echo "✗ Build failed!"
    echo "=================================="
    echo "Check the output above for errors."
    exit 1
fi
