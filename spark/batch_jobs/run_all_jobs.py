"""
Optimized Job Orchestrator
Runs all analytics jobs in sequence with proper Spark configuration
Now uses pre-trained model from /opt/spark/ml/ directory
"""

import subprocess
import logging
import os
from datetime import datetime
from pymongo import MongoClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JobOrchestrator:
    def __init__(self, mongo_uri):
        self.mongo_uri = mongo_uri
        self.client = MongoClient(mongo_uri)
        self.db = self.client['agriculture']
        self.jobs_collection = self.db['job_execution_log']
        
        # Spark configuration - SIMPLIFIED (no packages download)
        self.spark_config = [
            '--master', 'spark://spark-master:7077',
            '--deploy-mode', 'client',
            '--driver-memory', '1G',
            '--executor-memory', '2G',
            '--conf', 'spark.executor.instances=3',
            '--conf', 'spark.executor.cores=2'
        ]
        
        # Model directory
        self.model_dir = "/opt/spark/ml"
        self.model_path = f"{self.model_dir}/disease_prediction_model"
    
    def check_model_exists(self):
        """Check if trained model exists"""
        exists = os.path.exists(self.model_path)
        if exists:
            logger.info(f"✓ Pre-trained model found at {self.model_path}")
        else:
            logger.warning(f"⚠️  No pre-trained model found at {self.model_path}")
            logger.warning("   Run train_model.py first to create the model")
        return exists
    
    def run_job(self, job_name, script_path, timeout=1800):
        """
        Execute a single Spark job with optimized configuration
        
        Args:
            job_name: Human-readable job name
            script_path: Path to job script
            timeout: Job timeout in seconds (default 30 minutes)
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"🚀 Starting: {job_name}")
        logger.info(f"Script: {script_path}")
        logger.info(f"{'='*70}")
        
        start_time = datetime.now()
        
        try:
            # Use full path to spark-submit
            spark_submit_path = "/opt/spark/bin/spark-submit"
            
            # Build complete spark-submit command
            cmd = [spark_submit_path] + self.spark_config + [script_path]
            
            logger.info(f"Executing: {' '.join(cmd[:3])}...")
            
            # Run with timeout and capture output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd='/opt/spark'  # Set working directory
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Check result
            if result.returncode == 0:
                logger.info(f"✓ {job_name} completed successfully ({duration:.1f}s)")
                # Show last few lines of output
                if result.stdout:
                    output_lines = result.stdout.strip().split('\n')
                    for line in output_lines[-10:]:  # Last 10 lines
                        if line.strip():
                            logger.info(f"  {line}")
                status = 'success'
                error = None
            else:
                logger.error(f"✗ {job_name} failed (exit code {result.returncode})")
                # Show last 1000 chars of stderr
                if result.stderr:
                    error_lines = result.stderr.strip().split('\n')
                    for line in error_lines[-20:]:  # Last 20 lines
                        if line.strip() and not line.startswith('25/'):  # Skip Spark timestamps
                            logger.error(f"  {line}")
                status = 'failed'
                error = result.stderr[-1000:] if result.stderr else 'Unknown error'
            
            # Log execution to MongoDB
            self.jobs_collection.insert_one({
                'job_name': job_name,
                'timestamp': start_time,
                'status': status,
                'duration_seconds': duration,
                'error': error
            })
            
            return status == 'success'
            
        except subprocess.TimeoutExpired:
            logger.error(f"✗ {job_name} timed out (>{timeout}s)")
            self.jobs_collection.insert_one({
                'job_name': job_name,
                'timestamp': start_time,
                'status': 'timeout',
                'duration_seconds': timeout,
                'error': f'Job exceeded {timeout}s time limit'
            })
            return False
            
        except Exception as e:
            logger.error(f"✗ {job_name} execution error: {e}")
            self.jobs_collection.insert_one({
                'job_name': job_name,
                'timestamp': start_time,
                'status': 'error',
                'error': str(e)
            })
            return False
    
    def run_all(self, skip_jobs=None, force_retrain=False):
        """
        Execute all jobs in sequence
        
        Args:
            skip_jobs: List of job names to skip (optional)
            force_retrain: Force model retraining even if model exists
        """
        skip_jobs = skip_jobs or []
        
        logger.info("\n" + "="*70)
        logger.info("📊 SMART AGRICULTURE ANALYTICS PIPELINE")
        logger.info("="*70)
        logger.info(f"MongoDB: mongodb://admin:***@mongodb:27017/agriculture")
        logger.info(f"Spark Master: spark://spark-master:7077")
        logger.info(f"ML Model Path: {self.model_path}")
        logger.info("="*70 + "\n")
        
        # Check if model exists
        model_exists = self.check_model_exists()
        
        if not model_exists and not force_retrain:
            logger.error("\n❌ ERROR: No trained model found!")
            logger.error("Please run one of the following:")
            logger.error("  1. python /opt/spark-apps/train_model.py")
            logger.error("  2. python /opt/spark-apps/run_all_jobs.py --train")
            logger.error("\n")
            return False
        
        # Define all jobs in execution order
        jobs = [
            ('Daily Sensor Aggregation', '/opt/spark-apps/daily_sensor_aggregation.py', 600),
            ('Disease Frequency Analysis', '/opt/spark-apps/disease_frequency_analysis.py', 300),
            ('Data Quality Cleaner', '/opt/spark-apps/data_quality_cleaner.py', 900),
            ('Disease Prediction ML', '/opt/spark-apps/disease_prediction_ml.py', 1200),
            ('Correlation Analysis', '/opt/spark-apps/correlation_analysis.py', 600)
        ]
        
        # If force_retrain, add training job at the beginning
        if force_retrain:
            logger.info("🎓 TRAINING MODE ENABLED - Will retrain model first\n")
            jobs.insert(0, ('Model Training', '/opt/spark-apps/train_model.py', 1500))
        
        # Filter skipped jobs
        jobs = [(name, path, timeout) for name, path, timeout in jobs if name not in skip_jobs]
        
        results = {}
        failed_jobs = []
        pipeline_start = datetime.now()
        
        # Run each job
        for job_name, script_path, timeout in jobs:
            success = self.run_job(job_name, script_path, timeout=timeout)
            results[job_name] = success
            
            if not success:
                failed_jobs.append(job_name)
                logger.warning(f"\n⚠️  {job_name} failed - continuing with next job\n")
                
                # If model training failed, stop the pipeline
                if job_name == 'Model Training':
                    logger.error("❌ Model training failed - stopping pipeline")
                    break
        
        # Pipeline summary
        pipeline_end = datetime.now()
        total_duration = (pipeline_end - pipeline_start).total_seconds()
        
        logger.info("\n" + "="*70)
        logger.info("📋 PIPELINE EXECUTION SUMMARY")
        logger.info("="*70)
        
        for job_name, success in results.items():
            icon = "✓" if success else "✗"
            logger.info(f"{icon} {job_name}")
        
        successful = sum(1 for s in results.values() if s)
        total = len(results)
        
        logger.info(f"\nResults: {successful}/{total} jobs successful")
        logger.info(f"Total Duration: {total_duration/60:.1f} minutes ({int(total_duration)}s)")
        
        if failed_jobs:
            logger.warning(f"\n❌ Failed Jobs: {', '.join(failed_jobs)}")
            logger.warning("Check MongoDB 'job_execution_log' collection for details")
        else:
            logger.info("\n✅ All jobs completed successfully!")
        
        logger.info("="*70 + "\n")
        
        return all(results.values())
    
    def get_job_history(self, limit=20):
        """Retrieve recent job execution history"""
        try:
            history = list(
                self.jobs_collection
                .find()
                .sort('timestamp', -1)
                .limit(limit)
            )
            return history
        except Exception as e:
            logger.error(f"Could not retrieve history: {e}")
            return []
    
    def print_job_history(self, limit=10):
        """Print formatted job history"""
        history = self.get_job_history(limit)
        
        if not history:
            logger.info("No job history found")
            return
        
        logger.info("\n" + "="*70)
        logger.info("📜 RECENT JOB EXECUTION HISTORY")
        logger.info("="*70)
        
        for record in history:
            timestamp = record.get('timestamp', 'N/A')
            job_name = record.get('job_name', 'Unknown')
            status = record.get('status', 'unknown')
            duration = record.get('duration_seconds', 0)
            
            icon = "✓" if status == 'success' else "✗" if status in ['failed', 'error'] else "⏱"
            logger.info(f"{icon} {job_name:30} {status:10} {duration:8.1f}s")
        
        logger.info("="*70 + "\n")


def main():
    """Main entry point"""
    
    import sys
    
    # Check for command line flags
    force_retrain = '--train' in sys.argv or '--retrain' in sys.argv
    
    # MongoDB connection
    mongo_uri = "mongodb://admin:admin123@mongodb:27017/"
    
    # Create orchestrator
    orchestrator = JobOrchestrator(mongo_uri)
    
    # Run all jobs
    success = orchestrator.run_all(force_retrain=force_retrain)
    
    # Print execution history
    orchestrator.print_job_history(limit=10)
    
    # Exit with appropriate code
    exit(0 if success else 1)


if __name__ == "__main__":
    main()