# Gateway and HDFS Storage Guide

This guide explains how to use the multi-tier storage architecture, role-based access control (RBAC), and sensor simulation features added to the project.

## 🚀 System Overview

The system is designed to handle different data types efficiently:
- **MongoDB (Hot Storage)**: Stores real-time sensor data for the dashboard.
- **HDFS (Cold/Analytics Storage)**: Stores large-scale augmented image datasets, historical simulation logs, and archived real-time data.

---

## 🛠 Setup and Maintenance

### 1. Folder Structure in HDFS
The system expects certain directories to exist in HDFS. Create them with these commands:

```bash
# Create directorie for historical records
docker-compose exec namenode hdfs dfs -mkdir -p /agriculture/historical
```

### 2. Live Code Updates (Volume Mounts)
To ensure code changes in `gateway/src/` reflect immediately in the container, the `docker-compose.yml` uses volume mounting:

```yaml
gateway:
  volumes:
    - ./gateway/src:/app/src
```

### 3. Restarting the Gateway
If you change environment variables or dependencies, restart the container:

```bash
docker-compose up -d --recreate gateway
```

---

## 👤 Role-Based Access Control (RBAC)

The system defines three roles with different capabilities:

| Role | Permissions | Use Case |
| :--- | :--- | :--- |
| **ADMIN** | `manage_users`, `run_simulation`, `view_all_data` | System management and bulk data generation. |
| **FARMER** | `view_own_data`, `view_field` | Managing personal crops and viewing live data. |
| **RESEARCHER** | `run_simulation`, `access_hdfs` | Analyzing historical data and training ML models. |

Users are automatically set up during the gateway initialization (see `setup_environment()` in `main.py`).

---

## 📊 Running Simulations

### Mode 1: Historical Knowledge Base (Default)
Generates historical data (including ML 'knowledge' labels) and stores it directly in HDFS partitions.

```bash
# Default: Generate 30 days of historical data for Farmer Alice
docker-compose exec gateway python src/main.py

# Custom History: Generate 365 days for a specific user
docker-compose exec gateway python src/main.py history 365 RESEARCHER_BOB
```

### Mode 2: Real-time Streaming (Hot -> Cold)
Streams live data to MongoDB (Hot) and archives to HDFS (Cold) in batches.

```bash
# Start real-time stream for Farmer Alice (updates every 5 seconds)
docker-compose exec gateway python src/main.py stream FARMER_ALICE 5
```

---

## 🔍 Verification

### 1. MongoDB Verification
Check if data generation logs and records were created:

```bash
# Check generation logs (Audit trail)
docker-compose exec mongodb mongosh -u admin -p admin123 --authenticationDatabase admin --eval "db.getSiblingDB('agriculture').data_generation_logs.find()"

# Count all records (Users, Fields, Sensors, Diseases)
docker-compose exec mongodb mongosh -u admin -p admin123 --authenticationDatabase admin --eval "var db = db.getSiblingDB('agriculture'); print('Users: ' + db.users.countDocuments()); print('Fields: ' + db.fields.countDocuments()); print('Sensors: ' + db.sensors.countDocuments()); print('Diseases: ' + db.disease_records.countDocuments())"
```

### 2. HDFS Verification
Check if the historical data files were created in the `ml_training` partition:

```bash
# List all generated historical data files
docker-compose exec namenode hdfs dfs -ls -R /agriculture/ml_training/
```

---

## ⚠️ Troubleshooting

- **HDFS Connection Errors**: Ensure `HDFS_NAMENODE` in `docker-compose.yml` is set to `http://namenode:9870` (WebHDFS) rather than the RPC port 9000.
- **Permission Denied**: Check the `user_id` you are passing to the script. Ensure it matches the roles defined in the `RoleManager`.
- **Docker Mounts**: On Windows, ensure Docker has permission to access the project folder if files in `/app/src` aren't updating.
