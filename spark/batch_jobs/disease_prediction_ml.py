"""
Disease Prediction ML with LLM-Powered Recommendations
Uses Claude API to generate intelligent, context-aware recommendations
"""

from pyspark.sql import SparkSession, functions as F
from pyspark.ml import Pipeline, PipelineModel
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.evaluation import BinaryClassificationEvaluator
from pyspark.ml.linalg import SparseVector, DenseVector
from datetime import datetime, timezone
from pymongo import MongoClient
import anthropic
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMRecommendationEngine:
    """Generate recommendations using Claude AI"""
    
    def __init__(self, api_key=None):
        """Initialize Claude client"""
        if not api_key:
            # Try to get from environment variable
            api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not provided or set in environment")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        logger.info("✓ Claude AI client initialized")
    
    def get_recommendation(self, field_data, risk_score):
        """
        Send field data and risk score to Claude for intelligent recommendation
        
        Args:
            field_data: Dict with field_id, date, temp, humidity, moisture, rainfall, nitrogen
            risk_score: Float 0-1 indicating disease risk
        
        Returns:
            Dict with LLM-generated recommendation
        """
        
        # Build context for Claude
        prompt = f"""
You are an agricultural disease expert. Analyze this field data and disease risk prediction, then provide actionable recommendations.

FIELD DATA:
- Field ID: {field_data.get('field_id', 'Unknown')}
- Date: {field_data.get('date', 'Unknown')}
- Temperature: {field_data.get('temp_avg', 0):.1f}°C
- Humidity: {field_data.get('humidity_avg', 0):.1f}%
- Soil Moisture: {field_data.get('moisture_avg', 0):.1f}%
- Recent Rainfall: {field_data.get('rainfall_total', 0):.1f}mm
- Nitrogen Level: {field_data.get('nitrogen_avg', 0):.1f}ppm

DISEASE RISK PREDICTION:
- Risk Score: {risk_score:.3f} (0 = no risk, 1 = high risk)
- Risk Level: {"LOW" if risk_score < 0.3 else "MEDIUM" if risk_score < 0.6 else "HIGH"}

Based on this data, provide:
1. What disease(s) are likely occurring
2. Why the conditions favor this disease
3. Immediate actions to take (3-5 specific steps)
4. Treatment options (chemical and organic)
5. Preventive measures for future
6. Monitoring frequency

Format as JSON with keys: likely_disease, risk_explanation, immediate_actions (list), treatment_options (list), preventive_measures (list), monitoring_frequency_hours

Keep recommendations practical and farm-friendly."""
        
        try:
            # Call Claude API with correct model name
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract response
            response_text = message.content[0].text
            
            # Parse JSON response
            import json
            try:
                # Try to extract JSON from response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    recommendation = json.loads(json_str)
                else:
                    # Fallback if JSON not properly formatted
                    recommendation = {
                        'likely_disease': 'Disease detected',
                        'risk_explanation': response_text,
                        'immediate_actions': ['Monitor field closely'],
                        'treatment_options': ['Apply broad-spectrum fungicide'],
                        'preventive_measures': ['Improve air circulation'],
                        'monitoring_frequency_hours': 24
                    }
            except json.JSONDecodeError:
                logger.warning("Could not parse LLM response as JSON, using fallback")
                recommendation = {
                    'likely_disease': 'Disease detected',
                    'risk_explanation': response_text,
                    'immediate_actions': ['Monitor field closely'],
                    'treatment_options': ['Consult local agronomist'],
                    'preventive_measures': ['Check weather forecasts'],
                    'monitoring_frequency_hours': 24
                }
            
            return recommendation
            
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return {
                'likely_disease': 'API Error',
                'risk_explanation': f'Could not reach Claude API: {str(e)}',
                'immediate_actions': ['Check API key', 'Verify internet connection'],
                'treatment_options': [],
                'preventive_measures': [],
                'monitoring_frequency_hours': 24,
                'error': True
            }


class DiseasePredictionML:
    def __init__(self, spark, mongo_uri, mongo_db, claude_api_key=None, model_path=None):
        self.spark = spark
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = MongoClient(mongo_uri)
        self.db = self.client[mongo_db]
        
        # Use provided model_path or default to persistent location
        if model_path:
            self.model_path = model_path
        else:
            self.model_path = "/opt/spark/ml/disease_prediction_model"
        
        logger.info(f"Model path: {self.model_path}")
        
        # Initialize LLM engine
        try:
            self.llm_engine = LLMRecommendationEngine(api_key=claude_api_key)
        except ValueError as e:
            logger.error(f"Could not initialize Claude: {e}")
            logger.warning("Will continue with fallback recommendations")
            self.llm_engine = None
    
    def prepare_training_data(self):
        """Join sensor + disease data for ML training"""
        logger.info("Preparing training data...")
        
        try:
            sensor_docs = list(self.db['daily_sensor_summary'].find({}, {'_id': 0}))
            if not sensor_docs:
                logger.warning("No sensor data found")
                return None
            
            logger.info(f"✓ Loaded {len(sensor_docs)} sensor summaries")
            
            for doc in sensor_docs:
                if 'record_count' in doc and hasattr(doc['record_count'], 'real'):
                    doc['record_count'] = int(doc['record_count'])
            
            sensor_df = self.spark.createDataFrame(sensor_docs)
            logger.info(f"✓ Sensor records: {sensor_df.count()}")
            
            disease_docs = list(self.db['disease_records'].find({}, {'_id': 0}))
            if not disease_docs:
                logger.warning("No disease records found - using negative labels")
                disease_df = sensor_df.select("field_id", "date").distinct().withColumn("has_disease", F.lit(0))
            else:
                disease_df = self.spark.createDataFrame(disease_docs)
                logger.info(f"✓ Loaded {disease_df.count()} disease records")
                
                disease_df = disease_df.withColumn(
                    "disease_date",
                    F.to_date(F.col("detection_date"))
                ).select("field_id", "disease_date").distinct().withColumn("has_disease", F.lit(1))
            
            training_data = sensor_df.join(
                disease_df,
                (sensor_df.field_id == disease_df.field_id) &
                (sensor_df.date == disease_df.disease_date),
                "left"
            ).fillna(0, subset=['has_disease'])
            
            logger.info(f"✓ Prepared {training_data.count()} training records")
            return training_data
            
        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return None
    
    def train_model(self, training_data):
        """Train Logistic Regression model"""
        logger.info("Training ML model...")
        
        try:
            feature_columns = [
                'temp_avg', 'humidity_avg', 'moisture_avg',
                'rainfall_total', 'nitrogen_avg'
            ]
            
            available_columns = [col for col in feature_columns if col in training_data.columns]
            logger.info(f"Using features: {available_columns}")
            
            if not available_columns:
                logger.error("No feature columns found in data")
                return None
            
            training_clean = training_data.select(available_columns + ['has_disease'])
            count_before = training_clean.count()
            logger.info(f"Records with selected features: {count_before}")
            
            has_nulls = False
            for col in available_columns:
                null_count = training_clean.filter(F.col(col).isNull()).count()
                if null_count > 0:
                    logger.warning(f"  {col}: {null_count} nulls present")
                    has_nulls = True
            
            if has_nulls:
                training_clean = training_clean.dropna()
                clean_count = training_clean.count()
                logger.info(f"Removed {count_before - clean_count} rows with nulls")
            else:
                clean_count = count_before
                logger.info("✓ No nulls found - data is clean")
            
            if clean_count == 0:
                logger.error("✗ No clean training data")
                return None
            
            logger.info(f"✓ Clean training records: {clean_count}")
            
            assembler = VectorAssembler(
                inputCols=available_columns,
                outputCol="features",
                handleInvalid="skip"
            )
            
            scaler = StandardScaler(
                inputCol="features",
                outputCol="scaled_features",
                withMean=True,
                withStd=True
            )
            
            lr = LogisticRegression(
                featuresCol="scaled_features",
                labelCol="has_disease",
                maxIter=100,
                regParam=0.01,
                elasticNetParam=0.2
            )
            
            pipeline = Pipeline(stages=[assembler, scaler, lr])
            
            train_data, test_data = training_clean.randomSplit([0.8, 0.2], seed=42)
            train_count = train_data.count()
            test_count = test_data.count()
            
            logger.info(f"Training: {train_count}, Testing: {test_count}")
            
            if train_count == 0 or test_count == 0:
                logger.error("✗ Train/test split resulted in empty data")
                return None
            
            model = pipeline.fit(train_data)
            
            predictions = model.transform(test_data)
            evaluator = BinaryClassificationEvaluator(
                labelCol="has_disease",
                rawPredictionCol="rawPrediction"
            )
            auc = evaluator.evaluate(predictions)
            logger.info(f"✓ Model AUC: {auc:.4f}")
            
            # Save model to persistent location
            try:
                # Create directory if it doesn't exist
                model_dir = os.path.dirname(self.model_path)
                os.makedirs(model_dir, exist_ok=True)
                
                model.write().overwrite().save(self.model_path)
                logger.info(f"✓ Model saved to {self.model_path}")
            except Exception as e:
                logger.warning(f"Could not save model: {e}")
            
            return model
            
        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            return None
    
    def load_model(self):
        """Load existing model from persistent storage"""
        try:
            if os.path.exists(self.model_path):
                logger.info(f"Loading model from {self.model_path}...")
                model = PipelineModel.load(self.model_path)
                logger.info("✓ Model loaded successfully")
                return model
            else:
                logger.info(f"No model found at {self.model_path}")
                return None
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
            return None
    
    def generate_predictions(self, model):
        """Generate predictions and send to Claude for recommendations"""
        logger.info("Generating predictions and fetching AI recommendations...")
        
        try:
            latest_sensors_docs = list(self.db['daily_sensor_summary'].find({}, {'_id': 0}).sort("date", -1).limit(5))
            if not latest_sensors_docs:
                logger.warning("No sensor data for predictions")
                return False
            
            logger.info(f"✓ Retrieved {len(latest_sensors_docs)} latest sensor records")
            
            latest_sensors = self.spark.createDataFrame(latest_sensors_docs)
            
            if latest_sensors.count() == 0:
                logger.warning("No sensor data for predictions")
                return False
            
            logger.info(f"✓ Generating predictions for {latest_sensors.count()} records")
            
            # Generate predictions
            predictions = model.transform(latest_sensors)
            
            # Extract probability
            def extract_probability(prob_vector):
                if prob_vector is None:
                    return 0.0
                if isinstance(prob_vector, (SparseVector, DenseVector)):
                    return float(prob_vector[1])
                return float(prob_vector[1]) if len(prob_vector) > 1 else 0.0
            
            from pyspark.sql.types import DoubleType
            extract_prob_udf = F.udf(extract_probability, DoubleType())
            
            predictions_with_risk = predictions.withColumn(
                "risk_score",
                extract_prob_udf(F.col("probability"))
            )
            
            risk_scores = predictions_with_risk.select(
                F.col("field_id"),
                F.col("date").alias("prediction_date"),
                F.col("temp_avg"),
                F.col("humidity_avg"),
                F.col("moisture_avg"),
                F.col("rainfall_total"),
                F.col("nitrogen_avg"),
                F.col("risk_score"),
                F.col("prediction").alias("disease_present")
            ).collect()
            
            logger.info(f"✓ Generated {len(risk_scores)} predictions")
            
            # Generate recommendations using Claude
            recommendations = []
            claude_success_count = 0
            claude_error_count = 0
            
            for i, row in enumerate(risk_scores, 1):
                field_id = row.field_id
                risk = float(row.risk_score) if row.risk_score else 0
                
                # Prepare field data for Claude
                field_data = {
                    'field_id': field_id,
                    'date': str(row.prediction_date) if row.prediction_date else None,
                    'temp_avg': float(row.temp_avg) if row.temp_avg else 0,
                    'humidity_avg': float(row.humidity_avg) if row.humidity_avg else 0,
                    'moisture_avg': float(row.moisture_avg) if row.moisture_avg else 0,
                    'rainfall_total': float(row.rainfall_total) if row.rainfall_total else 0,
                    'nitrogen_avg': float(row.nitrogen_avg) if row.nitrogen_avg else 0
                }
                
                # Get recommendation from Claude or fallback
                if self.llm_engine:
                    try:
                        logger.info(f"  [{i}/{len(risk_scores)}] Getting AI recommendation for {field_id}...")
                        llm_rec = self.llm_engine.get_recommendation(field_data, risk)
                        
                        # Check if recommendation has error
                        if llm_rec.get('error'):
                            claude_error_count += 1
                            logger.warning(f"    ⚠️  Claude error: {llm_rec.get('risk_explanation', 'Unknown error')}")
                        else:
                            claude_success_count += 1
                            logger.info(f"    ✓ Got recommendation: {llm_rec.get('likely_disease', 'Unknown')}")
                    except Exception as e:
                        logger.error(f"    ❌ Exception calling Claude: {e}")
                        claude_error_count += 1
                        llm_rec = self._get_fallback_recommendation(risk)
                else:
                    logger.warning(f"  [{i}/{len(risk_scores)}] LLM engine not initialized, using fallback...")
                    llm_rec = self._get_fallback_recommendation(risk)
                    claude_error_count += 1
                
                # Combine ML prediction with recommendation
                rec = {
                    "field_id": field_id,
                    "prediction_date": str(row.prediction_date) if row.prediction_date else None,
                    "risk_score": risk,
                    "confidence": "low" if risk < 0.3 else "medium" if risk < 0.6 else "high",
                    "model_prediction": {
                        "temp_avg": field_data['temp_avg'],
                        "humidity_avg": field_data['humidity_avg'],
                        "moisture_avg": field_data['moisture_avg'],
                        "rainfall_total": field_data['rainfall_total'],
                        "nitrogen_avg": field_data['nitrogen_avg']
                    },
                    "ai_recommendation": llm_rec,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                recommendations.append(rec)
            
            # Write to MongoDB
            if recommendations:
                self.db['recommendations'].delete_many({})
                self.db['recommendations'].insert_many(recommendations)
                logger.info(f"✓ Stored {len(recommendations)} recommendations")
                logger.info(f"  ✓ Claude AI: {claude_success_count} successful")
                if claude_error_count > 0:
                    logger.warning(f"  ⚠️  Fallback used: {claude_error_count} times")
            
            return True
            
        except Exception as e:
            logger.error(f"Prediction generation failed: {e}", exc_info=True)
            return False
    
    def _get_fallback_recommendation(self, risk_score):
        """Fallback recommendation when Claude is not available"""
        if risk_score < 0.3:
            return {
                'likely_disease': 'Low risk - Normal conditions',
                'immediate_actions': ['Continue regular monitoring'],
                'treatment_options': ['No treatment needed'],
                'preventive_measures': ['Maintain good field hygiene']
            }
        elif risk_score < 0.6:
            return {
                'likely_disease': 'Medium risk - Early intervention recommended',
                'immediate_actions': [
                    'Increase field monitoring to 2-3 times per week',
                    'Improve air circulation',
                    'Apply preventive fungicide'
                ],
                'treatment_options': ['Broad-spectrum fungicide', 'Neem oil spray'],
                'preventive_measures': ['Adjust irrigation schedule', 'Remove infected leaves']
            }
        else:
            return {
                'likely_disease': 'High risk - Immediate action required',
                'immediate_actions': [
                    'Apply treatment fungicide today',
                    'Inspect field daily',
                    'Remove heavily infected plants',
                    'Isolate affected area'
                ],
                'treatment_options': ['Systemic fungicide', 'Copper-based treatment'],
                'preventive_measures': ['Increase monitoring', 'Adjust irrigation']
            }
    
    def run(self, retrain=False):
        """Run prediction pipeline"""
        logger.info("=" * 70)
        logger.info("DISEASE PREDICTION ML WITH LLM RECOMMENDATIONS")
        logger.info("=" * 70)
        
        try:
            # Try to load existing model first (unless retraining is forced)
            model = None
            if not retrain:
                model = self.load_model()
            
            # Train new model if needed
            if model is None:
                logger.info("Training new model...")
                training_data = self.prepare_training_data()
                if training_data is None:
                    logger.error("✗ Could not prepare training data")
                    return False
                
                model = self.train_model(training_data)
                if model is None:
                    logger.error("✗ Could not train model")
                    return False
            
            # Generate predictions using the model
            success = self.generate_predictions(model)
            
            if success:
                logger.info("=" * 70)
                logger.info("✓ ML JOB COMPLETED SUCCESSFULLY")
                logger.info("=" * 70)
            
            return success
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return False
        finally:
            self.client.close()


def main():
    """Entry point for Spark job"""
    
    import sys
    
    mongo_host = 'mongodb'
    mongo_port = 27017
    mongo_user = 'admin'
    mongo_password = 'admin123'
    mongo_uri = f'mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/'
    mongo_db = 'agriculture'
    
    # Get Claude API key from environment
    claude_api_key = os.getenv('ANTHROPIC_API_KEY')
    
    # Check for --retrain flag in command line arguments
    retrain = '--retrain' in sys.argv
    
    logger.info(f"MongoDB URI: {mongo_uri}")
    logger.info(f"Database: {mongo_db}")
    logger.info(f"Retrain mode: {retrain}")
    if claude_api_key:
        logger.info("✓ Claude API key found in environment")
    else:
        logger.warning("⚠️  Claude API key not found - will use fallback recommendations")
    
    spark = SparkSession.builder \
        .appName("DiseasePredictionML") \
        .getOrCreate()
    
    try:
        predictor = DiseasePredictionML(
            spark=spark,
            mongo_uri=mongo_uri,
            mongo_db=mongo_db,
            claude_api_key=claude_api_key
        )
        
        success = predictor.run(retrain=retrain)
        return 0 if success else 1
        
    finally:
        spark.stop()


if __name__ == "__main__":
    exit(main())