FROM python:3.11-slim

WORKDIR /app

# Compiler and Python development headers are required to build the C++/pybind11 module.
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies.
COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt \
    && pip install --no-cache-dir pybind11

# Copy application source and local databases.
COPY backend /app/backend
COPY database /app/database

# Build the C++ classifier as a Python extension directly inside backend/.
# This placement is intentional: "import tpu_classifier" must resolve to the
# compiled extension rather than the source directory namespace package.
WORKDIR /app/backend
RUN c++ -O3 -Wall -shared -std=c++17 -fPIC \
    $(python -m pybind11 --includes) \
    tpu_classifier/tpu_classifier/classifier.cpp \
    -o tpu_classifier$(python3-config --extension-suffix)

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
