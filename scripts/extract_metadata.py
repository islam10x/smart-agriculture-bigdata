#!/usr/bin/env python3
"""
Metadata Extraction Script for PlantVillage Plant Disease Dataset

This script extracts comprehensive metadata from processed images including:
- Image properties (dimensions, format, size)
- Statistical features (mean, std, pixel value distribution)
- Dataset information (class labels, file paths)
- Processing timestamps

Outputs metadata in both CSV and JSON formats for different use cases.
"""

import os
import sys
import yaml
import json
import csv
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import numpy as np
from PIL import Image
from tqdm import tqdm
import pandas as pd


class MetadataExtractor:
    """Extracts and organizes metadata from processed images"""
    
    def __init__(self, config_path: str = "scripts/preprocessing_config.yaml"):
        """Initialize metadata extractor with configuration"""
        self.config = self._load_config(config_path)
        self.metadata_records = []
        self.class_distribution = {}
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            print(f"✓ Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            print(f"✗ Config file not found: {config_path}")
            sys.exit(1)
    
    def extract_image_metadata(self, image_path: Path, class_label: str, split: str) -> Dict[str, Any]:
        """
        Extract comprehensive metadata from a single image
        
        Returns:
            Dictionary containing all metadata fields
        """
        try:
            # Load image
            img = Image.open(image_path)
            img_array = np.array(img)
            
            # Basic metadata
            metadata = {
                # File Information
                'filename': image_path.name,
                'filepath': str(image_path.relative_to(self.config['paths']['processed_data'])),
                'absolute_path': str(image_path.absolute()),
                'file_size_bytes': image_path.stat().st_size,
                'file_size_kb': round(image_path.stat().st_size / 1024, 2),
                
                # Image Properties
                'width': img.width,
                'height': img.height,
                'channels': len(img.getbands()),
                'mode': img.mode,
                'format': img.format if img.format else 'JPEG',
                
                # Classification Labels
                'class_label': class_label,
                'split': split,
                
                # Plant and Disease Information (parsed from class name)
                **self._parse_class_name(class_label),
                
                # Timestamps
                'created_at': datetime.fromtimestamp(image_path.stat().st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(image_path.stat().st_mtime).isoformat(),
            }
            
            # Statistical features (if enabled)
            if self.config['metadata']['extract_statistics']:
                stats = self._calculate_statistics(img_array)
                metadata.update(stats)
            
            return metadata
            
        except Exception as e:
            print(f"\n⚠️  Error extracting metadata from {image_path.name}: {e}")
            return None
    
    def _parse_class_name(self, class_label: str) -> Dict[str, str]:
        """
        Parse PlantVillage class name to extract plant and disease information
        
        Examples:
            - 'Tomato_Early_blight' -> plant='Tomato', disease='Early_blight', health_status='diseased'
            - 'Potato___healthy' -> plant='Potato', disease='None', health_status='healthy'
        """
        parts = class_label.replace('__', '_').split('_')
        
        # Determine plant and disease
        plant = parts[0] if parts else 'Unknown'
        
        is_healthy = 'healthy' in class_label.lower()
        disease = 'None' if is_healthy else '_'.join(parts[1:]) if len(parts) > 1 else 'Unknown'
        
        return {
            'plant_type': plant,
            'disease_name': disease,
            'health_status': 'healthy' if is_healthy else 'diseased'
        }
    
    def _calculate_statistics(self, img_array: np.ndarray) -> Dict[str, float]:
        """Calculate statistical features from image array"""
        stats = {
            'pixel_mean': round(float(np.mean(img_array)), 4),
            'pixel_std': round(float(np.std(img_array)), 4),
            'pixel_min': int(np.min(img_array)),
            'pixel_max': int(np.max(img_array)),
        }
        
        # Per-channel statistics (for RGB)
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            for i, channel in enumerate(['red', 'green', 'blue']):
                stats[f'{channel}_mean'] = round(float(np.mean(img_array[:, :, i])), 4)
                stats[f'{channel}_std'] = round(float(np.std(img_array[:, :, i])), 4)
        
        return stats
    
    def scan_processed_images(self) -> None:
        """Scan all processed images and extract metadata"""
        processed_path = Path(self.config['paths']['processed_data'])
        
        if not processed_path.exists():
            print(f"✗ Processed data directory not found: {processed_path}")
            print("  Please run preprocess_images.py first!")
            sys.exit(1)
        
        print(f"\n📂 Scanning processed images at: {processed_path}")
        
        # Track splits and classes
        splits = ['train', 'val', 'test']
        total_images = 0
        
        # Count total images first for progress bar
        for split in splits:
            split_path = processed_path / split
            if split_path.exists():
                total_images += sum(1 for _ in split_path.rglob('*.jpg'))
                total_images += sum(1 for _ in split_path.rglob('*.png'))
        
        print(f"📊 Found {total_images:,} images to process\n")
        
        # Extract metadata with progress bar
        with tqdm(total=total_images, desc="Extracting metadata", unit="img") as pbar:
            for split in splits:
                split_path = processed_path / split
                
                if not split_path.exists():
                    continue
                
                # Find all class directories
                class_dirs = [d for d in split_path.iterdir() if d.is_dir()]
                
                for class_dir in class_dirs:
                    class_label = class_dir.name
                    
                    # Initialize class distribution counter
                    if class_label not in self.class_distribution:
                        self.class_distribution[class_label] = {
                            'train': 0, 'val': 0, 'test': 0, 'total': 0
                        }
                    
                    # Get all images in class directory
                    images = list(class_dir.glob('*.jpg')) + list(class_dir.glob('*.png'))
                    
                    for img_path in images:
                        # Extract metadata
                        metadata = self.extract_image_metadata(img_path, class_label, split)
                        
                        if metadata:
                            self.metadata_records.append(metadata)
                            self.class_distribution[class_label][split] += 1
                            self.class_distribution[class_label]['total'] += 1
                        
                        pbar.update(1)
        
        print(f"\n✓ Extracted metadata from {len(self.metadata_records):,} images")
    
    def save_metadata_csv(self) -> Path:
        """Save metadata as CSV file (for Spark/Pandas analysis)"""
        output_dir = Path(self.config['paths']['metadata_output'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        csv_path = output_dir / 'image_metadata.csv'
        
        if not self.metadata_records:
            print("⚠️  No metadata records to save!")
            return None
        
        # Convert to DataFrame for easier CSV export
        df = pd.DataFrame(self.metadata_records)
        
        # Sort by split and class for better organization
        df = df.sort_values(['split', 'class_label', 'filename'])
        
        # Save to CSV
        df.to_csv(csv_path, index=False)
        
        print(f"✓ CSV metadata saved to: {csv_path}")
        print(f"  Rows: {len(df):,}, Columns: {len(df.columns)}")
        
        return csv_path
    
    def save_metadata_json(self) -> Path:
        """Save metadata as JSON file (for MongoDB/NoSQL storage)"""
        output_dir = Path(self.config['paths']['metadata_output'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        json_path = output_dir / 'image_metadata.json'
        
        # Create structured JSON
        json_data = {
            'dataset_info': {
                'name': self.config['dataset']['name'],
                'task': self.config['dataset']['task'],
                'num_classes': len(self.class_distribution),
                'total_images': len(self.metadata_records),
                'extraction_timestamp': datetime.now().isoformat(),
            },
            'images': self.metadata_records
        }
        
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"✓ JSON metadata saved to: {json_path}")
        
        return json_path
    
    def save_class_distribution(self) -> Path:
        """Save class distribution summary"""
        output_dir = Path(self.config['paths']['metadata_output'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        dist_path = output_dir / 'class_distribution.json'
        
        distribution_data = {
            'dataset_name': self.config['dataset']['name'],
            'total_classes': len(self.class_distribution),
            'total_images': sum(cls['total'] for cls in self.class_distribution.values()),
            'distribution': self.class_distribution,
            'generated_at': datetime.now().isoformat()
        }
        
        with open(dist_path, 'w') as f:
            json.dump(distribution_data, f, indent=2)
        
        print(f"✓ Class distribution saved to: {dist_path}")
        
        return dist_path
    
    def save_dataset_summary(self) -> Path:
        """Save high-level dataset summary"""
        output_dir = Path(self.config['paths']['metadata_output'])
        output_dir.mkdir(parents=True, exist_ok=True)
        
        summary_path = output_dir / 'dataset_summary.json'
        
        # Calculate summary statistics
        df = pd.DataFrame(self.metadata_records)
        
        summary = {
            'dataset_name': self.config['dataset']['name'],
            'extraction_date': datetime.now().isoformat(),
            'overview': {
                'total_images': len(self.metadata_records),
                'num_classes': len(self.class_distribution),
                'classes': list(self.class_distribution.keys()),
                'splits': {
                    'train': len(df[df['split'] == 'train']),
                    'val': len(df[df['split'] == 'val']),
                    'test': len(df[df['split'] == 'test']),
                }
            },
            'image_properties': {
                'avg_width': int(df['width'].mean()),
                'avg_height': int(df['height'].mean()),
                'avg_file_size_kb': round(df['file_size_kb'].mean(), 2),
                'total_size_mb': round(df['file_size_kb'].sum() / 1024, 2),
            },
            'health_status_distribution': {
                'healthy': len(df[df['health_status'] == 'healthy']),
                'diseased': len(df[df['health_status'] == 'diseased']),
            },
            'plant_types': df['plant_type'].value_counts().to_dict(),
            'config': self.config
        }
        
        # Add statistical info if available
        if 'pixel_mean' in df.columns:
            summary['pixel_statistics'] = {
                'overall_mean': round(df['pixel_mean'].mean(), 4),
                'overall_std': round(df['pixel_std'].mean(), 4),
            }
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"✓ Dataset summary saved to: {summary_path}")
        
        return summary_path
    
    def print_statistics(self) -> None:
        """Print summary statistics to console"""
        df = pd.DataFrame(self.metadata_records)
        
        print("\n" + "=" * 80)
        print("📊 METADATA EXTRACTION SUMMARY")
        print("=" * 80)
        print(f"Total Images:        {len(self.metadata_records):,}")
        print(f"Total Classes:       {len(self.class_distribution)}")
        print(f"\nSplit Distribution:")
        print(f"  ├─ Train:  {len(df[df['split'] == 'train']):,}")
        print(f"  ├─ Val:    {len(df[df['split'] == 'val']):,}")
        print(f"  └─ Test:   {len(df[df['split'] == 'test']):,}")
        
        print(f"\nHealth Status:")
        print(f"  ├─ Healthy:   {len(df[df['health_status'] == 'healthy']):,}")
        print(f"  └─ Diseased:  {len(df[df['health_status'] == 'diseased']):,}")
        
        print(f"\nPlant Types:")
        for plant, count in df['plant_type'].value_counts().items():
            print(f"  ├─ {plant}: {count:,}")
        
        print(f"\nStorage:")
        total_size_mb = df['file_size_kb'].sum() / 1024
        print(f"  └─ Total Size: {total_size_mb:.2f} MB")
        
        print(f"\nOutput Directory: {self.config['paths']['metadata_output']}")
        print("=" * 80)
    
    def run(self) -> None:
        """Run the complete metadata extraction pipeline"""
        print("=" * 80)
        print("📋 PlantVillage Metadata Extraction Pipeline")
        print("=" * 80)
        
        # Step 1: Scan and extract metadata
        self.scan_processed_images()
        
        if not self.metadata_records:
            print("\n✗ No metadata extracted!")
            return
        
        # Step 2: Save in multiple formats
        print("\n💾 Saving metadata files...")
        self.save_metadata_csv()
        self.save_metadata_json()
        self.save_class_distribution()
        self.save_dataset_summary()
        
        # Step 3: Print statistics
        self.print_statistics()
        
        print("\n✅ Metadata extraction complete!")


def main():
    """Main entry point"""
    # Check for config file argument
    config_path = "scripts/preprocessing_config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # Run metadata extraction
    extractor = MetadataExtractor(config_path)
    extractor.run()
    
    print("\n📦 Ready to upload to HDFS:")
    print(f"  1. Processed images: data/processed/plant-disease/")
    print(f"  2. Metadata files: data/processed/metadata/")


if __name__ == "__main__":
    main()
