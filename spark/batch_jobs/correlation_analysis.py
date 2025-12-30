# spark/batch_jobs/correlation_analysis.py
"""
Correlation Analysis Job
Analyzes correlations between environmental factors and disease
"""

from pyspark.sql import SparkSession, functions as F
from datetime import datetime, timezone
from pymongo import MongoClient
from scipy.stats import pearsonr, spearmanr
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CorrelationAnalysis:
    def __init__(self, spark, mongo_uri, mongo_db):
        self.spark = spark
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = MongoClient(mongo_uri)
        self.db = self.client[mongo_db]
    
    def run(self, lookback_days=90):
        """
        Analyze correlations between conditions and diseases
        
        Args:
            lookback_days: number of days to analyze
        """
        logger.info("=" * 70)
        logger.info("CORRELATION ANALYSIS JOB")
        logger.info("=" * 70)
        logger.info(f"Analyzing last {lookback_days} days")
        
        try:
            # Read sensor summaries - EXCLUDE _id
            sensor_docs = list(self.db['daily_sensor_summary'].find({}, {'_id': 0}))
            if not sensor_docs:
                logger.warning("No sensor data found")
                return True
            
            logger.info(f"✓ Loaded {len(sensor_docs)} sensor summaries")
            
            # Convert MongoDB Int64 types to native Python types
            for doc in sensor_docs:
                if 'reading_count' in doc and hasattr(doc['reading_count'], 'real'):
                    doc['reading_count'] = int(doc['reading_count'])
            
            sensor_df = self.spark.createDataFrame(sensor_docs)
            logger.info(f"✓ Sensor records: {sensor_df.count()}")
            
            # Read disease records - EXCLUDE _id
            disease_docs = list(self.db['disease_records'].find({}, {'_id': 0}))
            if not disease_docs:
                logger.warning("No disease records found - using all zeros")
                disease_daily = sensor_df.select("field_id", "date").distinct() \
                    .withColumn("has_disease", F.lit(0))
            else:
                disease_df = self.spark.createDataFrame(disease_docs)
                logger.info(f"✓ Loaded {disease_df.count()} disease records")
                
                # Create disease presence label
                disease_daily = disease_df.withColumn(
                    "disease_date",
                    F.to_date(F.col("detection_date"))
                ).groupBy("field_id", "disease_date").agg(
                    F.max("severity").alias("max_severity")
                ).withColumn(
                    "has_disease", F.lit(1)
                ).select("field_id", F.col("disease_date").alias("date"), "has_disease")
            
            # Join data
            combined = sensor_df.join(
                disease_daily,
                (sensor_df.field_id == disease_daily.field_id) &
                (sensor_df.date == disease_daily.date),
                "left"
            ).fillna(0, subset=['has_disease'])
            
            logger.info(f"Combined {combined.count()} records")
            
            # Select numeric columns for correlation
            feature_columns = [
                'temp_avg', 'humidity_avg', 'moisture_avg',
                'rainfall_total', 'nitrogen_avg', 'phosphorus_avg', 'potassium_avg'
            ]
            
            # Get available columns
            available_columns = [col for col in feature_columns if col in combined.columns]
            logger.info(f"Available features: {available_columns}")
            
            # Convert to Pandas for correlation calculation
            pdf = combined.select(available_columns + ['has_disease']).dropna().toPandas()
            
            logger.info(f"Computing correlations from {len(pdf)} records")
            
            if len(pdf) < 2:
                logger.warning("Not enough data for correlation analysis")
                return True
            
            # Calculate correlations
            correlations = []
            
            for feature in available_columns:
                try:
                    feature_data = pdf[feature].values
                    disease_data = pdf['has_disease'].values
                    
                    # Skip if constant
                    if np.std(feature_data) == 0 or np.std(disease_data) == 0:
                        continue
                    
                    # Pearson correlation
                    pearson_corr, pearson_p = pearsonr(feature_data, disease_data)
                    
                    # Spearman correlation
                    spearman_corr, spearman_p = spearmanr(feature_data, disease_data)
                    
                    # Convert numpy types to Python native types for MongoDB serialization
                    correlations.append({
                        'feature': feature,
                        'pearson_correlation': float(pearson_corr),
                        'pearson_pvalue': float(pearson_p),
                        'spearman_correlation': float(spearman_corr),
                        'spearman_pvalue': float(spearman_p),
                        'is_significant': bool(pearson_p < 0.05),  # Convert numpy.bool_ to Python bool
                        'interpretation': self._interpret_correlation(feature, pearson_corr)
                    })
                    
                except Exception as e:
                    logger.warning(f"Could not compute correlation for {feature}: {e}")
            
            # Sort by absolute correlation
            correlations.sort(
                key=lambda x: abs(x['pearson_correlation']),
                reverse=True
            )
            
            logger.info(f"Calculated {len(correlations)} correlations")
            
            # Create summary report
            significant_features = sum(1 for c in correlations if c['is_significant'])
            avg_corr = float(np.mean([c['pearson_correlation'] for c in correlations])) if correlations else 0.0
            
            report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'lookback_days': lookback_days,
                'total_records_analyzed': int(len(pdf)),
                'correlations': correlations,
                'top_risk_factors': [c['feature'] for c in correlations[:3]],
                'summary': {
                    'total_features': len(correlations),
                    'significant_features': significant_features,
                    'avg_correlation': avg_corr
                }
            }
            
            # Write to MongoDB
            logger.info("Writing correlation report to MongoDB...")
            self.db['correlations'].delete_many({})
            self.db['correlations'].insert_one(report)
            
            logger.info(f"✓ Correlation analysis complete")
            logger.info(f"  Total features analyzed: {len(correlations)}")
            logger.info(f"  Significant features: {significant_features}")
            logger.info(f"  Top risk factors: {report['top_risk_factors']}")
            logger.info(f"  Average correlation: {avg_corr:.4f}")
            
            logger.info("=" * 70)
            logger.info("✓ CORRELATION ANALYSIS COMPLETED SUCCESSFULLY")
            logger.info("=" * 70)
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Analysis failed: {e}", exc_info=True)
            logger.error("=" * 70)
            return False
        finally:
            self.client.close()
    
    def _interpret_correlation(self, feature, correlation):
        """Generate human-readable interpretation"""
        if abs(correlation) < 0.3:
            strength = "weak"
        elif abs(correlation) < 0.7:
            strength = "moderate"
        else:
            strength = "strong"
        
        direction = "increases" if correlation > 0 else "decreases"
        
        return f"{strength.capitalize()} - {direction} disease risk"


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
        .appName("CorrelationAnalysis") \
        .getOrCreate()
    
    try:
        analyzer = CorrelationAnalysis(
            spark=spark,
            mongo_uri=mongo_uri,
            mongo_db=mongo_db
        )
        
        success = analyzer.run(lookback_days=90)
        return 0 if success else 1
        
    finally:
        spark.stop()


if __name__ == "__main__":
    exit(main())