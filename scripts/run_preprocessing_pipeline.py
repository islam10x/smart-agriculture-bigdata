#!/usr/bin/env python3
"""
End-to-End Preprocessing Pipeline for PlantVillage Dataset

This script orchestrates the complete preprocessing workflow:
1. Image preprocessing (resize, normalize, split)
2. Metadata extraction (CSV, JSON)
3. Summary report generation

Run this single script to perform all preprocessing steps automatically.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
import time


class Pipeline:
    """Orchestrates the preprocessing pipeline"""
    
    def __init__(self):
        self.start_time = None
        self.steps_completed = []
        self.steps_failed = []
    
    def print_header(self):
        """Print pipeline header"""
        print("\n" + "=" * 80)
        print("🌾 PlantVillage Dataset Preprocessing Pipeline")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80 + "\n")
    
    def print_step(self, step_num: int, step_name: str):
        """Print step header"""
        print(f"\n{'─' * 80}")
        print(f"📌 STEP {step_num}: {step_name}")
        print(f"{'─' * 80}\n")
    
    def run_script(self, script_name: str, description: str) -> bool:
        """
        Run a Python script and capture its output
        
        Returns:
            True if successful, False otherwise
        """
        script_path = Path("scripts") / script_name
        
        if not script_path.exists():
            print(f"✗ Script not found: {script_path}")
            return False
        
        try:
            # Run the script
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=False,  # Show output in real-time
                text=True
            )
            
            if result.returncode == 0:
                print(f"\n✓ {description} completed successfully!")
                return True
            else:
                print(f"\n✗ {description} failed with return code {result.returncode}")
                return False
                
        except Exception as e:
            print(f"\n✗ Error running {script_name}: {e}")
            return False
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed"""
        print("🔍 Checking dependencies...\n")
        
        required_packages = [
            'PIL',
            'numpy',
            'pandas',
            'yaml',
            'sklearn',
            'tqdm'
        ]
        
        missing = []
        for package in required_packages:
            try:
                __import__(package if package != 'PIL' else 'PIL')
                print(f"  ✓ {package}")
            except ImportError:
                print(f"  ✗ {package} (missing)")
                missing.append(package)
        
        if missing:
            print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
            print("\nInstall them with:")
            print("  pip install -r scripts/requirements.txt")
            return False
        
        print("\n✓ All dependencies installed!")
        return True
    
    def verify_input_data(self) -> bool:
        """Verify that input data exists"""
        print("\n🔍 Verifying input data...\n")
        
        raw_data_path = Path("data/raw/plant-disease/PlantVillage")
        
        if not raw_data_path.exists():
            print(f"✗ Raw data directory not found: {raw_data_path}")
            print("\nPlease ensure your dataset is located at:")
            print(f"  {raw_data_path.absolute()}")
            return False
        
        # Count images
        image_count = sum(1 for _ in raw_data_path.rglob('*.jpg'))
        image_count += sum(1 for _ in raw_data_path.rglob('*.png'))
        
        if image_count == 0:
            print(f"✗ No images found in {raw_data_path}")
            return False
        
        print(f"✓ Found {image_count:,} images in dataset")
        return True
    
    def run(self) -> None:
        """Execute the complete pipeline"""
        self.start_time = time.time()
        self.print_header()
        
        # Pre-flight checks
        self.print_step(0, "Pre-flight Checks")
        
        if not self.check_dependencies():
            print("\n❌ Pipeline aborted: Missing dependencies")
            sys.exit(1)
        
        if not self.verify_input_data():
            print("\n❌ Pipeline aborted: Input data not found")
            sys.exit(1)
        
        # Step 1: Image Preprocessing
        self.print_step(1, "Image Preprocessing")
        if self.run_script("preprocess_images.py", "Image preprocessing"):
            self.steps_completed.append("Image Preprocessing")
        else:
            self.steps_failed.append("Image Preprocessing")
            print("\n❌ Pipeline aborted: Image preprocessing failed")
            sys.exit(1)
        
        # Step 2: Metadata Extraction
        self.print_step(2, "Metadata Extraction")
        if self.run_script("extract_metadata.py", "Metadata extraction"):
            self.steps_completed.append("Metadata Extraction")
        else:
            self.steps_failed.append("Metadata Extraction")
            print("\n❌ Pipeline aborted: Metadata extraction failed")
            sys.exit(1)
        
        # Final summary
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print final pipeline summary"""
        elapsed_time = time.time() - self.start_time
        
        print("\n" + "=" * 80)
        print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        
        print(f"\n⏱️  Total Time: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
        
        print(f"\n✅ Completed Steps ({len(self.steps_completed)}):")
        for i, step in enumerate(self.steps_completed, 1):
            print(f"  {i}. {step}")
        
        if self.steps_failed:
            print(f"\n❌ Failed Steps ({len(self.steps_failed)}):")
            for i, step in enumerate(self.steps_failed, 1):
                print(f"  {i}. {step}")
        
        print("\n📦 Output Directories:")
        print("  ├─ Processed Images: data/processed/plant-disease/")
        print("  │   ├─ train/")
        print("  │   ├─ val/")
        print("  │   └─ test/")
        print("  └─ Metadata Files: data/processed/metadata/")
        print("      ├─ image_metadata.csv")
        print("      ├─ image_metadata.json")
        print("      ├─ class_distribution.json")
        print("      └─ dataset_summary.json")
        
        print("\n📋 Next Steps:")
        print("  1. Review the processed images in data/processed/plant-disease/")
        print("  2. Check metadata files in data/processed/metadata/")
        print("  3. Upload to HDFS using the following commands:")
        print()
        print("     # Upload processed images")
        print("     docker-compose exec namenode hdfs dfs -mkdir -p /agriculture/plant-disease/processed")
        print('     docker-compose exec namenode bash -c "hdfs dfs -put -f /data/processed/plant-disease/* /agriculture/plant-disease/processed/"')
        print()
        print("     # Upload metadata")
        print("     docker-compose exec namenode hdfs dfs -mkdir -p /agriculture/plant-disease/metadata")
        print('     docker-compose exec namenode bash -c "hdfs dfs -put -f /data/processed/metadata/* /agriculture/plant-disease/metadata/"')
        print()
        print("     # Verify upload")
        print("     docker-compose exec namenode hdfs dfs -ls -R /agriculture/plant-disease")
        
        print("\n" + "=" * 80)


def main():
    """Main entry point"""
    pipeline = Pipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
