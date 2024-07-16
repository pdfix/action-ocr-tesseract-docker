# PDFix OCR with Tesseract 

Docker image based PDF text recogntion with OCR Tesseract and PDFix SDK

## System Requirements
- Docker Engine https://docs.docker.com/engine/install/

## Run using Command Line Interface

Usage:
```
./run.sh [OPTIONS]
```
```
Options:
  --input <input.pdf>     Path to the input PDF file
  --output <output.pdf>   Path the output PDF file
  --lang <lang>           OCR language
  --name <name>           License name
  --key <key>             License key
  --build                 Force rebuild of the Docker image
  --help                  Display this help message
```

## Run a Docker image 

### Build docker image
Build the docker image with the name `pdfix-tesseract-ocr`. You can choose another name if you want.

```
docker build -t pdfix-tesseract-ocr .
```

### Run docker container
To run docker container you should map directories with PDF documents to the container (`-v` parameter) and pass paths to input/output PDF document in the running container

Example: 

- Your input PDF is: `/home/pdfs_in/scanned.pdf`
- Your output PDF is: `/home/pdfs_out/ocred.pdf`

Path `/home/pdfs_in` is mapped to `/data_in` and `/home/pdfs_out` is mapped to `/data_out`

```
docker run --rm -v /home/pdfs_in:/data_in -v /home/pdfs_out:/data_out -it pdfix-tesseract-ocr --input /data/scanned.pdf --output /data/ocred.pdf --lang eng --name $LICENSE_NAME --key $LICENSE_KEY
```
Arguments `--input`, `--output`, `--lang`, `--name`, `--key` are the same as the CLI


## License & libraries used
- PDFix SDK - https://pdfix.net/terms
- OCR Tesseract - https://github.com/tesseract-ocr/tesseract/


## Help & Support
To obtain a PDFix SDK license or report an issue please contact us at support@pdfix.net.
For more information visit https://pdfix.net

