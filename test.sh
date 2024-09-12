#!/bin/bash

# local docker test 
info() { echo -e "\033[1;35m$1\033[0m"; }

# init
pushd "$(dirname $0)" > /dev/null

docker build --rm -t ocr-tesseract .

tmp_dir=".test"

if [ -d "$(pwd)/$tmp_dir" ]; then
  rm -rf $(pwd)/$tmp_dir
fi
mkdir -p $(pwd)/$tmp_dir

info "just list files in cwd"
docker run -it  -v $(pwd):/data -w /data --entrypoint ls ocr-tesseract

info "extract config"
docker run -it  -v $(pwd):/data -w /data ocr-tesseract config -o $tmp_dir/config.json
if [ ! -f "$(pwd)/$tmp_dir/config.json" ]; then
  echo "config.json not saved"
  exit 1
fi

info "run ocr"
docker run -it  -v $(pwd):/data -w /data ocr-tesseract ocr -i example/changement_climatique.pdf -o $tmp_dir/changement_climatique_ocr.pdf
if [ ! -f "$(pwd)/$tmp_dir/changement_climatique_ocr.pdf" ]; then
  echo "ocr failed on example/changement_climatique_ocr.pdf"
  exit 1
fi

popd

echo "SUCCESS"
