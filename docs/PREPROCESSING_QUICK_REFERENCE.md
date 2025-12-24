# Quick Reference: PlantVillage Dataset Preprocessing

## 🚀 Quick Commands

### One-Command Pipeline (Recommended)
```bash
# Run complete preprocessing pipeline
python scripts/run_preprocessing_pipeline.py
```

### Individual Steps
```bash
# 1. Install dependencies
pip install -r scripts/requirements.txt

# 2. Preprocess images
python scripts/preprocess_images.py

# 3. Extract metadata
python scripts/extract_metadata.py
```

## 📦 Output Structure

```
data/processed/
├── plant-disease/
│   ├── train/              # 70% of images (10,490)
│   │   ├── Tomato_Early_blight/
│   │   ├── Potato___healthy/
│   │   └── [15 more classes]/
│   ├── val/                # 15% of images (2,248)
│   ├── test/               # 15% of images (2,249)
│   └── manifest.json       # Dataset structure info
└── metadata/
    ├── image_metadata.csv          # Tabular format for Spark
    ├── image_metadata.json         # JSON format for MongoDB
    ├── class_distribution.json     # Class balance info
    └── dataset_summary.json        # High-level statistics
```

## 🗄️ HDFS Upload Commands

### Create Directories
```bash
docker-compose exec namenode hdfs dfs -mkdir -p /agriculture/plant-disease/processed
docker-compose exec namenode hdfs dfs -mkdir -p /agriculture/plant-disease/metadata
```

### Upload Data
```bash
# Upload all processed images
docker-compose exec namenode bash -c "hdfs dfs -put -f /data/processed/plant-disease/* /agriculture/plant-disease/processed/"

# Upload metadata
docker-compose exec namenode bash -c "hdfs dfs -put -f /data/processed/metadata/* /agriculture/plant-disease/metadata/"
```

### Verify Upload
```bash
# List files
docker-compose exec namenode hdfs dfs -ls -R /agriculture/plant-disease

# Count files
docker-compose exec namenode hdfs dfs -count -h /agriculture/plant-disease

# Check size
docker-compose exec namenode hdfs dfs -du -h /agriculture/plant-disease
```

## 📊 Expected Results

| Metric | Value |
|--------|-------|
| Total Images | ~15,000 |
| Number of Classes | 17 |
| Image Size | 256×256 pixels |
| Format | JPEG (95% quality) |
| Train Split | 70% (~10,490 images) |
| Val Split | 15% (~2,248 images) |
| Test Split | 15% (~2,249 images) |
| Processed Data Size | ~500 MB |
| Metadata Files | 4 files |

## 🔧 Configuration Quick Edit

Edit `scripts/preprocessing_config.yaml`:

```yaml
# Change image size
preprocessing:
  target_size: [256, 256]  # or [224, 224], [512, 512]

# Change split ratios
split:
  train: 0.70
  val: 0.15
  test: 0.15

# Adjust performance
processing:
  num_workers: 4  # Increase for more CPU cores
  batch_size: 100
```

## ✅ Verification Checklist

- [ ] Dependencies installed (`pip install -r scripts/requirements.txt`)
- [ ] Raw data exists in `data/raw/plant-disease/PlantVillage/`
- [ ] Preprocessing completed successfully
- [ ] Metadata extracted successfully
- [ ] Output directories created
- [ ] Files visible in `data/processed/`
- [ ] HDFS containers running (`docker-compose ps`)
- [ ] Data uploaded to HDFS
- [ ] HDFS files verified (`hdfs dfs -ls`)

## 🐛 Common Issues

**Missing dependencies**: `pip install -r scripts/requirements.txt`

**Input data not found**: Check `data/raw/plant-disease/PlantVillage/` exists

**HDFS connection failed**: `docker-compose restart namenode`

**Out of memory**: Reduce `batch_size` in config to 50

## 📖 Full Documentation

For detailed information, see: [`docs/PREPROCESSING_GUIDE.md`](./PREPROCESSING_GUIDE.md)

## Plant Disease Classes (17 total)

### Pepper (2 classes)
- Pepper__bell___Bacterial_spot
- Pepper__bell___healthy

### Potato (3 classes)
- Potato___Early_blight
- Potato___Late_blight
- Potato___healthy

### Tomato (12 classes)
- Tomato_Bacterial_spot
- Tomato_Early_blight
- Tomato_Late_blight
- Tomato_Leaf_Mold
- Tomato_Septoria_leaf_spot
- Tomato_Spider_mites_Two_spotted_spider_mite
- Tomato__Target_Spot
- Tomato__Tomato_YellowLeaf__Curl_Virus
- Tomato__Tomato_mosaic_virus
- Tomato_healthy
- (and more)

## 🎯 Next Steps After Preprocessing

1. **Upload to HDFS** (commands above)
2. **Train ML Models** using processed images
3. **Run Spark Jobs** on metadata for analysis
4. **Integrate with API** for disease detection
5. **Visualize** in React dashboard

---

**Questions?** Check the full guide: `docs/PREPROCESSING_GUIDE.md`
