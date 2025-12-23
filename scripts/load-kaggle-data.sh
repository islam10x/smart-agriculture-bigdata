#!/bin/bash
set -e

echo "📦 Loading Kaggle Plant Disease Dataset..."

# Check if data directory exists
if [ ! -d "data/raw/plant-disease" ]; then
    echo "❌ Error: data/raw/plant-disease directory not found"
    echo "Please download the dataset first:"
    echo "  kaggle datasets download -d emmarex/plantdisease"
    echo "  unzip plantdisease.zip -d data/raw/plant-disease/"
    exit 1
fi

# Count files
FILE_COUNT=$(find data/raw/plant-disease -type f | wc -l)
echo "✓ Found $FILE_COUNT files in dataset"

# Copy to HDFS
echo "📤 Copying data to HDFS..."
docker-compose exec namenode hdfs dfs -mkdir -p /agriculture/raw/diseases
docker-compose exec namenode hdfs dfs -put -f /data/plant-disease /agriculture/raw/diseases/

echo "✓ Dataset loaded successfully!"
echo "📊 To verify: docker-compose exec namenode hdfs dfs -ls /agriculture/raw/diseases"
