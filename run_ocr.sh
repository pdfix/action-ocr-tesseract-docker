#!/bin/bash
IMAGE_NAME="tesseract-ocr"
IMAGE_TAG="latest"
IMAGE="$IMAGE_NAME:$IMAGE_TAG"

# Initialize variables for arguments
FORCE_REBUILD=false
HOST_FOLDER=""
INPUT_PDF=""
OUTPUT_PDF=""

# Function to print help message
print_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --build                 Force rebuild of the Docker image."
    echo "  --folder <path>         Specify the host folder to be mounted."
    echo "  --input <input.pdf>     Specify the name of the input PDF file."
    echo "  --output <output.pdf>   Specify the name of the output PDF file."
    echo "  --help                  Display this help message and exit."
}

# Parse script arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --build) FORCE_REBUILD=true ;;
        --folder) HOST_FOLDER="$2"; shift ;;
        --input) INPUT_PDF="$2"; shift ;;
        --output) OUTPUT_PDF="$2"; shift ;;
        --help) print_help; exit 0 ;;
        *) echo "Unknown parameter passed: $1"; print_help; exit 1 ;;
    esac
    shift
done

# Check if required arguments are provided
if [ -z "$HOST_FOLDER" ] || [ -z "$INPUT_PDF" ] || [ -z "$OUTPUT_PDF" ]; then
    echo "Error: --folder, --input, and --output arguments are required."
    print_help
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null
then
    echo "Error: Docker is not installed on this system."
    exit 1
else
    echo "Docker is installed."
fi

# Function to build Dockerfile
build_dockerfile() {
    echo "Building Dockerfile..."
    if docker build -t $IMAGE .
    then
        echo "Dockerfile built successfully and image $IMAGE created."
    else
        echo "Error: Failed to build Dockerfile."
        exit 1
    fi
}

# Check if the Docker image is already present
if docker image inspect $IMAGE > /dev/null 2>&1
then
    if [ "$FORCE_REBUILD" = true ]; then
        echo "Force rebuild flag is set. Rebuilding Docker image $IMAGE..."
        build_dockerfile
    else
        echo "Docker image $IMAGE already exists."
    fi
else
    echo "Docker image $IMAGE does not exist. Building Dockerfile..."
    build_dockerfile
fi

# Run the Docker container with the specified arguments
docker run --rm -v "$HOST_FOLDER":/data -it $IMAGE -i /data/"$INPUT_PDF" -o /data/"$OUTPUT_PDF"
