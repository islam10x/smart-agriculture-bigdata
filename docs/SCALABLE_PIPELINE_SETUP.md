# Scalable HDFS-Spark Pipeline Setup & Guide

This guide details the complete setup, execution, and verification of the scalable Big Data pipeline for the **Smart Agriculture** project.

It specifically addresses the **Low Resource (8GB RAM)** configuration used to successfully run HDFS, Spark, MongoDB, and Gateway services simultaneously on a single machine.

---

## 🏗️ Architecture Overview

The pipeline implements a "Lakehouse" pattern:
1.  **Ingestion Layer**: `gateway` generates simulated IoT sensor data and writes it to **HDFS** (Cold Storage).
2.  **Metadata Layer**: `gateway` writes "hot" data (e.g., disease labels) to **MongoDB**.
3.  **Processing Layer**: **Spark** reads massive datasets from HDFS, joins them with MongoDB labels, and trains ML models.
4.  **Serving Layer**: **Spark** writes Recommendations to **MongoDB**; Models are saved to local disk for persistence.

---

## 🛠️ Low-Resource Optimizations (8GB RAM)

Running a full Hadoop/Spark stack on 8GB RAM required significant tuning. Below are the critical changes made to `docker-compose.yml` and configuration files:

### 1. Service Reduction
We disabled non-essential services to save ~1.5GB RAM:
*   ❌ **DataNodes 2 & 3**: Reduced HDFS cluster to a single DataNode.
*   ❌ **Grafana & Dashboard**: Disabled UI monitoring services.

### 2. Container Memory Limits
Strict limits were enforced to prevent Out-Of-Memory (OOM) crashes:
*   **Spark Master**: `800MB` → Increased to **1.5GB** (Running Driver + Master).
*   **Spark Workers**: `800MB` (Hard Limit) / `512MB` (JVM Heap).
*   **DataNode**: `512MB`.
*   **NameNode**: `512MB`.

### 3. HDFS Replication (`hadoop.env`)
Since we only have 1 DataNode, we must set replication to 1, otherwise HDFS will report "Under Replicated" blocks.
*   `DFS_REPLICATION=1` (Changed from 2).

---

## 🚀 Pipeline Execution Walkthrough

Follow these steps to generate data, train the model, and verify results.

### Step 1: Start the Infrastructure
Start the optimized Docker stack.
```powershell
docker-compose up -d
```
> **Expected Output**: All containers (namenode, datanode1, spark-master, spark-worker-1/2/3, mongodb, gateway, postgres) should show "Started".

### Step 2: Generate Training Data (HDFS)
We need historical data to train the model. This command generates **30 days** of sensor data and uploads it directly to HDFS.
```powershell
docker-compose exec gateway python3 src/main.py history 30
```
> **Expected Output**:
> ```
> Generating historical data for 30 days...
> ...
> Uploaded data_2024-01-01_... to hdfs://namenode:9000/agriculture/ml_training/
> ...
> Historical batch generation complete.
> ```

### Step 3: Verify HDFS Data
Confirm that the files are actually in HDFS.
```powershell
docker-compose exec namenode hdfs dfs -ls -R /agriculture/ml_training
```
> **Expected Output**: A list of `.json` files (e.g., `data_2025-01-01_...json`).

### Step 4: Run Spark ML Training Job
This is the main event. It runs the `disease_prediction_ml.py` job on the Spark cluster.
**Note**: We explicitly define memory settings to fit within our 8GB constraints.

```powershell
docker-compose exec spark-master /opt/spark/bin/spark-submit --jars /opt/spark/extra-jars/mongo-spark-connector_2.12-10.1.1.jar,/opt/spark/extra-jars/mongodb-driver-sync-4.9.0.jar,/opt/spark/extra-jars/mongodb-driver-core-4.9.0.jar,/opt/spark/extra-jars/bson-4.9.0.jar --master spark://spark-master:7077 --conf spark.driver.host=spark-master --conf spark.driver.bindAddress=0.0.0.0 --conf spark.executor.memory=512m --conf spark.executor.memoryOverhead=128m --conf spark.driver.memory=512m /opt/spark-apps/disease_prediction_ml.py
```

> **Expected Output**:
> ```
> ...
> INFO:__main__:✓ Loaded 4320 records from HDFS
> INFO:__main__:✓ Loaded 14 disease labels from MongoDB
> INFO:__main__:✓ Aggregated HDFS data into 90 daily records
> INFO:__main__:Training ML model...
> INFO:__main__:✓ Model saved to /opt/spark-models/disease_prediction_model
> ...
> ```

---

## ✅ Verification

### 1. Check Model Persistence
The model should be saved to your host machine (mapped volume).
```powershell
ls -R ./spark/ml_models
```
> **Success**: You should see a `disease_prediction_model` directory containing Parquet files.

### 2. Check Recommendations (MongoDB)
The job should have generated recommendations for fields based on the analysis.
```powershell
docker-compose exec gateway-service python -c "from pymongo import MongoClient; print(f'Recommendations: {MongoClient(\"mongodb://admin:admin123@mongodb:27017/\").agriculture.recommendations.count_documents({})}')"
```
> **Success**: Output should be `Recommendations: 90` (or similar non-zero number).

---

## ❓ Troubleshooting

**Issue**: `Spark Master OOM / Container Killed`
*   **Cause**: The process `spark-submit` (Driver) runs INSIDE the `spark-master` container. If the container limit is 800MB, but Master needs 300MB and Driver needs 600MB, it crashes.
*   **Fix**: Ensure `spark-master` has at least `1.5GB` limit in `docker-compose.yml`.

**Issue**: `Initial job has not accepted any resources`
*   **Cause**: Spark Workers don't have enough free RAM to launch an executor.
*   **Fix**: Lower `--conf spark.executor.memory` in the submit command (e.g., to `350m` or `450m`).

**Issue**: `ConnectionRefused` to HDFS
*   **Cause**: NameNode is not healthy.
*   **Fix**: Check `docker-compose logs namenode`. If it says "SafeMode", wait a minute or run `hdfs dfsadmin -safemode leave`.
