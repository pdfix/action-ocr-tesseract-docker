# PDFix OCR with Tesseract 

Docker image for PDF text recogntion with OCR Tesseract and PDFix SDK

## System Requirements
- Docker Engine

## Run OCR using Command Line Interface

To run docker container as CLI you should share the folder with PDF to process using `-i` parameter. In this example it's current folder.

```
docker run -v $(pwd):/data/ -w /data/ pdfix/ocr-tesseract:latest --input scanned.pdf --output ocr.pdf --lang eng 
```
With PDFix License add these arguments. 
```
--name $LICENSE_NAME --key $LICENSE_KEY
```

First run will pull the docker image, which may take some time. Make your own image for more advanced use.

## Run OCR using REST API
Comming soon. Please contact us.

## License & libraries used
- PDFix SDK - https://pdfix.net/terms
- OCR Tesseract - https://github.com/tesseract-ocr/tesseract/

Trial version of the PDFix SDK may apply a watermark on the page and redact random parts of the PDF includeing the scanned image in background. Contact us to get an evaluation license.

## Help & Support
To obtain a PDFix SDK license or report an issue please contact us at support@pdfix.net.
For more information visit https://pdfix.net

