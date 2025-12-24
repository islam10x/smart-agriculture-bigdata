#!/usr/bin/env python3
"""
Image Preprocessing Script for PlantVillage Plant Disease Dataset

This script processes the PlantVillage dataset by:
1. Loading and validating images
2. Resizing to target dimensions
3. Normalizing pixel values
4. Splitting into train/val/test sets
5. Saving processed images to organized directory structure

Optimized for plant disease detection and classification tasks.
"""

import os
import sys
import yaml
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from PIL import Image
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import json
from datetime import datetime


class ImagePreprocessor:
    """Handles image preprocessing for PlantVillage dataset"""
    
    def __init__(self, config_path: str = "scripts/preprocessing_config.yaml"):
        """Initialize preprocessor with configuration"""
        self.config = self._load_config(config_path)
        self.stats = {
            'total_images': 0,
            'processed_images': 0,
            'skipped_images': 0,
            'corrupted_images': 0,
            'classes': {},
            'splits': {'train': 0, 'val': 0, 'test': 0}
        }
        
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
        except yaml.YAMLError as e:
            print(f"✗ Error parsing config file: {e}")
            sys.exit(1)
    
    def scan_dataset(self) -> Dict[str, List[Path]]:
        """Scan the raw dataset and organize by class"""
        raw_path = Path(self.config['paths']['raw_data'])
        
        if not raw_path.exists():
            print(f"✗ Raw data directory not found: {raw_path}")
            sys.exit(1)
        
        print(f"\n📂 Scanning dataset at: {raw_path}")
        
        # Find all class directories
        class_dirs = [d for d in raw_path.rglob('*') if d.is_dir() and not d.name.startswith('.')]
        
        dataset = {}
        total_images = 0
        
        for class_dir in class_dirs:
            # Get all image files
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
            images = [
                img for img in class_dir.iterdir()
                if img.is_file() and img.suffix.lower() in image_extensions
            ]
            
            if images:
                class_name = class_dir.name
                dataset[class_name] = images
                total_images += len(images)
                print(f"  ├─ {class_name}: {len(images)} images")
        
        print(f"\n📊 Dataset Summary:")
        print(f"  ├─ Total Classes: {len(dataset)}")
        print(f"  └─ Total Images: {total_images}")
        
        self.stats['total_images'] = total_images
        self.stats['classes'] = {k: len(v) for k, v in dataset.items()}
        
        return dataset
    
    def split_dataset(self, dataset: Dict[str, List[Path]]) -> Dict[str, Dict[str, List[Path]]]:
        """Split dataset into train/val/test sets with stratification"""
        train_ratio = self.config['split']['train']
        val_ratio = self.config['split']['val']
        test_ratio = self.config['split']['test']
        random_seed = self.config['split']['random_seed']
        
        print(f"\n🔀 Splitting dataset (Train: {train_ratio:.0%}, Val: {val_ratio:.0%}, Test: {test_ratio:.0%})")
        
        splits = {'train': {}, 'val': {}, 'test': {}}
        
        for class_name, images in dataset.items():
            # First split: train vs (val + test)
            train_imgs, temp_imgs = train_test_split(
                images,
                test_size=(val_ratio + test_ratio),
                random_state=random_seed
            )
            
            # Second split: val vs test
            val_imgs, test_imgs = train_test_split(
                temp_imgs,
                test_size=test_ratio / (val_ratio + test_ratio),
                random_state=random_seed
            )
            
            splits['train'][class_name] = train_imgs
            splits['val'][class_name] = val_imgs
            splits['test'][class_name] = test_imgs
            
            print(f"  ├─ {class_name}: Train={len(train_imgs)}, Val={len(val_imgs)}, Test={len(test_imgs)}")
        
        # Update stats
        for split_name in ['train', 'val', 'test']:
            self.stats['splits'][split_name] = sum(len(imgs) for imgs in splits[split_name].values())
        
        return splits
    
    def apply_augmentation(self, img: Image.Image) -> List[Image.Image]:
        """Apply random augmentations to generate new images"""
        aug_config = self.config['preprocessing']['augmentation']
        augmented_images = []
        
        # Determine how many augmented versions to create (default 3 if not specified)
        num_aug = aug_config.get('num_versions', 3)
        
        for _ in range(num_aug):
            aug_img = img.copy()
            
            # Random Rotation
            if aug_config.get('rotation_range', 0) > 0:
                angle = np.random.uniform(-aug_config['rotation_range'], aug_config['rotation_range'])
                aug_img = aug_img.rotate(angle, resample=Image.Resampling.BILINEAR, expand=False)
            
            # Random Horizontal Flip
            if aug_config.get('horizontal_flip', False) and np.random.random() > 0.5:
                aug_img = aug_img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                
            # Random Vertical Flip
            if aug_config.get('vertical_flip', False) and np.random.random() > 0.5:
                aug_img = aug_img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                
            # Random Brightness
            if aug_config.get('brightness_range'):
                min_b, max_b = aug_config['brightness_range']
                factor = np.random.uniform(min_b, max_b)
                # Simple pixel value scaling for brightness
                # Convert to array, scale, clip, convert back
                arr = np.array(aug_img).astype(np.float32)
                arr = np.clip(arr * factor, 0, 255).astype(np.uint8)
                aug_img = Image.fromarray(arr)
            
            augmented_images.append(aug_img)
            
        return augmented_images

    def process_image(self, image_path: Path, augment: bool = False) -> List[Tuple[np.ndarray, str]]:
        """
        Process a single image: load, resize, normalize, optionally augment
        
        Returns:
            List of tuples (processed_image_array, suffix)
            Suffix is empty string for original, '_aug_N' for augmented
        """
        results = []
        try:
            # Load image
            img = Image.open(image_path)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize
            target_size = tuple(self.config['preprocessing']['target_size'])
            img = img.resize(target_size, Image.Resampling.LANCZOS)
            
            # Prepare list of images to process (original + optional augmented)
            images_to_process = [(img, "")]
            
            if augment and self.config['preprocessing']['augmentation']['enabled']:
                aug_imgs = self.apply_augmentation(img)
                for i, aug_img in enumerate(aug_imgs):
                    images_to_process.append((aug_img, f"_aug_{i+1}"))
            
            # Normalize and convert all images
            for image, suffix in images_to_process:
                img_array = np.array(image)
                
                if self.config['preprocessing']['normalize']:
                    img_array = img_array.astype(np.float32) / 255.0
                
                results.append((img_array, suffix))
            
            return results, True
            
        except Exception as e:
            if self.config['processing']['verbose']:
                print(f"\n⚠️  Error processing {image_path.name}: {e}")
            return [], False
    
    def save_processed_image(self, image_array: np.ndarray, output_path: Path) -> bool:
        """Save processed image to disk"""
        try:
            # Create parent directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Denormalize if image was normalized
            if self.config['preprocessing']['normalize']:
                image_array = (image_array * 255).astype(np.uint8)
            
            # Convert back to PIL Image
            img = Image.fromarray(image_array)
            
            # Save with specified format and quality
            img_format = self.config['preprocessing']['format']
            quality = self.config['preprocessing']['quality']
            
            if img_format.upper() == 'JPEG':
                img.save(output_path, format='JPEG', quality=quality, optimize=True)
            else:
                img.save(output_path, format=img_format)
            
            return True
            
        except Exception as e:
            print(f"\n✗ Error saving {output_path}: {e}")
            return False
    
    def process_split(self, split_name: str, split_data: Dict[str, List[Path]]) -> None:
        """Process all images in a split (train/val/test)"""
        output_base = Path(self.config['paths']['processed_data']) / split_name
        
        # Only augment training data
        should_augment = (split_name == 'train')
        
        print(f"\n🔄 Processing {split_name.upper()} split (Augmentation: {should_augment})...")
        
        # Count total images in this split
        total_images = sum(len(images) for images in split_data.values())
        
        with tqdm(total=total_images, desc=f"Processing {split_name}", unit="img") as pbar:
            for class_name, images in split_data.items():
                output_dir = output_base / class_name
                
                for img_path in images:
                    # Process image (returns list of results)
                    results, success = self.process_image(img_path, augment=should_augment)
                    
                    if success and results:
                        for img_array, suffix in results:
                            # Create output path with optional suffix
                            output_path = output_dir / f"{img_path.stem}{suffix}.jpg"
                            
                            if self.save_processed_image(img_array, output_path):
                                self.stats['processed_images'] += 1
                            else:
                                self.stats['skipped_images'] += 1
                    else:
                        self.stats['corrupted_images'] += 1
                        if not self.config['processing']['skip_corrupted']:
                            raise Exception(f"Failed to process {img_path}")
                    
                    pbar.update(1)
    
    def create_manifest(self, splits: Dict[str, Dict[str, List[Path]]]) -> None:
        """Create a manifest file with dataset structure information"""
        manifest = {
            'dataset_name': self.config['dataset']['name'],
            'created_at': datetime.now().isoformat(),
            'preprocessing_config': self.config['preprocessing'],
            'splits': {},
            'classes': list(self.stats['classes'].keys()),
            'num_classes': len(self.stats['classes']),
            'statistics': self.stats
        }
        
        # Add file paths for each split
        for split_name, split_data in splits.items():
            manifest['splits'][split_name] = {}
            for class_name, images in split_data.items():
                manifest['splits'][split_name][class_name] = [str(img) for img in images]
        
        # Save manifest
        manifest_path = Path(self.config['paths']['processed_data']) / 'manifest.json'
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"\n📄 Manifest saved to: {manifest_path}")
    
    def run(self) -> None:
        """Run the complete preprocessing pipeline"""
        print("=" * 80)
        print("🌾 PlantVillage Image Preprocessing Pipeline")
        print("=" * 80)
        
        # Step 1: Scan dataset
        dataset = self.scan_dataset()
        
        if not dataset:
            print("\n✗ No images found in dataset!")
            return
        
        # Step 2: Split dataset
        splits = self.split_dataset(dataset)
        
        # Step 3: Process each split
        for split_name in ['train', 'val', 'test']:
            self.process_split(split_name, splits[split_name])
        
        # Step 4: Create manifest
        if self.config['processing']['create_backup_manifest']:
            self.create_manifest(splits)
        
        # Step 5: Print summary
        self._print_summary()
    
    def _print_summary(self) -> None:
        """Print processing summary"""
        print("\n" + "=" * 80)
        print("📊 PREPROCESSING SUMMARY")
        print("=" * 80)
        print(f"Total Images Scanned:    {self.stats['total_images']:,}")
        print(f"Successfully Processed:  {self.stats['processed_images']:,}")
        print(f"Skipped/Failed:          {self.stats['skipped_images']:,}")
        print(f"Corrupted:              {self.stats['corrupted_images']:,}")
        print(f"\nSplit Distribution:")
        print(f"  ├─ Train:  {self.stats['splits']['train']:,} images")
        print(f"  ├─ Val:    {self.stats['splits']['val']:,} images")
        print(f"  └─ Test:   {self.stats['splits']['test']:,} images")
        print(f"\nOutput Directory: {self.config['paths']['processed_data']}")
        print("=" * 80)
        
        # Calculate success rate
        if self.stats['total_images'] > 0:
            success_rate = (self.stats['processed_images'] / self.stats['total_images']) * 100
            print(f"\n✓ Success Rate: {success_rate:.2f}%")


def main():
    """Main entry point"""
    # Check for config file argument
    config_path = "scripts/preprocessing_config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # Run preprocessing
    preprocessor = ImagePreprocessor(config_path)
    preprocessor.run()
    
    print("\n✅ Preprocessing complete! You can now upload the processed data to HDFS.")


if __name__ == "__main__":
    main()
