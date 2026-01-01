from pyspark.sql import SparkSession
import time

print("Starting Simple Spark Test...")
spark = SparkSession.builder.appName("SimpleTest").getOrCreate()
print(f"Spark Version: {spark.version}")
print("Session created. Stopping...")
spark.stop()
print("Done.")
