# Spark Analytics Jobs - Quick Reference & Execution Guide

Complete guide for running Spark batch jobs, understanding the ML pipeline, and interpreting analytics results.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [ML Model Setup](#ml-model-setup)
4. [Job Descriptions](#job-descriptions)
5. [Execution Commands](#execution-commands)
6. [Data Flow & Pipeline](#data-flow--pipeline)
7. [Output Collections](#output-collections)
8. [Verification & Results](#verification--results)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Usage](#advanced-usage)

---

## 🎯 Prerequisites

### System Requirements
- **Docker**: All Spark containers running
- **MongoDB**: Populated with sensor and disease data
- **Memory**: Minimum 8GB RAM allocated to Docker
- **Data**: At least 30 days of sensor readings in MongoDB

### Check Services Status

```bash
# Verify all containers are running
docker-compose ps

# Check Spark cluster health (should show 3 workers)
curl -s http://localhost:8080 | grep -o "Workers ([0-9]*)"

# Verify MongoDB has data
docker exec mongodb mongosh agriculture --eval "
print('Sensor readings:', db.sensor_data.countDocuments({}));
print('Disease records:', db.disease_records.countDocuments({}));
" -u admin -p admin123 --authenticationDatabase admin --quiet
```

**Expected Output:**
```
Sensor readings: 1800+
Disease records: 40+
Workers (3)
```

---

## 🚀 Quick Start

### One-Command Execution (Recommended)

Run the complete analytics pipeline with a single command:

```bash
# Execute all 5 jobs in sequence
docker-compose exec spark-master python3 /opt/spark-apps/run_all_jobs.py
```

**What it does:**
1. ✅ Aggregates daily sensor statistics
2. ✅ Analyzes disease frequency patterns
3. ✅ Cleans data quality issues
4. ✅ Trains ML model & generates AI recommendations
5. ✅ Calculates correlations between factors and diseases

**Expected Duration:** 12-15 minutes

**Expected Output:**
```
======================================================================
📊 SMART AGRICULTURE ANALYTICS PIPELINE
======================================================================
MongoDB: mongodb://admin:***@mongodb:27017/agriculture
Spark Master: spark://spark-master:7077
======================================================================

======================================================================
🚀 Starting: Daily Sensor Aggregation
Script: /opt/spark-apps/daily_sensor_aggregation.py
======================================================================
✓ Daily Sensor Aggregation completed successfully (120.5s)

======================================================================
🚀 Starting: Disease Frequency Analysis
======================================================================
✓ Disease Frequency Analysis completed successfully (85.2s)

======================================================================
🚀 Starting: Data Quality Cleaner
======================================================================
✓ Data Quality Cleaner completed successfully (180.3s)

======================================================================
🚀 Starting: Disease Prediction ML
======================================================================
✓ Disease Prediction ML completed successfully (420.8s)

======================================================================
🚀 Starting: Correlation Analysis
======================================================================
✓ Correlation Analysis completed successfully (150.2s)

======================================================================
📋 PIPELINE EXECUTION SUMMARY
======================================================================
✓ Daily Sensor Aggregation
✓ Disease Frequency Analysis
✓ Data Quality Cleaner
✓ Disease Prediction ML
✓ Correlation Analysis

Results: 5/5 jobs successful
Total Duration: 14.3 minutes (858s)

✅ All jobs completed successfully!
======================================================================
```

---

## 🎓 ML Model Setup

### First Time Setup (Train the Model)

Before running the analytics pipeline for the first time, you need to train the disease prediction model.

#### **Option 1: Run Training Script Directly**

```bash
# Train model and save to /opt/spark/ml/
docker-compose exec spark-master /opt/spark/bin/spark-submit \
  --jars /opt/spark/extra-jars/mongo-spark-connector_2.12-10.1.1.jar,/opt/spark/extra-jars/mongodb-driver-sync-4.9.0.jar,/opt/spark/extra-jars/mongodb-driver-core-4.9.0.jar,/opt/spark/extra-jars/bson-4.9.0.jar \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  --driver-memory 1G \
  --executor-memory 2G \
  /opt/spark-apps/train_model.py
```

**Expected Output:**
```
======================================================================
🎓 MODEL TRAINING MODE
======================================================================
MongoDB: mongodb://admin:***@mongodb:27017/agriculture
Database: agriculture
Model will be saved to: /opt/spark/ml/disease_prediction_model
======================================================================

🔄 Starting model training...
✓ Loaded 180 sensor summaries
✓ Loaded 45 disease records
✓ Prepared 180 training records
✓ Clean training records: 180
Training: 144, Testing: 36
✓ Model AUC: 0.8542
✓ Model saved to /opt/spark/ml/disease_prediction_model

======================================================================
✅ MODEL TRAINED AND SAVED SUCCESSFULLY
======================================================================
The model is now available at: /opt/spark/ml/disease_prediction_model
Future runs will use this pre-trained model.
======================================================================
```

#### **Option 2: Run Orchestrator with Training Flag**

```bash
# Train model as part of pipeline
docker-compose exec spark-master python3 /opt/spark-apps/run_all_jobs.py --train
```

**What it does:**
- Trains the model first
- Then runs all 5 analytics jobs
- Uses the newly trained model for predictions

**Expected Output:**
```
======================================================================
📊 SMART AGRICULTURE ANALYTICS PIPELINE
======================================================================
MongoDB: mongodb://admin:***@mongodb:27017/agriculture
Spark Master: spark://spark-master:7077
ML Model Path: /opt/spark/ml/disease_prediction_model
======================================================================

🎓 TRAINING MODE ENABLED - Will retrain model first

======================================================================
🚀 Starting: Model Training
Script: /opt/spark-apps/train_model.py
======================================================================
✓ Model Training completed successfully (320.5s)

======================================================================
🚀 Starting: Daily Sensor Aggregation
...
```

---

### Normal Operations (Use Existing Model)

Once the model is trained, run the pipeline normally:

```bash
# Use pre-trained model (no retraining)
docker-compose exec spark-master python3 /opt/spark-apps/run_all_jobs.py
```

**What it does:**
- ✅ Loads the pre-trained model from `/opt/spark/ml/`
- ✅ Runs all analytics jobs
- ✅ Generates predictions without retraining
- ⚡ Much faster (saves 5-7 minutes)

**Expected Output:**
```
======================================================================
📊 SMART AGRICULTURE ANALYTICS PIPELINE
======================================================================
ML Model Path: /opt/spark/ml/disease_prediction_model
✓ Pre-trained model found at /opt/spark/ml/disease_prediction_model
======================================================================

[All jobs run with existing model]
```

---

### Force Retrain the Model

If you want to retrain with new data (e.g., after adding more sensor/disease records):

#### **Option 1: Retrain via Orchestrator**

```bash
# Retrain model and run full pipeline
docker-compose exec spark-master python3 /opt/spark-apps/run_all_jobs.py --retrain
```

#### **Option 2: Retrain ML Job Directly**

```bash
# Only retrain the model
docker-compose exec spark-master /opt/spark/bin/spark-submit \
  --jars /opt/spark/extra-jars/mongo-spark-connector_2.12-10.1.1.jar,/opt/spark/extra-jars/mongodb-driver-sync-4.9.0.jar,/opt/spark/extra-jars/mongodb-driver-core-4.9.0.jar,/opt/spark/extra-jars/bson-4.9.0.jar \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  --driver-memory 1G \
  --executor-memory 2G \
  /opt/spark-apps/disease_prediction_ml.py --retrain
```

---

### Check if Model Exists

```bash
# Verify model is trained and saved
docker exec spark-master ls -lh /opt/spark/ml/disease_prediction_model/

# Expected output:
# drwxr-xr-x 2 root root 4.0K metadata
# drwxr-xr-x 2 root root 4.0K stages
```

---

### Model Training Best Practices

| Scenario | Command | When to Use |
|----------|---------|-------------|
| **First Time** | `--train` | Initial setup, no model exists |
| **Daily Runs** | No flags | Model already trained, just predict |
| **New Data Added** | `--retrain` | Added more sensor/disease records |
| **Model Tuning** | `--retrain` | Want to adjust hyperparameters |
| **Performance Issues** | `--retrain` | Model accuracy degraded |

---

## 📊 Job Descriptions

### 1. Daily Sensor Aggregation
**File:** `daily_sensor_aggregation.py`  
**Purpose:** Computes daily summary statistics for all sensor readings  
**Runtime:** 2-3 minutes  
**Input:** `sensor_data` collection  
**Output:** `daily_sensor_summary` collection

**What it does:**
- Aggregates raw sensor readings by field and sensor type
- Calculates min/max/avg/stddev for temperature, humidity, moisture
- Sums rainfall totals, averages wind speed
- Computes NPK nutrient levels (nitrogen, phosphorus, potassium)
- Creates daily summaries for ML feature engineering

**Output Schema:**
```json
{
  "field_id": "FIELD_001",
  "sensor_type": "soil",
  "aggregation_date": "2024-12-25",
  "temp_min": 18.5,
  "temp_max": 28.3,
  "temp_avg": 23.4,
  "humidity_avg": 65.2,
  "moisture_avg": 42.8,
  "rainfall_total": 12.5,
  "nitrogen_avg": 45.2,
  "phosphorus_avg": 30.1,
  "potassium_avg": 41.7,
  "record_count": 48
}
```

---

### 2. Disease Frequency Analysis
**File:** `disease_frequency_analysis.py`  
**Purpose:** Analyzes disease patterns and generates statistics  
**Runtime:** 1-2 minutes  
**Input:** `disease_records` collection  
**Output:** `disease_statistics` collection

**What it does:**
- Counts disease occurrences by type, field, and season
- Calculates average severity levels
- Identifies seasonal patterns
- Tracks disease spread over time
- Generates top disease rankings

**Output Schema:**
```json
{
  "timestamp": "2024-12-25T14:00:00Z",
  "lookback_days": 30,
  "overall_statistics": {
    "total_records": 45,
    "avg_severity": 0.62,
    "unique_diseases": 5,
    "affected_fields": 8
  },
  "disease_by_field": [
    {
      "disease": "Tomato_Early_blight",
      "field_id": "FIELD_001",
      "occurrence_count": 12,
      "avg_severity": 0.68,
      "first_detected": "2024-11-25",
      "last_detected": "2024-12-20"
    }
  ],
  "disease_by_season": [...],
  "top_diseases": [...]
}
```

---

### 3. Data Quality Cleaner
**File:** `data_quality_cleaner.py`  
**Purpose:** Fixes null values and ensures data integrity for ML  
**Runtime:** 3-4 minutes  
**Input:** `daily_sensor_summary` collection  
**Output:** Clean `daily_sensor_summary` + `data_quality_report`

**What it does:**
- Detects null/missing values in sensor summaries
- Imputes nulls using field-level means
- Fills remaining nulls with global means
- Removes rows if nulls persist (last resort)
- Generates quality report

**Output Report:**
```json
{
  "timestamp": "2024-12-25T14:00:00Z",
  "original_count": 1800,
  "clean_count": 1800,
  "removed_count": 0,
  "removal_percentage": 0,
  "status": "completed",
  "null_summary": {
    "temp_avg": 0,
    "humidity_avg": 0,
    "moisture_avg": 0
  }
}
```

**Why it's important:**
- ML models cannot handle null values
- Correlation analysis requires complete data
- Ensures consistent feature engineering

---

### 4. Disease Prediction ML (with AI Recommendations)
**File:** `disease_prediction_ml.py`  
**Purpose:** Trains ML model and generates AI-powered recommendations  
**Runtime:** 5-7 minutes  
**Input:** `daily_sensor_summary` + `disease_records`  
**Output:** `recommendations` collection + trained model

**What it does:**
- Joins sensor data with disease labels
- Trains Logistic Regression model on 5 features:
  - Temperature average
  - Humidity average
  - Soil moisture average
  - Rainfall total
  - Nitrogen levels
- Generates risk scores (0-1) for each field
- **Sends data to Claude AI** for intelligent recommendations
- Stores complete recommendations in MongoDB

**Key Features:**
- Uses PySpark MLlib for distributed training
- Standardizes features with StandardScaler
- 80/20 train-test split with stratification
- Evaluates model with AUC metric
- Integrates with Anthropic Claude API

**Output Schema:**
```json
{
  "field_id": "FIELD_001",
  "prediction_date": "2024-12-25",
  "risk_score": 0.72,
  "confidence": "high",
  "model_prediction": {
    "temp_avg": 28.5,
    "humidity_avg": 78.2,
    "moisture_avg": 65.3,
    "rainfall_total": 15.2,
    "nitrogen_avg": 42.1
  },
  "ai_recommendation": {
    "likely_disease": "Late Blight",
    "risk_explanation": "High humidity (78%) and recent rainfall create ideal conditions for fungal diseases",
    "immediate_actions": [
      "Apply copper-based fungicide within 24 hours",
      "Remove infected leaves immediately",
      "Increase air circulation between plants"
    ],
    "treatment_options": [
      "Copper hydroxide spray",
      "Mancozeb fungicide",
      "Chlorothalonil treatment"
    ],
    "preventive_measures": [
      "Install drip irrigation to avoid leaf wetness",
      "Space plants 60cm apart for air flow",
      "Apply preventive fungicide every 7-10 days"
    ],
    "monitoring_frequency_hours": 12
  },
  "created_at": "2024-12-25T14:30:00Z"
}
```

**Claude AI Integration:**
- Requires `ANTHROPIC_API_KEY` environment variable
- Falls back to rule-based recommendations if API unavailable
- Generates context-aware, actionable advice
- Uses Claude Sonnet 4.5 model

---

### 5. Correlation Analysis
**File:** `correlation_analysis.py`  
**Purpose:** Analyzes correlations between environmental factors and disease  
**Runtime:** 2-3 minutes  
**Input:** `daily_sensor_summary` + `disease_records`  
**Output:** `correlations` collection

**What it does:**
- Calculates Pearson correlation coefficients
- Calculates Spearman correlation (non-linear relationships)
- Identifies significant correlations (p-value < 0.05)
- Ranks features by correlation strength
- Generates interpretations

**Output Schema:**
```json
{
  "timestamp": "2024-12-25T14:00:00Z",
  "lookback_days": 90,
  "total_records_analyzed": 1800,
  "correlations": [
    {
      "feature": "humidity_avg",
      "pearson_correlation": 0.68,
      "pearson_pvalue": 0.0001,
      "spearman_correlation": 0.65,
      "spearman_pvalue": 0.0002,
      "is_significant": true,
      "interpretation": "Strong - increases disease risk"
    },
    {
      "feature": "moisture_avg",
      "pearson_correlation": 0.52,
      "pearson_pvalue": 0.003,
      "is_significant": true,
      "interpretation": "Moderate - increases disease risk"
    }
  ],
  "top_risk_factors": [
    "humidity_avg",
    "moisture_avg",
    "rainfall_total"
  ],
  "summary": {
    "total_features": 7,
    "significant_features": 4,
    "avg_correlation": 0.42
  }
}
```

---

## 💻 Execution Commands

### Execute Complete Pipeline

```bash
# Run all jobs in sequence
 docker-compose exec spark-master python3 /opt/spark-apps/run_all_jobs.py
 ```

---

### Execute Individual Jobs

#### 1. Daily Sensor Aggregation
```bash
docker-compose exec spark-master /opt/spark/bin/spark-submit `
  --jars /opt/spark/extra-jars/mongo-spark-connector_2.12-10.1.1.jar,/opt/spark/extra-jars/mongodb-driver-sync-4.9.0.jar,/opt/spark/extra-jars/mongodb-driver-core-4.9.0.jar,/opt/spark/extra-jars/bson-4.9.0.jar `
  --master spark://spark-master:7077 `
  --deploy-mode client `
  --driver-memory 1G `
  --executor-memory 2G `
  /opt/spark-apps/daily_sensor_aggregation.py
```

#### 2. Disease Frequency Analysis
```bash
docker-compose exec spark-master /opt/spark/bin/spark-submit `
  --jars /opt/spark/extra-jars/mongo-spark-connector_2.12-10.1.1.jar,/opt/spark/extra-jars/mongodb-driver-sync-4.9.0.jar,/opt/spark/extra-jars/mongodb-driver-core-4.9.0.jar,/opt/spark/extra-jars/bson-4.9.0.jar `
  --master spark://spark-master:7077 `
  --deploy-mode client `
  --driver-memory 1G `
  --executor-memory 2G `
  /opt/spark-apps/disease_frequency_analysis.py

```

#### 3. Data Quality Cleaner
```bash
docker-compose exec spark-master /opt/spark/bin/spark-submit `
  --jars /opt/spark/extra-jars/mongo-spark-connector_2.12-10.1.1.jar,/opt/spark/extra-jars/mongodb-driver-sync-4.9.0.jar,/opt/spark/extra-jars/mongodb-driver-core-4.9.0.jar,/opt/spark/extra-jars/bson-4.9.0.jar `
  --master spark://spark-master:7077 `
  --deploy-mode client `
  --driver-memory 1G `
  --executor-memory 2G `
  /opt/spark-apps/data_quality_cleaner.py
```

#### 4. Disease Prediction ML
```bash
docker-compose exec spark-master /opt/spark/bin/spark-submit `
  --jars /opt/spark/extra-jars/mongo-spark-connector_2.12-10.1.1.jar,/opt/spark/extra-jars/mongodb-driver-sync-4.9.0.jar,/opt/spark/extra-jars/mongodb-driver-core-4.9.0.jar,/opt/spark/extra-jars/bson-4.9.0.jar `
  --master spark://spark-master:7077 `
  --deploy-mode client `
  --driver-memory 1G `
  --executor-memory 2G `
  /opt/spark-apps/disease_prediction_ml.py
```

#### 5. Correlation Analysis
```bash
docker-compose exec spark-master /opt/spark/bin/spark-submit `
  --jars /opt/spark/extra-jars/mongo-spark-connector_2.12-10.1.1.jar,/opt/spark/extra-jars/mongodb-driver-sync-4.9.0.jar,/opt/spark/extra-jars/mongodb-driver-core-4.9.0.jar,/opt/spark/extra-jars/bson-4.9.0.jar `
  --master spark://spark-master:7077 `
  --deploy-mode client `
  --driver-memory 1G `
  --executor-memory 2G `
  /opt/spark-apps/correlation_analysis.py
```

---

## 🔄 Data Flow & Pipeline

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAW DATA (MongoDB)                           │
│  • sensor_data (raw readings)                                   │
│  • disease_records (detection events)                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              JOB 1: Daily Sensor Aggregation                    │
│  • Groups by field + sensor type + date                         │
│  • Calculates statistics (min/max/avg/std)                      │
│  Output: daily_sensor_summary                                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              JOB 2: Disease Frequency Analysis                  │
│  • Analyzes patterns by season, month, field                    │
│  • Calculates severity trends                                   │
│  Output: disease_statistics                                     │
└─────────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              JOB 3: Data Quality Cleaner                        │
│  • Detects and fixes null values                                │
│  • Imputes missing data with field/global means                 │
│  Output: Clean daily_sensor_summary                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              JOB 4: Disease Prediction ML                       │
│  • Trains Logistic Regression model                             │
│  • Generates risk scores (0-1)                                  │
│  • Sends to Claude AI for recommendations                       │
│  Output: recommendations (with AI insights)                     │
└─────────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              JOB 5: Correlation Analysis                        │
│  • Calculates Pearson + Spearman correlations                   │
│  • Identifies significant risk factors                          │
│  Output: correlations                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Data Dependencies

```
sensor_data + disease_records
    ├─> daily_sensor_aggregation.py
    │       └─> daily_sensor_summary
    │
    ├─> disease_frequency_analysis.py
    │       └─> disease_statistics
    │
    └─> daily_sensor_summary
            ├─> data_quality_cleaner.py
            │       └─> Clean daily_sensor_summary
            │
            ├─> disease_prediction_ml.py
            │       └─> recommendations (with Claude AI)
            │
            └─> correlation_analysis.py
                    └─> correlations
```

---

## 📚 Output Collections

### MongoDB Collections Created by Jobs

| Collection | Created By | Purpose | Document Count |
|-----------|-----------|---------|----------------|
| `daily_sensor_summary` | Job 1 | Daily aggregated sensor stats | ~90 per field |
| `disease_statistics` | Job 2 | Disease pattern analysis | 1 summary doc |
| `data_quality_report` | Job 3 | Data cleaning report | 1 report doc |
| `recommendations` | Job 4 | AI-powered predictions | ~100 predictions |
| `correlations` | Job 5 | Feature correlation analysis | 1 analysis doc |
| `job_execution_log` | Orchestrator | Job execution history | 1 per job run |

---

## ✅ Verification & Results

### Check Job Execution History

```bash
# View last 10 job runs
docker exec mongodb mongosh agriculture --eval "
  db.job_execution_log.find()
    .sort({timestamp: -1})
    .limit(10)
    .forEach(doc => {
      print(doc.job_name + ' - ' + doc.status + ' (' + doc.duration_seconds + 's)');
    });
" -u admin -p admin123 --authenticationDatabase admin --quiet
```

**Expected Output:**
```
Correlation Analysis - success (150.2s)
Disease Prediction ML - success (420.8s)
Data Quality Cleaner - success (180.3s)
Disease Frequency Analysis - success (85.2s)
Daily Sensor Aggregation - success (120.5s)
```

---

### View AI Recommendations

```bash
# Get latest recommendations with Claude AI insights
docker exec mongodb mongosh agriculture --eval "
  db.recommendations.find()
    .sort({created_at: -1})
    .limit(3)
    .forEach(doc => {
      print('='.repeat(60));
      print('Field:', doc.field_id);
      print('Risk Score:', doc.risk_score);
      print('Disease:', doc.ai_recommendation.likely_disease);
      print('Actions:');
      doc.ai_recommendation.immediate_actions.forEach(a => print('  -', a));
    });
" -u admin -p admin123 --authenticationDatabase admin --quiet
```

**Expected Output:**
```
============================================================
Field: FIELD_001
Risk Score: 0.72
Disease: Late Blight
Actions:
  - Apply copper-based fungicide within 24 hours
  - Remove infected leaves immediately
  - Increase air circulation between plants
============================================================
```

---

### View Correlation Results

```bash
# View top risk factors
docker exec mongodb mongosh agriculture --eval "
  var doc = db.correlations.findOne();
  print('Top Risk Factors:');
  doc.correlations.slice(0, 5).forEach(c => {
    print('  -', c.feature + ':', c.pearson_correlation.toFixed(3), 
          '(' + c.interpretation + ')');
  });
" -u admin -p admin123 --authenticationDatabase admin --quiet
```

**Expected Output:**
```
Top Risk Factors:
  - humidity_avg: 0.680 (Strong - increases disease risk)
  - moisture_avg: 0.520 (Moderate - increases disease risk)
  - rainfall_total: 0.485 (Moderate - increases disease risk)
  - temp_avg: 0.320 (Weak - increases disease risk)
  - nitrogen_avg: -0.150 (Weak - decreases disease risk)
```

---

### Check Data Quality Report

```bash
# View data cleaning summary
docker exec mongodb mongosh agriculture --eval "
  var report = db.data_quality_report.findOne();
  print('Data Quality Report:');
  print('  Original Records:', report.original_count);
  print('  Clean Records:', report.clean_count);
  print('  Removed:', report.removed_count, '(' + report.removal_percentage + '%)');
  print('  Status:', report.status);
" -u admin -p admin123 --authenticationDatabase admin --quiet
```

---

### View Disease Statistics

```bash
# View disease frequency stats
docker exec mongodb mongosh agriculture --eval "
  var stats = db.disease_statistics.findOne();
  print('Disease Statistics:');
  print('  Total Records:', stats.overall_statistics.total_records);
  print('  Unique Diseases:', stats.overall_statistics.unique_diseases);
  print('  Affected Fields:', stats.overall_statistics.affected_fields);
  print('  Avg Severity:', stats.overall_statistics.avg_severity.toFixed(2));
  print('\\nTop Diseases:');
  stats.top_diseases.slice(0, 3).forEach(d => {
    print('  -', d.disease + ':', d.occurrence_count, 'cases');
  });
" -u admin -p admin123 --authenticationDatabase admin --quiet
```

---

## 🔧 Troubleshooting


### Job Fails: "Claude API error"

**Problem:** ML job cannot reach Claude AI

**Solution:**
```bash
# Check if API key is set
docker exec spark-master printenv ANTHROPIC_API_KEY

# If empty, add to .env file:
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# Restart services
docker-compose restart spark-master spark-worker-1 spark-worker-2 spark-worker-3

# Job will use fallback recommendations if API unavailable
```

---

### Job Fails: "Out of memory"

**Problem:** Spark workers running out of memory

**Solution:**
```bash
# Edit docker-compose.yml
# Increase worker memory:
spark-worker-1:
  environment:
    SPARK_WORKER_MEMORY: 4G  # Increase from 3G

# Restart workers
docker-compose restart spark-worker-1 spark-worker-2 spark-worker-3
```

---

### Job Hangs: "Stuck at X%"

**Problem:** Job appears frozen

**Solution:**
```bash
# Check Spark UI for failed stages
# Open: http://localhost:8080
# Click on running application

# Check worker logs
docker-compose logs spark-worker-1 --tail=50

# If truly stuck, restart job
docker exec spark-master pkill -f spark-submit
docker exec -it spark-master python3 /opt/spark-apps/job_orchestrator.py
```

---

### Data Quality Issues: "High null percentage"

**Problem:** Too many null values removed

**Solution:**
```bash
# Check data generation quality
docker exec mongodb mongosh agriculture --eval "
  db.sensor_data.aggregate([
    {$project: {
      has_temp: {$cond: [{$ne: ['$readings.temperature', null]}, 1, 0]},
      has_humidity: {$cond: [{$ne: ['$readings.humidity', null]}, 1, 0]}
    }},
    {$group: {
      _id: null,
      total: {$sum: 1},
      with_temp: {$sum: '$has_temp'},
      with_humidity: {$sum: '$has_humidity'}
    }}
  ])
" -u admin -p admin123 --quiet

# If many nulls, regenerate data with better quality
docker exec gateway-service python3 -c "
from src.data_generator import generate_sample_data
generate_sample_data(num_fields=5, days=90)
"
```

---

## 🎯 Advanced Usage

### Schedule Daily Execution

Add to crontab for automatic daily runs:

```bash
# Run at 2 AM every day
docker exec spark-master bash -c "
echo '0 2 * * * /usr/bin/python3 /opt/spark-apps/job_orchestrator.py >> /var/log/spark-jobs.log 2>&1' | crontab -
"

# Verify crontab
docker exec spark-master crontab -l
```

---

### Customize Job Parameters

Edit scripts directly or pass parameters:

```python
# In disease_prediction_ml.py
# Change model parameters
lr = LogisticRegression(
    maxIter=200,        # Increase iterations
    regParam=0.001,     # Reduce regularization
    elasticNetParam=0.5 # Change L1/L2 mix
)

# In correlation_analysis.py
# Change lookback period
success = analyzer.run(lookback_days=180)  # Analyze 6 months
```

---

### Monitor Performance

```bash
# View Spark UI for job details
open http://localhost:8080

# Check container stats
docker stats spark-master spark-worker-1 spark-worker-2 spark-worker-3

# View detailed job logs
docker-compose logs -f spark-master
```

---

## 📊 Expected Performance

| Job | Runtime | Memory | CPU | Output Size |
|-----|---------|--------|-----|-------------|
| Sensor Aggregation | 2-3 min | ~1.5 GB | Medium | ~5 KB |
| Disease Frequency | 1-2 min | ~1 GB | Low | ~10 KB |
| Data Quality | 3-4 min | ~2 GB | Medium | ~2 KB |
| ML Prediction | 5-7 min | ~3 GB | High | ~50 KB |
| Correlation | 2-3 min | ~2 GB | Medium | ~15 KB |

**Total Pipeline:** ~15 minutes, ~8 GB peak memory

---

## 🎉 Success Checklist

After running jobs, verify:

- [ ] All 5 jobs show "success" in `job_execution_log`
- [ ] `daily_sensor_summary` has ~90 docs per field
- [ ] `recommendations` collection has predictions
- [ ] `correlations` shows significant features
- [ ] `data_quality_report` shows low null percentage (<5%)
- [ ] No error messages in Spark logs
- [ ] Spark UI shows completed applications

---

## 📚 Next Steps

After successful job execution:

1. **API Integration**: Access results via FastAPI endpoints
2. **Dashboard Visualization**: Display predictions in React dashboard
3. **Alert System**: Set up notifications for high-risk predictions
4. **Model Monitoring**: Track model performance over time
5. **Production Deployment**: Schedule jobs for continuous operation

---

**Built for the Smart Agriculture Big Data Platform** 🌾🚜📊