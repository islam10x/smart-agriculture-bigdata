"""
One-time model training script
Run this separately to train and save the model to /opt/spark/ml/
"""

from pyspark.sql import SparkSession
import sys
import os

# Add parent directory to path to import the ML module
sys.path.insert(0, '/opt/spark-apps')

from disease_prediction_ml import DiseasePredictionML
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Train and save the disease prediction model"""
    
    logger.info("\n" + "="*70)
    logger.info("🎓 MODEL TRAINING MODE")
    logger.info("="*70)
    
    mongo_host = 'mongodb'
    mongo_port = 27017
    mongo_user = 'admin'
    mongo_password = 'admin123'
    mongo_uri = f'mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/'
    mongo_db = 'agriculture'
    
    claude_api_key = os.getenv('ANTHROPIC_API_KEY')
    
    logger.info(f"MongoDB: {mongo_uri}")
    logger.info(f"Database: {mongo_db}")
    logger.info(f"Model will be saved to: /opt/spark/ml/disease_prediction_model")
    
    spark = SparkSession.builder \
        .appName("ModelTraining") \
        .getOrCreate()
    
    try:
        predictor = DiseasePredictionML(
            spark=spark,
            mongo_uri=mongo_uri,
            mongo_db=mongo_db,
            claude_api_key=claude_api_key,
            model_path="/opt/spark/ml/disease_prediction_model"
        )
        
        # Force training
        logger.info("\n🔄 Starting model training...")
        success = predictor.run(retrain=True)
        
        if success:
            logger.info("\n" + "="*70)
            logger.info("✅ MODEL TRAINED AND SAVED SUCCESSFULLY")
            logger.info("="*70)
            logger.info("The model is now available at: /opt/spark/ml/disease_prediction_model")
            logger.info("Future runs will use this pre-trained model.")
            logger.info("="*70 + "\n")
        else:
            logger.error("\n❌ MODEL TRAINING FAILED")
        
        return 0 if success else 1
        
    finally:
        spark.stop()


if __name__ == "__main__":
    exit(main())