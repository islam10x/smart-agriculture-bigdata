# PlantVillage Dataset Preprocessing Guide

Complete guide for preprocessing the PlantVillage plant disease dataset and preparing it for HDFS storage and big data analysis.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Steps](#detailed-steps)
4. [Configuration](#configuration)
5. [Scripts Overview](#scripts-overview)
6. [Uploading to HDFS](#uploading-to-hdfs)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **RAM**: Minimum 4GB (8GB recommended)
- **Disk Space**: ~3GB for processed data
- **Docker**: Running with Hadoop HDFS containers

### Python Dependencies

Install required packages:

```bash
# Navigate to scripts directory
cd scripts

# Install dependencies
pip install -r requirements.txt
```

Required packages:
- `Pillow>=10.0.0` - Image processing
- `opencv-python>=4.8.0` - Advanced image operations
- `pandas>=2.0.0` - Data manipulation
- `numpy>=1.24.0` - Numerical operations
- `pyyaml>=6.0` - Configuration parsing
- `tqdm>=4.65.0` - Progress bars
- `scikit-learn>=1.3.0` - Data splitting

## Quick Start

### One-Command Pipeline

Run the complete preprocessing pipeline with a single command:

```bash
# Run from project root
python scripts/run_preprocessing_pipeline.py
```

This will:
1. ✅ Check dependencies
2. ✅ Verify input data
3. ✅ Preprocess all images
4. ✅ Extract metadata
5. ✅ Generate summary reports

**Expected Output Files:**
```
data/processed/
├── plant-disease/
│   ├── train/           # 70% of data
│   │   ├── Tomato_Early_blight/
│   │   ├── Potato___healthy/
│   │   └── ...
│   ├── val/             # 15% of data
│   └── test/            # 15% of data
└── metadata/
    ├── image_metadata.csv
    ├── image_metadata.json
    ├── class_distribution.json
    └── dataset_summary.json
```

## Detailed Steps

### Step 1: Configure Processing Parameters

Edit `scripts/preprocessing_config.yaml` to customize preprocessing:

```yaml
preprocessing:
  target_size: [256, 256]    # Image dimensions
  format: "JPEG"             # Output format
  quality: 95                # JPEG quality (1-100)
  normalize: true            # Normalize pixels to [0, 1]

split:
  train: 0.70               # Training set ratio
  val: 0.15                 # Validation set ratio  
  test: 0.15                # Test set ratio
  random_seed: 42           # For reproducibility
```

### Step 2: Run Image Preprocessing

Process images (resize, normalize, split):

```bash
python scripts/preprocess_images.py
```

**What it does:**
- ✅ Scans all images in `data/raw/plant-disease/PlantVillage/`
- ✅ Validates and loads each image
- ✅ Converts to RGB (if needed)
- ✅ Resizes to 256×256 pixels
- ✅ Normalizes pixel values to [0, 1]
- ✅ Splits into train/val/test sets (stratified by class)
- ✅ Saves processed images to `data/processed/plant-disease/`
- ✅ Creates manifest file with dataset structure

**Expected Output:**
```
📊 PREPROCESSING SUMMARY
==================================================
Total Images Scanned:    15,000
Successfully Processed:  14,987
Skipped/Failed:         13
Corrupted:              0

Split Distribution:
  ├─ Train:  10,490 images
  ├─ Val:    2,248 images
  └─ Test:   2,249 images

✓ Success Rate: 99.91%
```

### Step 3: Extract Metadata

Extract comprehensive metadata from processed images:

```bash
python scripts/extract_metadata.py
```

**What it does:**
- ✅ Scans all processed images
- ✅ Extracts file properties (size, format, dimensions)
- ✅ Parses class labels (plant type, disease, health status)
- ✅ Calculates pixel statistics (mean, std, min, max)
- ✅ Generates metadata in CSV format (for Spark)
- ✅ Generates metadata in JSON format (for MongoDB)
- ✅ Creates class distribution summary
- ✅ Creates dataset summary report

**Output Files:**

1. **`image_metadata.csv`** - Tabular metadata (17+ columns)
   - filename, filepath, file_size_bytes
   - width, height, channels, format
   - class_label, plant_type, disease_name, health_status
   - pixel_mean, pixel_std, red_mean, green_mean, blue_mean
   - created_at, modified_at

2. **`image_metadata.json`** - Nested JSON structure
   ```json
   {
     "dataset_info": {
       "name": "PlantVillage",
       "num_classes": 17,
       "total_images": 14987
     },
     "images": [...]
   }
   ```

3. **`class_distribution.json`** - Class balance info
   ```json
   {
     "Tomato_Early_blight": {
       "train": 700,
       "val": 150,
       "test": 150,
       "total": 1000
     },
     ...
   }
   ```

4. **`dataset_summary.json`** - High-level statistics
   - Overview (counts, splits)
   - Image properties (avg size, dimensions)
   - Plant/disease distribution
   - Configuration used

## Configuration

### Customizing Image Size

For different use cases, adjust target size:

```yaml
preprocessing:
  target_size: [224, 224]  # For MobileNet, ResNet
  # target_size: [299, 299]  # For Inception
  # target_size: [512, 512]  # For high-resolution analysis
```

### Adjusting Split Ratios

```yaml
split:
  train: 0.80   # 80% training
  val: 0.10     # 10% validation
  test: 0.10    # 10% test
```

### Enabling Data Augmentation

To create augmented versions:

```yaml
preprocessing:
  augmentation:
    enabled: true
    rotation_range: 15
    horizontal_flip: true
    brightness_range: [0.8, 1.2]
```

## Scripts Overview

### 1. `preprocessing_config.yaml`
Configuration file with all preprocessing parameters.

### 2. `preprocess_images.py`
Main preprocessing script that handles image loading, resizing, normalization, and splitting.

**Usage:**
```bash
python scripts/preprocess_images.py [config_path]
```

### 3. `extract_metadata.py`
Extracts comprehensive metadata and exports to CSV/JSON formats.

**Usage:**
```bash
python scripts/extract_metadata.py [config_path]
```

### 4. `run_preprocessing_pipeline.py`
End-to-end pipeline that runs all steps sequentially.

**Usage:**
```bash
python scripts/run_preprocessing_pipeline.py
```








## Uploading to HDFS

After preprocessing, upload data to HDFS for distributed processing.

### Step 1: Verify HDFS is Running

```bash
# Check HDFS containers
docker-compose ps namenode

# Access HDFS web UI
# Open: http://localhost:9870
```

### Step 2: Create HDFS Directory Structure

```bash
# Create base directories
docker-compose exec namenode hdfs dfs -mkdir -p /agriculture/plant-disease/processed
docker-compose exec namenode hdfs dfs -mkdir -p /agriculture/plant-disease/metadata
docker-compose exec namenode hdfs dfs -mkdir -p /agriculture/plant-disease/raw
```

### Step 3: Upload Processed Images

```bash
# Upload processed images using generated manifests/splits
docker-compose exec namenode bash -c "hdfs dfs -put -f /data/processed/plant-disease/* /agriculture/plant-disease/processed/"
```

### Step 4: Upload Metadata Files

```bash
# Upload all metadata files
docker-compose exec namenode bash -c "hdfs dfs -put -f /data/processed/metadata/* /agriculture/plant-disease/metadata/"
```

### Step 5: Optionally Upload Raw Images (Backup)

```bash
# Upload original images as backup
docker-compose exec namenode hdfs dfs -put data/raw/plant-disease/PlantVillage /agriculture/plant-disease/raw/
```

## Verification

### Verify Local Processing

```bash
# Check processed images exist
ls -lh data/processed/plant-disease/train/
ls -lh data/processed/plant-disease/val/
ls -lh data/processed/plant-disease/test/

# Check metadata files
ls -lh data/processed/metadata/

# View metadata sample
head -20 data/processed/metadata/image_metadata.csv
```

### Verify HDFS Upload

```bash
# List all files in HDFS
docker-compose exec namenode hdfs dfs -ls -R /agriculture/plant-disease

# Count files and directories
docker-compose exec namenode hdfs dfs -count -h /agriculture/plant-disease

# Check storage usage
docker-compose exec namenode hdfs dfs -du -h /agriculture/plant-disease

# View metadata file
docker-compose exec namenode hdfs dfs -cat /agriculture/plant-disease/metadata/dataset_summary.json | head -50
```

### Test with Spark

```python
# Example: Load metadata in PySpark
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("PlantDiseaseTest").getOrCreate()

# Read metadata CSV from HDFS
df = spark.read.csv(
    "hdfs://namenode:9000/agriculture/plant-disease/metadata/image_metadata.csv",
    header=True,
    inferSchema=True
)

df.show(10)
df.printSchema()
df.groupBy("plant_type", "health_status").count().show()
```

## Troubleshooting

### Issue: Missing Dependencies

**Error:** `ModuleNotFoundError: No module named 'PIL'`

**Solution:**
```bash
pip install -r scripts/requirements.txt
```

---

### Issue: Input Data Not Found

**Error:** `✗ Raw data directory not found`

**Solution:**
- Verify dataset location: `data/raw/plant-disease/PlantVillage/`
- Check that images are organized by class in subdirectories
- Ensure dataset is extracted (not still in `.zip` file)

---

### Issue: Out of Memory

**Error:** `MemoryError` during processing

**Solution:**
- Reduce `batch_size` in config:
  ```yaml
  processing:
    batch_size: 50  # Reduce from 100
  ```
- Close other applications
- Process one split at a time

---

### Issue: HDFS Connection Failed

**Error:** Cannot connect to HDFS

**Solution:**
```bash
# Restart HDFS containers
docker-compose restart namenode datanode1 datanode2 datanode3

# Check HDFS health
docker-compose exec namenode hdfs dfsadmin -report
```

---

### Issue: Corrupted Images

**Error:** Some images fail to load

**Solution:**
- Script automatically skips corrupted images by default
- Check logs for specific filenames
- Manually remove corrupted files from raw directory
- Re-run preprocessing

---

### Issue: Slow Processing

**Problem:** Preprocessing takes too long

**Solution:**
- Enable parallel processing:
  ```yaml
  processing:
    num_workers: 8  # Increase based on CPU cores
  ```
- Use SSD storage if available
- Disable metadata statistics:
  ```yaml
  metadata:
    extract_statistics: false
  ```

## Performance Tips

1. **Use SSD Storage**: Store data on SSD for faster I/O
2. **Increase Workers**: Set `num_workers` based on CPU cores
3. **Batch Processing**: Keep `batch_size` at 100 for optimal memory usage
4. **Skip Statistics**: Disable advanced metadata if not needed

## Next Steps

After successful preprocessing and HDFS upload:

1. **Build ML Models**: Use processed images for disease classification
2. **Spark Analysis**: Analyze metadata with Spark batch jobs
3. **Dashboard Integration**: Connect processed data to React dashboard
4. **API Integration**: Expose disease detection via FastAPI endpoints

## Support

For issues or questions:
- Check logs in console output
- Review configuration in `preprocessing_config.yaml`
- Verify HDFS status at http://localhost:9870
- Check dataset structure matches PlantVillage format

---

**Built for the Smart Agriculture Big Data Platform** 🌾
