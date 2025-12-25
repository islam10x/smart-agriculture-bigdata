# Sensor Simulation & Data Strategy

This document provides a technical deep-dive into the smart agriculture data platform. It explains how location contexts are determined, where data is stored, and the exact schemas used for integration.

---

## 🌍 WeatherAPI Location Logic

**How does the system know which location to check?**

The location is **NOT** dynamic per sensor. It is inherited from the **Field Definition** in the database.

1.  **Field Creation**: When a farmer creates a field (e.g., "North Tomato Field"), they provide GPS coordinates (`latitude`, `longitude`).
    *   *Source Code*: `gateway/main.py -> FieldManager.create_field()`
2.  **Sensor Assignment**: Sensors are assigned to that field and inherit its location (plus or minus 10 meters for variance).
3.  **Weather Context**:
    *   The `WeatherSimulator` reads the **Field's Latitude/Longitude**.
    *   It passes these exact coordinates to the **OpenWeatherMap API**:
        `GET api.openweathermap.org/data/2.5/weather?lat={FIELD_LAT}&lon={FIELD_LON}`
    *   This ensures the weather data matches the exact micro-climate of the farm.

---

## 📂 Data Storage & Schemas

The system uses a **Poltglot Persistence** architecture, utilizing both MongoDB and HDFS.

### 1. MongoDB (Hot Storage) 🔥

**Purpose**: Real-time alerts, Dashboard UI, User Profiles.
**Access**: Port `27017` (URI: `mongodb://admin:admin123@localhost:27017/`)

#### Collection: `sensor_data`
Used for live graphs. Time-To-Live (TTL) index is recommended here (e.g., delete after 30 days).

```json
{
  "_id": "ObjectId('...')",
  "sensor_id": "SOIL_FIELD_001_001",
  "field_id": "FIELD_FARMER_ALICE_1234",
  "sensor_type": "soil",   // or "atmospheric"
  "timestamp": "2024-12-25T14:30:00Z",
  "location": { "lat": 36.8, "lon": 10.1 },
  "readings": {
    "moisture": 45.2,      // Percentage
    "temperature": 23.5,   // Celsius
    "ph": 6.8,
    "nitrogen": 45.0,      // mg/kg
    "phosphorus": 30.2,
    "potassium": 41.5
  },
  "weather_context": {
    "is_raining": false,
    "humidity": 60,
    "source": "openweathermap"
  }
}
```

#### Collection: `disease_records`
Stores detected risks for alert notifications.

```json
{
  "field_id": "FIELD_FARMER_ALICE_1234",
  "disease": "Tomato_Early_blight",
  "severity": 0.72,        // 0.0 - 1.0 Risk Score
  "status": "active_infection",
  "detection_date": "2024-12-25T14:00:00Z"
}
```

---

### 2. HDFS (Cold Storage) ❄️

**Purpose**: Machine Learning Training, Historical Trends, Spark Batch Processing.
**Access**: Port `9000` (NameNode URI: `hdfs://namenode:9000/`)
**Web UI**: `http://localhost:9870`

#### Directory Structure
Data is partitioned by **Date** to optimize Spark read performance (Predicate Pushdown).

```
/agriculture
    /ml_training
        /20241225/
            data_103000.json
            data_104500.json
        /20241226/
            ...
    /realtime_archive
        /20241225/
            ...
```

#### File Format & Schema (JSON/Parquet)
Files contain an **Array of JSON Objects**. The schema acts as a "Fat Table" combining Sensor + Weather data.

| Field | Type | Description |
| :--- | :--- | :--- |
| `sensor_id` | String | Unique ID of the device |
| `field_id` | String | ID of the farm field |
| `timestamp` | Timestamp | UTC time of reading |
| `readings.temperature` | Double | Sensor reading |
| `readings.moisture` | Double | Sensor reading |
| `weather_context.rainfall` | Double | Rain at that moment (for correlation) |
| `weather_context.season` | String | ML Feature: 'summer', 'winter' |

---

## 💻 Verification & Inspection Commands

Run these commands in your **local terminal** to inspect the live data inside the containers.

### 🔍 MongoDB Verification

**1. Connect to the MongoDB Shell:**
```bash
docker-compose exec mongodb mongosh -u admin -p admin123 --authenticationDatabase admin agriculture
```

**2. Check for latest Sensor Data (Last 3 entries):**
```javascript
// Paste this into the mongosh shell
db.sensor_data.find().sort({timestamp: -1}).limit(3).pretty()
```

**3. Check for any detected Diseases:**
```javascript
db.disease_records.find().pretty()
```

### 🔍 HDFS Verification

**1. List Processed Data Directories:**
```bash
docker-compose exec namenode hdfs dfs -ls -R /agriculture
```

**2. View Content of a Stored File:**
*(First, list files to get a filename, then use cat to view logic keep in mind these file names are different for each one based on the date and time)*

**PowerShell (Windows):**
```powershell
# Step 1: Find a file (e.g., in ml_training)
docker-compose exec namenode hdfs dfs -ls /agriculture/ml_training/2024*

# Step 2: Read the first 20 lines (Using Select-Object)
# Note: The file name is different for each one based on the date and time
docker-compose exec namenode hdfs dfs -cat /agriculture/ml_training/20251224/data_154815.json | Select-Object -First 20
```

**Git Bash / Linux / Mac:**
```bash
docker-compose exec namenode hdfs dfs -cat /agriculture/ml_training/20251224/data_154815.json | head -n 20
```

---

## 💻 How to Access the Data (Code)

### A. Accessing MongoDB (Python)

```python
from pymongo import MongoClient

client = MongoClient("mongodb://admin:admin123@localhost:27017/")
db = client["agriculture"]

# Get latest alerts
alerts = db.disease_records.find({"status": "active_infection"})
for alert in alerts:
    print(f"Risk in Field {alert['field_id']}: {alert['disease']}")
```

### B. Accessing HDFS (Spark / PySpark)

This is how your **Batch Processing Jobs** will read data for recommendations.

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("AgriAnalytics").getOrCreate()

# Read all historical data
# Spark automatically handles the /YYYYMMDD/ partitions!
df = spark.read.json("hdfs://namenode:9000/agriculture/ml_training/*/*")

# Analyze: Find average moisture per field
df.groupBy("field_id").avg("readings.moisture").show()
```

---

## 🚀 Expected Output for Your App

When your system is running, the Farmer's App will receive:

1.  **Alert (Push Notification)**:
    *   *Trigger*: MongoDB update in `disease_records`.
    *   *Message*: "⚠️ Early Blight risk detected in North Field."
    
2.  **Recommendation (Dashboard Card)**:
    *   *Trigger*: Spark Job output to `recommendations` collection.
    *   *Message*: "📉 Nitrogen levels are low (`42 mg/kg`). Recommended: Apply urea fertilizer by Friday."
