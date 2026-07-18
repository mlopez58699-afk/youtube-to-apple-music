#!/bin/bash

set -e

APP_NAME="YouTube to Apple Music"
APP_COMMAND="ytmusic"
APP_DIR="$HOME/.youtube-to-apple-music"
BIN_DIR="$HOME/.local/bin"
VERSION=$(cat VERSION)

print_header() {
    echo
    echo "=========================================="
    echo " $APP_NAME Installer"
    echo " Version $VERSION"
    echo "=========================================="
    echo
}

check_command() {
    command -v "$1" >/dev/null 2>&1
}

status_ok() {
    echo "✔ $1"
}

status_info() {
    echo "➜ $1"
}

status_fail() {
    echo "✖ $1"
}

print_header

#########################################
# System Checks
#########################################

if [[ "$(uname)" != "Darwin" ]]; then
    status_fail "This installer only supports macOS."
    exit 1
fi

status_ok "macOS detected"


#########################################
# Check Homebrew
#########################################

status_info "Checking Homebrew..."

if check_command brew; then
    status_ok "Homebrew installed"
else
    status_info "Homebrew not found. Installing..."

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    status_ok "Homebrew installed"
fi


#########################################
# Check Python
#########################################

status_info "Checking Python..."

if check_command python3; then
    PYTHON_VERSION=$(python3 --version)
    status_ok "$PYTHON_VERSION"
else
    status_info "Python not found. Installing..."

    brew install python

    status_ok "Python installed"
fi

#########################################
# Check yt-dlp
#########################################

status_info "Checking yt-dlp..."

if check_command yt-dlp; then
    YTDLP_VERSION=$(yt-dlp --version)
    status_ok "yt-dlp $YTDLP_VERSION"
else
    status_info "yt-dlp not found. Installing..."

    brew install yt-dlp

    status_ok "yt-dlp installed"
fi


#########################################
# Check ffmpeg
#########################################

status_info "Checking ffmpeg..."

if check_command ffmpeg; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n 1)
    status_ok "$FFMPEG_VERSION"
else
    status_info "ffmpeg not found. Installing..."

    brew install ffmpeg

    status_ok "ffmpeg installed"
fi


#########################################
# Check Deno
#########################################

status_info "Checking Deno..."

if check_command deno; then
    DENO_VERSION=$(deno --version | head -n 1)
    status_ok "$DENO_VERSION"
else
    status_info "Deno not found. Installing..."

    brew install deno

    status_ok "Deno installed"
fi
