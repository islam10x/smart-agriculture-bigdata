# spark/batch_jobs/daily_sensor_aggregation.py
"""
Daily Sensor Aggregation Job
Computes daily summary statistics for all sensor readings
"""

from pyspark.sql import SparkSession, functions as F
from datetime import datetime, timedelta
from pymongo import MongoClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DailySensorAggregation:
    def __init__(self, spark, mongo_uri, mongo_db):
        self.spark = spark
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        # Use PyMongo for writes, Spark for reads only with proper URI
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[mongo_db]
    
    def run(self, target_date=None):
        """
        Aggregate sensor data for a specific date
        
        Args:
            target_date: datetime object (default: yesterday)
        """
        if not target_date:
            target_date = datetime.now() - timedelta(days=1)
        
        logger.info(f"Starting sensor aggregation for {target_date.date()}")
        
        try:
            # Read sensor data directly from MongoDB using PyMongo (more reliable)
            # Filter for target date
            date_str = target_date.strftime('%Y-%m-%d')
            next_date_str = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            sensor_docs = list(self.db['sensor_data'].find({
                "timestamp": {
                    "$gte": f"{date_str} 00:00:00",
                    "$lt": f"{next_date_str} 00:00:00"
                }
            }))
            
            if not sensor_docs:
                logger.warning(f"No sensor data found for {target_date.date()}")
                return True
            
            logger.info(f"✓ Loaded {len(sensor_docs)} sensor records")
            
            # Convert to Spark DataFrame
            df = self.spark.createDataFrame(sensor_docs)
            
            # Aggregate by field and sensor type
            aggregations = df.groupBy("field_id", "sensor_type").agg(
                # Temperature metrics
                F.min("readings.temperature").alias("temp_min"),
                F.max("readings.temperature").alias("temp_max"),
                F.avg("readings.temperature").alias("temp_avg"),
                F.stddev("readings.temperature").alias("temp_std"),
                
                # Humidity metrics
                F.min("readings.humidity").alias("humidity_min"),
                F.max("readings.humidity").alias("humidity_max"),
                F.avg("readings.humidity").alias("humidity_avg"),
                F.stddev("readings.humidity").alias("humidity_std"),
                
                # Soil moisture (for soil sensors)
                F.avg("readings.moisture").alias("moisture_avg"),
                F.min("readings.moisture").alias("moisture_min"),
                F.max("readings.moisture").alias("moisture_max"),
                
                # NPK nutrients
                F.avg("readings.nitrogen").alias("nitrogen_avg"),
                F.avg("readings.phosphorus").alias("phosphorus_avg"),
                F.avg("readings.potassium").alias("potassium_avg"),
                
                # Rain and wind
                F.sum("weather_context.rainfall").alias("rainfall_total"),
                F.avg("weather_context.wind_speed").alias("wind_speed_avg"),
                F.max("weather_context.wind_speed").alias("wind_speed_max"),
                
                # Data quality
                F.count("*").alias("record_count")
            ).withColumn(
                "aggregation_date", F.lit(target_date)
            ).withColumn(
                "created_at", F.current_timestamp()
            )
            
            # Convert to list of dicts for MongoDB insert
            records = aggregations.toPandas().to_dict('records')
            
            # Clean NaN values and convert dates
            clean_records = []
            for record in records:
                clean_record = {}
                for k, v in record.items():
                    if str(v) == 'nan':
                        clean_record[k] = None
                    elif hasattr(v, 'isoformat'):  # datetime object
                        clean_record[k] = v.isoformat()
                    else:
                        clean_record[k] = v
                clean_records.append(clean_record)
            
            # Write to MongoDB using PyMongo (more reliable)
            if clean_records:
                self.db['daily_sensor_summary'].insert_many(clean_records)
                logger.info(f"✓ Inserted {len(clean_records)} daily summaries")
                return True
            else:
                logger.warning("No records to insert")
                return False
            
        except Exception as e:
            logger.error(f"✗ Aggregation failed: {e}", exc_info=True)
            return False
        finally:
            self.client.close()


def main():
    """Entry point for Spark job"""
    
    # MongoDB configuration
    mongo_host = 'mongodb'  # Docker service name
    mongo_port = 27017
    mongo_user = 'admin'
    mongo_password = 'admin123'
    mongo_uri = f'mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/'
    mongo_db = 'agriculture'
    
    logger.info(f"MongoDB URI: {mongo_uri}")
    logger.info(f"Database: {mongo_db}")
    
    spark = SparkSession.builder \
        .appName("DailySensorAggregation") \
        .getOrCreate()
    
    try:
        aggregator = DailySensorAggregation(
            spark=spark,
            mongo_uri=mongo_uri,
            mongo_db=mongo_db
        )
        
        success = aggregator.run()
        return 0 if success else 1
        
    finally:
        spark.stop()


if __name__ == "__main__":
    exit(main())