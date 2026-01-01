from pyspark.sql import SparkSession
import sys

print("Starting HDFS Read Test...")
spark = SparkSession.builder.appName("HDFSTest").getOrCreate()

hdfs_path = "hdfs://namenode:9000/agriculture/ml_training/20251226/data_154452.json"
print(f"Reading from: {hdfs_path}")

try:
    df = spark.read.json(hdfs_path)
    print("Schema:")
    df.printSchema()
    print(f"Count: {df.count()}")
    df.show(5)
    print("✓ Read Successful")
except Exception as e:
    print(f"✗ Error: {e}")

spark.stop()
print("Done.")
