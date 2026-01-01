"""
Test script for Disease Prediction ML Model
Validates the saved PipelineModel at spark/ml_models/disease_prediction_model
"""

from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.types import StructType, StructField, DoubleType, StringType
from pyspark.ml.linalg import SparseVector, DenseVector
from pyspark.sql import functions as F
import os
import sys

def test_model():
    """Test the disease prediction model"""
    
    print("=" * 70)
    print("DISEASE PREDICTION MODEL TEST")
    print("=" * 70)
    
    # Check if model exists - use Docker container path
    local_model_path = "/opt/spark-models/disease_prediction_model"
    
    print(f"\n[1/5] Checking model path: {local_model_path}")
    
    if not os.path.exists(local_model_path):
        print(f"  ✗ Model not found at {local_model_path}")
        return False
    
    # Check model structure
    metadata_path = os.path.join(local_model_path, "metadata")
    stages_path = os.path.join(local_model_path, "stages")
    
    print(f"  ✓ Model directory exists")
    print(f"  ✓ Metadata: {'exists' if os.path.exists(metadata_path) else 'missing'}")
    print(f"  ✓ Stages: {'exists' if os.path.exists(stages_path) else 'missing'}")
    
    # List stages
    if os.path.exists(stages_path):
        stages = os.listdir(stages_path)
        print(f"  ✓ Pipeline stages ({len(stages)}):")
        for stage in sorted(stages):
            print(f"      - {stage}")
    
    # Initialize Spark
    print("\n[2/5] Initializing Spark session...")
    spark = SparkSession.builder \
        .appName("TestDiseaseModel") \
        .master("local[*]") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    print(f"  ✓ Spark version: {spark.version}")
    
    try:
        # Load the model
        print("\n[3/5] Loading PipelineModel...")
        model = PipelineModel.load(local_model_path)
        print(f"  ✓ Model loaded successfully")
        print(f"  ✓ Pipeline stages: {len(model.stages)}")
        
        for i, stage in enumerate(model.stages):
            print(f"      Stage {i}: {stage.__class__.__name__}")
        
        # Create test data
        print("\n[4/5] Creating test data with various scenarios...")
        
        # Define the schema matching the training features
        schema = StructType([
            StructField("field_id", StringType(), True),
            StructField("date", StringType(), True),
            StructField("temp_avg", DoubleType(), True),
            StructField("humidity_avg", DoubleType(), True),
            StructField("moisture_avg", DoubleType(), True),
            StructField("rainfall_total", DoubleType(), True),
            StructField("nitrogen_avg", DoubleType(), True),
        ])
        
        # Test scenarios with different risk levels
        test_data = [
            # Low risk scenario (healthy conditions)
            ("field_test_001", "2025-12-30", 22.0, 55.0, 40.0, 5.0, 45.0),
            # Medium risk scenario (moderate conditions)
            ("field_test_002", "2025-12-30", 27.0, 72.0, 55.0, 18.0, 38.0),
            # High risk scenario (disease-prone conditions)
            ("field_test_003", "2025-12-30", 30.0, 92.0, 75.0, 45.0, 25.0),
            # Another high risk (extreme conditions)
            ("field_test_004", "2025-12-30", 32.0, 95.0, 85.0, 60.0, 20.0),
            # Normal farming conditions
            ("field_test_005", "2025-12-30", 25.0, 65.0, 50.0, 10.0, 50.0),
        ]
        
        test_df = spark.createDataFrame(test_data, schema)
        print(f"  ✓ Created {test_df.count()} test records")
        
        # Run predictions
        print("\n[5/5] Running predictions...")
        predictions = model.transform(test_df)
        
        # Extract probability function
        def extract_prob(prob_vector):
            if prob_vector is None:
                return 0.0
            if isinstance(prob_vector, (SparseVector, DenseVector)):
                return float(prob_vector[1])
            return float(prob_vector[1]) if len(prob_vector) > 1 else 0.0
        
        from pyspark.sql.types import DoubleType as DT
        extract_prob_udf = F.udf(extract_prob, DT())
        
        results = predictions.withColumn("risk_score", extract_prob_udf(F.col("probability")))
        
        # Display results
        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print("\n{:<15} {:>8} {:>8} {:>8} {:>10} {:>10} {:>10}".format(
            "Field ID", "Temp", "Humid", "Moist", "Risk", "Predict", "Level"
        ))
        print("-" * 70)
        
        for row in results.select(
            "field_id", "temp_avg", "humidity_avg", "moisture_avg",
            "risk_score", "prediction"
        ).collect():
            risk = row.risk_score
            risk_level = "LOW" if risk < 0.3 else "MEDIUM" if risk < 0.6 else "HIGH"
            prediction_label = "DISEASE" if row.prediction == 1.0 else "HEALTHY"
            
            print("{:<15} {:>8.1f} {:>8.1f} {:>8.1f} {:>10.4f} {:>10} {:>10}".format(
                row.field_id,
                row.temp_avg,
                row.humidity_avg,
                row.moisture_avg,
                risk,
                prediction_label,
                risk_level
            ))
        
        print("-" * 70)
        
        # Summary statistics
        avg_risk = results.agg(F.avg("risk_score")).collect()[0][0]
        high_risk_count = results.filter(F.col("risk_score") >= 0.6).count()
        disease_predicted = results.filter(F.col("prediction") == 1.0).count()
        
        print(f"\nSummary:")
        print(f"  ✓ Average Risk Score: {avg_risk:.4f}")
        print(f"  ✓ High Risk Fields: {high_risk_count}/{len(test_data)}")
        print(f"  ✓ Disease Predicted: {disease_predicted}/{len(test_data)}")
        
        print("\n" + "=" * 70)
        print("✓ MODEL TEST COMPLETED SUCCESSFULLY")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        spark.stop()
        print("\n  ✓ Spark session stopped")


if __name__ == "__main__":
    success = test_model()
    sys.exit(0 if success else 1)
