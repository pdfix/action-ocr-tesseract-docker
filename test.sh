#!/bin/bash

# local docker test 

GREEN='\033[0;32m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print info messages
info() {
    echo -e "${PURPLE}$1${NC}"
}

# Function to print success messages
success() {
    echo -e "${GREEN}$1${NC}"
}

# Function to print error messages
error() {
    echo -e "${RED}ERROR: $1${NC}"
}

# init
pushd "$(dirname $0)" > /dev/null

EXIT_STATUS=0

img="ocr-tesseract:test"
pltfm="--platform linux/amd64"

info "Building docker image..."
docker build --rm -t $img . 

tmp_dir=".test"

if [ -d "$(pwd)/$tmp_dir" ]; then
  rm -rf $(pwd)/$tmp_dir
fi
mkdir -p $(pwd)/$tmp_dir

info "List files in cwd"
docker run -v $(pwd):/data -w /data --entrypoint ls $img

info "Test #01: Show help"
docker run $pltfm -v $(pwd):/data -w /data $img --help > /dev/null
if [ $? -eq 0 ]; then
    success "passed"
else
    error "Failed to run \"--help\" command"
    EXIT_STATUS=1
fi

info "Test #02: Extract config"
docker run -v $(pwd):/data -w /data $img config -o $tmp_dir/config.json > /dev/null
if [ -f "$(pwd)/$tmp_dir/config.json" ]; then
  success "passed"
else
  error "config.json not saved"
  EXIT_STATUS=1
fi

info "Test #03: Run ocr-tesseract" 
docker run -v $(pwd):/data -w /data $img ocr -i example/changement_climatique.pdf -o $tmp_dir/changement_climatique_ocr.pdf > /dev/null
if [ -f "$(pwd)/$tmp_dir/changement_climatique_ocr.pdf" ]; then
  success "passed"
else
  error "ocr-tesseract failed on example/changement_climatique.pdf"
  EXIT_STATUS=1
fi

popd > /dev/null

if [ $EXIT_STATUS -eq 1 ]; then
  error "One or more tests failed."
  exit 1
else
  success "All tests passed."
  exit 0
fi
