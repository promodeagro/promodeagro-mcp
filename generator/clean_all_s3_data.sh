#!/bin/bash

# Clean All S3 Data Script for Starhub Call Analysis
# This script safely removes all call analysis data from S3
# Uses the Python cleanup tool with built-in safety features

set -e  # Exit on any error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "🧹 STARHUB S3 DATA CLEANUP"
echo "=========================="
echo ""
echo "This script will help you clean call analysis data from S3."
echo "⚠️  WARNING: This action cannot be undone!"
echo ""

# Check if cleanup script exists
if [ ! -f "cleanup_s3_data.py" ]; then
    echo "❌ Error: cleanup_s3_data.py not found in current directory"
    echo "Please run this script from the generator directory"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed"
    exit 1
fi

# Check AWS credentials
echo "🔍 Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Error: AWS credentials not configured or invalid"
    echo ""
    echo "Please configure AWS credentials first:"
    echo "  aws configure"
    echo "  OR set environment variables:"
    echo "    export AWS_ACCESS_KEY_ID=your_key"
    echo "    export AWS_SECRET_ACCESS_KEY=your_secret"
    echo "    export AWS_DEFAULT_REGION=ap-southeast-1"
    exit 1
fi

echo "✅ AWS credentials configured"
echo ""

# Show menu options
echo "Select cleanup option:"
echo "1. Preview what would be deleted (dry run - safe)"
echo "2. Clean analysis folder (main call analysis data)"
echo "3. Clean transcript folder (transcript files)"
echo "4. Clean sfdcaction folder (Salesforce action files)"
echo "5. Clean athena-results folder (Athena query results)"
echo "6. Clean diarized folder (diarized audio files)"
echo "7. Clean everything (all folders)"
echo "8. Custom cleanup"
echo "9. Exit"
echo ""

read -p "Enter your choice [1-9]: " choice

case $choice in
    1)
        echo ""
        echo "🔍 PREVIEW MODE - No data will be deleted"
        echo "=====================================+"
        python3 cleanup_s3_data.py --dry-run
        ;;
    
    2)
        echo ""
        echo "🗑️  CLEANING ANALYSIS DATA"
        echo "=========================="
        echo "This will delete all files in: s3://starhub-totogi-poc/analysis/"
        echo ""
        read -p "Are you absolutely sure? Type 'yes' to continue: " confirm
        
        if [ "$confirm" = "yes" ]; then
            python3 cleanup_s3_data.py
        else
            echo "❌ Cleanup cancelled"
        fi
        ;;
    
    3)
        echo ""
        echo "🗑️  CLEANING TRANSCRIPT DATA"
        echo "============================"
        echo "This will delete all files in: s3://starhub-totogi-poc/transcript/"
        echo ""
        read -p "Type 'yes' to continue: " confirm
        
        if [ "$confirm" = "yes" ]; then
            echo "🧹 Removing transcript files..."
            aws s3 rm s3://starhub-totogi-poc/transcript/ --recursive
            echo "✅ Transcript data cleaned successfully"
        else
            echo "❌ Cleanup cancelled"
        fi
        ;;
    
    4)
        echo ""
        echo "🗑️  CLEANING SFDCACTION DATA"
        echo "============================="
        echo "This will delete all files in: s3://starhub-totogi-poc/sfdcaction/"
        echo ""
        read -p "Type 'yes' to continue: " confirm
        
        if [ "$confirm" = "yes" ]; then
            echo "🧹 Removing sfdcaction files..."
            aws s3 rm s3://starhub-totogi-poc/sfdcaction/ --recursive
            echo "✅ SFDC action data cleaned successfully"
        else
            echo "❌ Cleanup cancelled"
        fi
        ;;
    
    5)
        echo ""
        echo "🗑️  CLEANING ATHENA RESULTS"
        echo "============================"
        echo "This will delete all files in: s3://starhub-totogi-poc/athena-results/"
        echo ""
        read -p "Type 'yes' to continue: " confirm
        
        if [ "$confirm" = "yes" ]; then
            echo "🧹 Removing athena-results files..."
            aws s3 rm s3://starhub-totogi-poc/athena-results/ --recursive
            echo "✅ Athena results cleaned successfully"
        else
            echo "❌ Cleanup cancelled"
        fi
        ;;
    
    6)
        echo ""
        echo "🗑️  CLEANING DIARIZED DATA"
        echo "==========================="
        echo "This will delete all files in: s3://starhub-totogi-poc/diarized/"
        echo ""
        read -p "Type 'yes' to continue: " confirm
        
        if [ "$confirm" = "yes" ]; then
            echo "🧹 Removing diarized files..."
            aws s3 rm s3://starhub-totogi-poc/diarized/ --recursive
            echo "✅ Diarized data cleaned successfully"
        else
            echo "❌ Cleanup cancelled"
        fi
        ;;
    
    7)
        echo ""
        echo "🗑️  CLEANING EVERYTHING"
        echo "======================"
        echo "This will delete ALL data from the following folders:"
        echo "  - s3://starhub-totogi-poc/analysis/"
        echo "  - s3://starhub-totogi-poc/transcript/"
        echo "  - s3://starhub-totogi-poc/sfdcaction/"
        echo "  - s3://starhub-totogi-poc/athena-results/"
        echo "  - s3://starhub-totogi-poc/diarized/"
        echo ""
        echo "⚠️  This will remove ALL data from the bucket! ⚠️"
        echo ""
        read -p "Type 'DELETE EVERYTHING' to confirm: " confirm
        
        if [ "$confirm" = "DELETE EVERYTHING" ]; then
            echo ""
            echo "🧹 Cleaning analysis data..."
            python3 cleanup_s3_data.py --no-backup
            
            echo ""
            echo "🧹 Cleaning transcript data..."
            aws s3 rm s3://starhub-totogi-poc/transcript/ --recursive
            
            echo ""
            echo "🧹 Cleaning sfdcaction data..."
            aws s3 rm s3://starhub-totogi-poc/sfdcaction/ --recursive
            
            echo ""
            echo "🧹 Cleaning athena-results data..."
            aws s3 rm s3://starhub-totogi-poc/athena-results/ --recursive
            
            echo ""
            echo "🧹 Cleaning diarized data..."
            aws s3 rm s3://starhub-totogi-poc/diarized/ --recursive
            
            echo ""
            echo "✅ All data cleaned successfully!"
        else
            echo "❌ Cleanup cancelled"
        fi
        ;;
    
    8)
        echo ""
        echo "🛠️  CUSTOM CLEANUP"
        echo "=================="
        echo "Available options for cleanup_s3_data.py:"
        echo ""
        python3 cleanup_s3_data.py --help
        echo ""
        read -p "Enter custom arguments (or press Enter for interactive): " custom_args
        
        if [ -z "$custom_args" ]; then
            python3 cleanup_s3_data.py
        else
            python3 cleanup_s3_data.py $custom_args
        fi
        ;;
    
    9)
        echo "👋 Cleanup cancelled by user"
        exit 0
        ;;
    
    *)
        echo "❌ Invalid option selected"
        exit 1
        ;;
esac

echo ""
echo "🎉 Cleanup operation completed!"

# Show next steps
if [ "$choice" != "1" ] && [ "$choice" != "9" ]; then
    echo ""
    echo "📋 Next steps:"
    echo "1. Generate fresh data: python3 call_data_generator.py --num-calls 20"
    echo "2. Create Athena table: python3 setup_athena_table.py"
    echo "3. Test with clean data: python3 test_single_record.py"
fi

echo ""