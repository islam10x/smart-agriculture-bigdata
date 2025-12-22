db = db.getSiblingDB('agriculture');

// Create collections
db.createCollection('sensor_data');
db.createCollection('disease_records');
db.createCollection('weather_data');
db.createCollection('alerts');
db.createCollection('analytics_results');

// Create indexes for sensor_data
db.sensor_data.createIndex({ "timestamp": -1 });
db.sensor_data.createIndex({ "sensor_id": 1, "timestamp": -1 });
db.sensor_data.createIndex({ "location.field_id": 1 });
db.sensor_data.createIndex({ "sensor_type": 1 });

// Create indexes for disease_records
db.disease_records.createIndex({ "detection_date": -1 });
db.disease_records.createIndex({ "field_id": 1 });
db.disease_records.createIndex({ "plant_type": 1 });
db.disease_records.createIndex({ "disease": 1 });
db.disease_records.createIndex({ "severity": 1 });

// Create indexes for alerts
db.alerts.createIndex({ "created_at": -1 });
db.alerts.createIndex({ "status": 1 });
db.alerts.createIndex({ "field_id": 1 });

print("MongoDB initialization completed successfully");
