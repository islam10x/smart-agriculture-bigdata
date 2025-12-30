# spark/batch_jobs/disease_frequency_analysis.py
"""
Disease Frequency Analysis Job
Analyzes disease patterns and generates statistics
"""

from pyspark.sql import SparkSession, functions as F
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiseaseFrequencyAnalysis:
    def __init__(self, spark, mongo_uri, mongo_db):
        self.spark = spark
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = MongoClient(mongo_uri)
        self.db = self.client[mongo_db]
    
    def run(self, lookback_days=30):
        """
        Analyze disease patterns over lookback period
        
        Args:
            lookback_days: number of days to analyze
        """
        logger.info(f"Starting disease frequency analysis ({lookback_days} days)")
        
        try:
            # Read disease records directly from MongoDB (exclude _id)
            disease_docs = list(self.db['disease_records'].find({}, {'_id': 0}))
            
            if not disease_docs:
                logger.warning("No disease records found")
                return True
            
            logger.info(f"✓ Loaded {len(disease_docs)} disease records")
            
            # Convert to Spark DataFrame
            df = self.spark.createDataFrame(disease_docs)
            
            # Parse timestamp if needed
            df = df.withColumn(
                "timestamp_parsed",
                F.when(
                    F.col("detection_date").cast("string").rlike("\\d{4}-\\d{2}-\\d{2}"),
                    F.to_timestamp(F.col("detection_date"), "yyyy-MM-dd HH:mm:ss")
                ).otherwise(F.col("detection_date"))
            )
            
            # Extract date
            df = df.withColumn(
                "date_only",
                F.to_date(F.col("timestamp_parsed"))
            )
            
            # Extract month
            df = df.withColumn("month", F.month(F.col("timestamp_parsed")))
            
            # Analysis 1: Disease frequency by type and field
            logger.info("Computing disease by field...")
            disease_by_field = df.groupBy("disease", "field_id").agg(
                F.count("*").alias("occurrence_count"),
                F.avg("severity").alias("avg_severity"),
                F.max("severity").alias("max_severity"),
                F.min(F.col("timestamp_parsed")).alias("first_detected"),
                F.max(F.col("timestamp_parsed")).alias("last_detected")
            ).collect()
            
            # Analysis 2: Seasonal distribution
            logger.info("Computing seasonal distribution...")
            disease_by_season = df.groupBy("disease", "season").agg(
                F.count("*").alias("count"),
                F.avg("severity").alias("avg_severity")
            ).collect()
            
            # Analysis 3: Monthly distribution
            logger.info("Computing monthly distribution...")
            disease_by_month = df.groupBy("disease", "month").agg(
                F.count("*").alias("count"),
                F.avg("severity").alias("avg_severity"),
                F.max("severity").alias("max_severity")
            ).collect()
            
            # Analysis 4: Overall statistics
            logger.info("Computing overall statistics...")
            overall_stats = df.agg(
                F.count("*").alias("total_records"),
                F.avg("severity").alias("avg_severity"),
                F.max("severity").alias("max_severity"),
                F.min("severity").alias("min_severity"),
                F.countDistinct("disease").alias("unique_diseases"),
                F.countDistinct("field_id").alias("affected_fields")
            ).collect()[0]
            
            # Convert results to dicts
            disease_field_list = [row.asDict() for row in disease_by_field]
            disease_season_list = [row.asDict() for row in disease_by_season]
            disease_month_list = [row.asDict() for row in disease_by_month]
            overall_dict = overall_stats.asDict()
            
            # Create comprehensive report
            report = {
                'timestamp': datetime.now(timezone.utc),
                'lookback_days': lookback_days,
                'overall_statistics': {
                    'total_records': int(overall_dict['total_records']),
                    'avg_severity': float(overall_dict['avg_severity']) if overall_dict['avg_severity'] else 0,
                    'max_severity': float(overall_dict['max_severity']) if overall_dict['max_severity'] else 0,
                    'min_severity': float(overall_dict['min_severity']) if overall_dict['min_severity'] else 0,
                    'unique_diseases': int(overall_dict['unique_diseases']),
                    'affected_fields': int(overall_dict['affected_fields'])
                },
                'disease_by_field': disease_field_list,
                'disease_by_season': disease_season_list,
                'disease_by_month': disease_month_list,
                'top_diseases': sorted(
                    disease_field_list,
                    key=lambda x: x['occurrence_count'],
                    reverse=True
                )[:5]
            }
            
            # Clean datetime objects for MongoDB
            for key in report:
                if key == 'timestamp':
                    report[key] = report[key].isoformat()
            
            # Write to MongoDB
            self.db['disease_statistics'].delete_many({})
            self.db['disease_statistics'].insert_one(report)
            
            logger.info(f"✓ Disease analysis complete")
            logger.info(f"  Total diseases: {report['overall_statistics']['unique_diseases']}")
            logger.info(f"  Affected fields: {report['overall_statistics']['affected_fields']}")
            logger.info(f"  Avg severity: {report['overall_statistics']['avg_severity']:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Analysis failed: {e}", exc_info=True)
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
        .appName("DiseaseFrequencyAnalysis") \
        .getOrCreate()
    
    try:
        analyzer = DiseaseFrequencyAnalysis(
            spark=spark,
            mongo_uri=mongo_uri,
            mongo_db=mongo_db
        )
        
        success = analyzer.run(lookback_days=30)
        return 0 if success else 1
        
    finally:
        spark.stop()


if __name__ == "__main__":
    exit(main())