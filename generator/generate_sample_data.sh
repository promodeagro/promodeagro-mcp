#!/bin/bash

# Starhub Call Analysis Data Generator
# Quick generation script with common presets

echo "Starhub Call Analysis Data Generator"
echo "===================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check if required modules are installed
if ! python3 -c "import boto3" 2>/dev/null; then
    echo "Installing required Python packages..."
    echo "Note: Installing in system Python (externally managed environment)"
    pip3 install -r requirements.txt --break-system-packages || {
        echo "Failed to install packages. Trying individual installation..."
        pip3 install boto3 --break-system-packages
    }
fi

echo ""
# S3 Bucket Configuration
echo "S3 Configuration:"
read -p "S3 bucket name [starhub-totogi-poc]: " s3_bucket
s3_bucket=${s3_bucket:-starhub-totogi-poc}

echo ""
echo "Available options:"
echo "1. Quick test (5 calls, local only)"
echo "2. Small dataset (20 calls, 14 days, S3 only)" 
echo "3. Medium dataset (50 calls, 30 days, S3 only)"
echo "4. Large dataset (100 calls, 60 days, S3 only)"
echo "5. Custom parameters"
echo ""

read -p "Select option [1-5]: " choice

case $choice in
    1)
        echo "Generating quick test dataset (local only)..."
        python3 call_data_generator.py --num-calls 5 --days-back 3 --s3-bucket "$s3_bucket" --local-only
        ;;
    2)
        echo "Generating small dataset (S3 only)..."
        python3 call_data_generator.py --num-calls 20 --days-back 14 --s3-bucket "$s3_bucket"
        ;;
    3)
        echo "Generating medium dataset (S3 only)..."
        python3 call_data_generator.py --num-calls 50 --days-back 30 --s3-bucket "$s3_bucket"
        ;;
    4)
        echo "Generating large dataset with S3 upload..."
        read -p "This will upload to S3. Do you have AWS credentials configured? [y/N]: " confirm
        if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
            python3 call_data_generator.py --num-calls 100 --days-back 60 --s3-bucket "$s3_bucket"
        else
            echo "Please configure AWS credentials first:"
            echo "  aws configure"
            echo "  OR set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
            exit 1
        fi
        ;;
    5)
        echo "Custom generation..."
        read -p "Number of calls [10]: " num_calls
        read -p "Days back [7]: " days_back
        read -p "Upload to S3? [y/N]: " upload_s3
        
        num_calls=${num_calls:-10}
        days_back=${days_back:-7}
        
        if [[ $upload_s3 == [yY] || $upload_s3 == [yY][eE][sS] ]]; then
            python3 call_data_generator.py --num-calls $num_calls --days-back $days_back --s3-bucket "$s3_bucket"
        else
            python3 call_data_generator.py --num-calls $num_calls --days-back $days_back --s3-bucket "$s3_bucket" --local-only
        fi
        ;;
    *)
        echo "Invalid option. Exiting."
        exit 1
        ;;
esac

echo ""
echo "Generation complete!"
echo "Local files are saved in: ./output/ with structure:"
echo "  - ./output/analysis/year=YYYY/month=MM/day=DD/"
echo "  - ./output/transcript/year=YYYY/month=MM/day=DD/"
echo "  - ./output/sfdcaction/year=YYYY/month=MM/day=DD/"
echo "  - ./output/diarized/year=YYYY/month=MM/day=DD/"
echo "S3 files (if uploaded) are stored in: s3://$s3_bucket/"
echo ""
echo "Next steps:"
echo "1. Review generated JSON files in the structured folders"
echo "2. Create Athena table using the DDL in docs/ddl-for-call-analysis-table.md"
echo "3. Test SQL queries against your partitioned data"
echo "4. Analysis files contain S3 URIs linking to transcript, sfdcaction, and diarized files"
echo ""
