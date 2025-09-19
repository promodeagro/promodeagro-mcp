#!/usr/bin/env python3
"""
S3 Data Cleanup Script for Starhub Call Analysis

This script safely removes old/problematic data from the S3 bucket that's causing
Athena JSON parsing errors. It includes safety measures and confirmation prompts.

⚠️  WARNING: This script will delete data from S3. Use with caution! ⚠️

Author: AI Assistant
Date: 2025
"""

import boto3
import argparse
import time
from datetime import datetime
from typing import List, Dict, Any

class S3DataCleaner:
    def __init__(self, s3_bucket: str = "starhub-totogi-poc"):
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3')
        self.s3_prefix = "analysis/"
        
    def list_objects(self, prefix: str = None) -> List[Dict[str, Any]]:
        """List all objects in the specified S3 prefix"""
        prefix = prefix or self.s3_prefix
        objects = []
        
        print(f"🔍 Scanning s3://{self.s3_bucket}/{prefix}...")
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.s3_bucket, Prefix=prefix)
            
            for page in pages:
                if 'Contents' in page:
                    objects.extend(page['Contents'])
                    
        except Exception as e:
            print(f"❌ Error listing objects: {str(e)}")
            return []
            
        print(f"📊 Found {len(objects)} objects")
        return objects
    
    def analyze_objects(self, objects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the objects to provide summary information"""
        analysis = {
            'total_objects': len(objects),
            'total_size_bytes': sum(obj['Size'] for obj in objects),
            'file_types': {},
            'date_range': {'earliest': None, 'latest': None},
            'monthly_distribution': {}
        }
        
        for obj in objects:
            # File type analysis
            key = obj['Key']
            if key.endswith('.json'):
                if 'analysis' in key:
                    file_type = 'analysis'
                elif 'sfdcaction' in key:
                    file_type = 'sfdcaction'
                elif 'transcript' in key:
                    file_type = 'transcript'
                else:
                    file_type = 'other_json'
            else:
                file_type = 'other'
                
            analysis['file_types'][file_type] = analysis['file_types'].get(file_type, 0) + 1
            
            # Date analysis
            last_modified = obj['LastModified']
            if analysis['date_range']['earliest'] is None or last_modified < analysis['date_range']['earliest']:
                analysis['date_range']['earliest'] = last_modified
            if analysis['date_range']['latest'] is None or last_modified > analysis['date_range']['latest']:
                analysis['date_range']['latest'] = last_modified
                
            # Monthly distribution
            month_key = last_modified.strftime('%Y-%m')
            analysis['monthly_distribution'][month_key] = analysis['monthly_distribution'].get(month_key, 0) + 1
        
        return analysis
    
    def print_analysis(self, analysis: Dict[str, Any]):
        """Print detailed analysis of the objects"""
        print("\n📈 DATA ANALYSIS SUMMARY")
        print("=" * 50)
        
        print(f"📁 Total Objects: {analysis['total_objects']:,}")
        print(f"💾 Total Size: {analysis['total_size_bytes']:,} bytes ({analysis['total_size_bytes'] / (1024*1024):.2f} MB)")
        
        if analysis['date_range']['earliest'] and analysis['date_range']['latest']:
            print(f"📅 Date Range: {analysis['date_range']['earliest'].strftime('%Y-%m-%d')} to {analysis['date_range']['latest'].strftime('%Y-%m-%d')}")
        
        print(f"\n📊 File Types:")
        for file_type, count in sorted(analysis['file_types'].items()):
            print(f"  • {file_type}: {count:,} files")
        
        print(f"\n📆 Monthly Distribution:")
        for month, count in sorted(analysis['monthly_distribution'].items()):
            print(f"  • {month}: {count:,} files")
    
    def confirm_deletion(self, objects: List[Dict[str, Any]]) -> bool:
        """Get user confirmation before deletion"""
        print(f"\n⚠️  WARNING: This will DELETE {len(objects):,} objects from S3!")
        print(f"📍 Bucket: s3://{self.s3_bucket}/{self.s3_prefix}")
        print(f"💾 Total Size: {sum(obj['Size'] for obj in objects) / (1024*1024):.2f} MB")
        
        print(f"\n🔄 This action CANNOT be undone!")
        print(f"💡 Consider creating a backup first if you're unsure.")
        
        confirmation = input(f"\nType 'DELETE ALL DATA' to confirm deletion: ").strip()
        
        if confirmation == "DELETE ALL DATA":
            final_confirm = input(f"Are you absolutely sure? Type 'YES' to proceed: ").strip().upper()
            return final_confirm == "YES"
        
        return False
    
    def delete_objects_batch(self, objects: List[Dict[str, Any]], batch_size: int = 1000) -> bool:
        """Delete objects in batches for efficiency"""
        total_objects = len(objects)
        deleted_count = 0
        
        print(f"\n🗑️  Starting deletion of {total_objects:,} objects in batches of {batch_size}...")
        
        try:
            for i in range(0, total_objects, batch_size):
                batch = objects[i:i + batch_size]
                
                # Prepare batch delete request
                delete_request = {
                    'Objects': [{'Key': obj['Key']} for obj in batch],
                    'Quiet': False
                }
                
                # Execute batch delete
                response = self.s3_client.delete_objects(
                    Bucket=self.s3_bucket,
                    Delete=delete_request
                )
                
                batch_deleted = len(response.get('Deleted', []))
                deleted_count += batch_deleted
                
                # Handle any errors
                if 'Errors' in response:
                    for error in response['Errors']:
                        print(f"❌ Error deleting {error['Key']}: {error['Message']}")
                
                # Progress update
                progress = (deleted_count / total_objects) * 100
                print(f"🔄 Progress: {deleted_count:,}/{total_objects:,} ({progress:.1f}%) - Batch {(i//batch_size)+1} completed")
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
                
        except Exception as e:
            print(f"❌ Error during batch deletion: {str(e)}")
            return False
        
        print(f"✅ Successfully deleted {deleted_count:,} objects!")
        return True
    
    def backup_object_list(self, objects: List[Dict[str, Any]], filename: str = None) -> str:
        """Save list of objects to a backup file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"s3_deletion_backup_{timestamp}.json"
        
        import json
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'bucket': self.s3_bucket,
            'prefix': self.s3_prefix,
            'total_objects': len(objects),
            'objects': [
                {
                    'Key': obj['Key'],
                    'Size': obj['Size'],
                    'LastModified': obj['LastModified'].isoformat()
                }
                for obj in objects
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        print(f"💾 Object list backed up to: {filename}")
        return filename
    
    def clean_all_data(self, dry_run: bool = False, create_backup: bool = True, batch_size: int = 1000) -> bool:
        """Main method to clean all old data"""
        print("🧹 STARHUB S3 DATA CLEANUP TOOL")
        print("=" * 40)
        
        # List all objects
        objects = self.list_objects()
        
        if not objects:
            print("✅ No objects found to delete")
            return True
        
        # Analyze objects
        analysis = self.analyze_objects(objects)
        self.print_analysis(analysis)
        
        if dry_run:
            print(f"\n🔍 DRY RUN MODE - No objects will be deleted")
            print(f"📋 Would delete {len(objects):,} objects ({analysis['total_size_bytes'] / (1024*1024):.2f} MB)")
            return True
        
        # Create backup of object list
        if create_backup:
            self.backup_object_list(objects)
        
        # Get confirmation
        if not self.confirm_deletion(objects):
            print("❌ Deletion cancelled by user")
            return False
        
        # Perform deletion
        success = self.delete_objects_batch(objects, batch_size)
        
        if success:
            print(f"\n🎉 Cleanup completed successfully!")
            print(f"📊 Deleted {len(objects):,} objects from s3://{self.s3_bucket}/{self.s3_prefix}")
            
            # Verify cleanup
            remaining_objects = self.list_objects()
            if remaining_objects:
                print(f"⚠️  Warning: {len(remaining_objects)} objects still remain")
            else:
                print(f"✅ Cleanup verified - no objects remain in the path")
        
        return success
    
    def clean_specific_pattern(self, pattern: str, dry_run: bool = False):
        """Clean objects matching a specific pattern"""
        print(f"🧹 Cleaning objects matching pattern: {pattern}")
        
        objects = self.list_objects()
        matching_objects = [obj for obj in objects if pattern in obj['Key']]
        
        if not matching_objects:
            print(f"✅ No objects found matching pattern '{pattern}'")
            return True
        
        print(f"📊 Found {len(matching_objects)} objects matching pattern")
        
        if dry_run:
            print("🔍 DRY RUN MODE - Would delete:")
            for obj in matching_objects[:10]:  # Show first 10
                print(f"  • {obj['Key']}")
            if len(matching_objects) > 10:
                print(f"  ... and {len(matching_objects) - 10} more")
            return True
        
        if self.confirm_deletion(matching_objects):
            return self.delete_objects_batch(matching_objects)
        
        return False

def main():
    parser = argparse.ArgumentParser(description="Clean old S3 call analysis data")
    parser.add_argument("--s3-bucket", default="starhub-totogi-poc", help="S3 bucket name")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--pattern", type=str, help="Only delete objects matching this pattern")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backup file")
    parser.add_argument("--batch-size", type=int, default=1000, help="Number of objects to delete per batch")
    
    args = parser.parse_args()
    
    cleaner = S3DataCleaner(s3_bucket=args.s3_bucket)
    
    if args.pattern:
        success = cleaner.clean_specific_pattern(args.pattern, dry_run=args.dry_run)
    else:
        success = cleaner.clean_all_data(
            dry_run=args.dry_run,
            create_backup=not args.no_backup,
            batch_size=args.batch_size
        )
    
    if success:
        print("\n🎯 Next steps:")
        print("1. Run 'python test_with_clean_data.py' to generate fresh data")
        print("2. Use 'python setup_athena_table.py' to recreate the main table")
        print("3. Test queries against your clean data")
    else:
        print("\n❌ Cleanup failed or was cancelled")

if __name__ == "__main__":
    main()
