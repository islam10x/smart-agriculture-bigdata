# spark/batch_jobs/data_quality_cleaner.py
"""
Data Quality Cleaner
Fixes null values in sensor summaries so ML and correlation jobs work
"""

from pyspark.sql import SparkSession, functions as F
from datetime import datetime, timezone
from pymongo import MongoClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataQualityCleaner:
    def __init__(self, spark, mongo_uri, mongo_db):
        self.spark = spark
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = MongoClient(mongo_uri)
        self.db = self.client[mongo_db]
    
    def run(self):
        """
        Clean and impute null values in daily_sensor_summary
        """
        logger.info("=" * 70)
        logger.info("STARTING DATA QUALITY CLEANING")
        logger.info("=" * 70)
        
        try:
            # Read sensor summaries (exclude _id)
            sensor_docs = list(self.db['daily_sensor_summary'].find({}, {'_id': 0}))
            
            if not sensor_docs:
                logger.warning("No sensor data found")
                return True
            
            logger.info(f"✓ Loaded {len(sensor_docs)} sensor records from MongoDB")
            
            # Convert MongoDB Int64 types to native Python types
            for doc in sensor_docs:
                if 'reading_count' in doc and hasattr(doc['reading_count'], 'real'):
                    doc['reading_count'] = int(doc['reading_count'])
            
            # Convert to Spark DataFrame
            df = self.spark.createDataFrame(sensor_docs)
            original_count = df.count()
            
            logger.info(f"Original record count: {original_count}")
            logger.info("Original null counts by column:")
            
            # Show null counts for feature columns
            feature_columns = [
                'temp_avg', 'humidity_avg', 'moisture_avg',
                'rainfall_total', 'nitrogen_avg', 'phosphorus_avg', 'potassium_avg'
            ]
            
            null_summary = {}
            for col in feature_columns:
                if col in df.columns:
                    null_count = df.filter(F.col(col).isNull()).count()
                    null_summary[col] = null_count
                    logger.info(f"  {col}: {null_count} nulls")
            
            # Step 1: Fill nulls with mean values per field_id and sensor_type
            logger.info("\n[Step 1] Filling nulls with field + sensor type means...")
            
            for col in feature_columns:
                if col in df.columns:
                    # Calculate mean by field_id
                    field_means = df.groupBy('field_id').agg(
                        F.avg(F.col(col)).alias(f'{col}_field_mean')
                    )
                    
                    df = df.join(field_means, 'field_id', 'left')
                    
                    # Fill with field mean if available
                    df = df.withColumn(
                        col,
                        F.when(
                            F.col(col).isNull(),
                            F.col(f'{col}_field_mean')
                        ).otherwise(F.col(col))
                    ).drop(f'{col}_field_mean')
            
            logger.info("Filled with field means")
            
            # Step 2: Fill remaining nulls with overall column mean
            logger.info("[Step 2] Filling remaining nulls with overall column means...")
            
            for col in feature_columns:
                if col in df.columns:
                    # Get overall mean
                    overall_mean = df.agg(F.avg(col)).collect()[0][0]
                    
                    if overall_mean is not None:
                        df = df.withColumn(
                            col,
                            F.when(
                                F.col(col).isNull(),
                                F.lit(overall_mean)
                            ).otherwise(F.col(col))
                        )
                        logger.info(f"  {col}: overall mean = {overall_mean:.2f}")
            
            # Step 3: Verify no nulls remain in feature columns
            logger.info("\n[Step 3] Verifying data quality...")
            
            remaining_nulls = False
            for col in feature_columns:
                if col in df.columns:
                    null_count = df.filter(F.col(col).isNull()).count()
                    if null_count > 0:
                        logger.warning(f"  {col}: {null_count} nulls STILL PRESENT")
                        remaining_nulls = True
                    else:
                        logger.info(f"  {col}: 0 nulls ✓")
            
            # Step 4: If any nulls remain, drop those rows as last resort
            if remaining_nulls:
                logger.info("\n[Step 4] Dropping rows with remaining nulls...")
                df_clean = df.dropna(subset=feature_columns)
                clean_count = df_clean.count()
                removed_count = original_count - clean_count
                logger.warning(f"Removed {removed_count} rows with remaining nulls")
            else:
                df_clean = df
                clean_count = df.count()
                removed_count = 0
            
            logger.info(f"\n✓ Final clean record count: {clean_count}")
            logger.info(f"✓ Total removed: {removed_count} ({removed_count/original_count*100:.1f}%)")
            
            if clean_count == 0:
                logger.error("✗ No clean records remain - check data quality")
                return False
            
            # Convert back to MongoDB documents
            clean_docs = df_clean.toPandas().to_dict('records')
            
            # Clean datetime objects for MongoDB
            for doc in clean_docs:
                for key, val in doc.items():
                    if hasattr(val, 'isoformat'):
                        doc[key] = val.isoformat()
            
            # Replace old data with cleaned data
            logger.info("\nUpdating MongoDB with clean data...")
            self.db['daily_sensor_summary'].delete_many({})
            result = self.db['daily_sensor_summary'].insert_many(clean_docs)
            
            logger.info(f"✓ Inserted {len(result.inserted_ids)} clean records into daily_sensor_summary")
            
            # Create summary
            summary = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'original_count': original_count,
                'clean_count': clean_count,
                'removed_count': removed_count,
                'removal_percentage': round((removed_count / original_count * 100), 2) if original_count > 0 else 0,
                'status': 'completed',
                'null_summary': null_summary
            }
            
            # Store summary
            self.db['data_quality_report'].delete_many({})
            self.db['data_quality_report'].insert_one(summary)
            
            logger.info(f"\n📊 Data Quality Report:")
            logger.info(f"  Original records: {summary['original_count']}")
            logger.info(f"  Clean records: {summary['clean_count']}")
            logger.info(f"  Removed: {summary['removed_count']} ({summary['removal_percentage']}%)")
            logger.info("=" * 70)
            logger.info("✓ DATA QUALITY CLEANING COMPLETE - Ready for ML pipeline")
            logger.info("=" * 70)
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Cleaning failed: {e}", exc_info=True)
            logger.error("=" * 70)
            return False
        finally:
            self.client.close()


def main():
    """Entry point for Spark job"""
    
    mongo_host = 'mongodb'
    mongo_port = 27017
    mongo_user = 'admin'
    mongo_password = 'admin123'
    mongo_uri = f'mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/'
    mongo_db = 'agriculture'
    
    logger.info(f"MongoDB URI: {mongo_uri}")
    logger.info(f"Database: {mongo_db}")
    
    spark = SparkSession.builder \
        .appName("DataQualityCleaner") \
        .master("spark://spark-master:7077") \
        .config("spark.executor.memory", "1g") \
        .config("spark.executor.cores", "1") \
        .config("spark.cores.max", "6") \
        .config("spark.driver.memory", "1g") \
        .config("spark.network.timeout", "600s") \
        .config("spark.executor.heartbeatInterval", "30s") \
        .getOrCreate()
    
    try:
        cleaner = DataQualityCleaner(
            spark=spark,
            mongo_uri=mongo_uri,
            mongo_db=mongo_db
        )
        
        success = cleaner.run()
        return 0 if success else 1
        
    finally:
        spark.stop()


if __name__ == "__main__":
    exit(main())