#!/bin/bash

# Athena Table Setup Script for Starhub Call Analysis
# This script drops existing table and creates it fresh

set -e  # Exit on any error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "🚀 STARHUB ATHENA TABLE SETUP"
echo "============================="
echo ""

# Configuration
DEFAULT_DATABASE="starhub-poc"
DEFAULT_S3_RESULTS="s3://starhub-totogi-poc/athena-results/"
DEFAULT_S3_BUCKET="starhub-totogi-poc"

# Parse command line arguments
DATABASE="$DEFAULT_DATABASE"
S3_RESULTS="$DEFAULT_S3_RESULTS"
S3_BUCKET="$DEFAULT_S3_BUCKET"
TABLE_TYPE="production"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --database)
            DATABASE="$2"
            shift 2
            ;;
        --s3-results)
            S3_RESULTS="$2"
            shift 2
            ;;
        --s3-bucket)
            S3_BUCKET="$2"
            shift 2
            ;;
        --test)
            TABLE_TYPE="test"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --database NAME       Athena database name (default: starhub-poc)"
            echo "  --s3-results PATH     S3 path for query results (default: s3://starhub-totogi-poc/athena-results/)"
            echo "  --s3-bucket NAME      S3 bucket for data (default: starhub-totogi-poc)"
            echo "  --test               Create test table instead of production"
            echo "  --dry-run            Show what would be done without executing"
            echo "  --help               Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set table name and DDL file based on type
if [ "$TABLE_TYPE" = "test" ]; then
    TABLE_NAME="call_analysis_test"
    S3_PATH="s3://$S3_BUCKET/analysis-test/"
else
    TABLE_NAME="call_analysis"
    S3_PATH="s3://$S3_BUCKET/analysis/"
fi

echo "📋 Configuration:"
echo "   Database: $DATABASE"
echo "   Table: $TABLE_NAME"
echo "   S3 Data Path: $S3_PATH"
echo "   S3 Results: $S3_RESULTS"
echo "   Mode: $([ "$DRY_RUN" = true ] && echo "DRY RUN" || echo "EXECUTE")"
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "❌ Error: AWS CLI is required but not installed"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Error: AWS credentials not configured or invalid"
    echo ""
    echo "Please configure AWS credentials first:"
    echo "  aws configure"
    exit 1
fi

echo "✅ AWS CLI and credentials configured"

# Check if Python setup script exists
if [ ! -f "setup_athena_table.py" ]; then
    echo "❌ Error: setup_athena_table.py not found"
    echo "Please run this script from the generator directory"
    exit 1
fi

# Check if DDL file exists
if [ ! -f "create_athena_table.sql" ]; then
    echo "❌ Error: create_athena_table.sql not found"
    exit 1
fi

echo "✅ Required files found"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "🔍 DRY RUN MODE - Commands that would be executed:"
    echo ""
    echo "1. Drop existing table:"
    echo "   DROP TABLE IF EXISTS $TABLE_NAME;"
    echo ""
    echo "2. Create table from DDL file (modified for $TABLE_TYPE)"
    echo ""
    echo "3. Repair partitions:"
    echo "   MSCK REPAIR TABLE $TABLE_NAME;"
    echo ""
    echo "4. Validate table with sample queries"
    echo ""
    exit 0
fi

# Function to execute Athena query
execute_athena_query() {
    local query="$1"
    local description="$2"
    
    echo "⚡ $description..."
    
    # Start query execution
    QUERY_ID=$(aws athena start-query-execution \
        --query-string "$query" \
        --query-execution-context Database="$DATABASE" \
        --result-configuration OutputLocation="$S3_RESULTS" \
        --query 'QueryExecutionId' \
        --output text)
    
    echo "   Query ID: $QUERY_ID"
    
    # Wait for completion
    while true; do
        STATUS=$(aws athena get-query-execution \
            --query-execution-id "$QUERY_ID" \
            --query 'QueryExecution.Status.State' \
            --output text)
        
        case $STATUS in
            SUCCEEDED)
                echo "   ✅ $description completed successfully"
                return 0
                ;;
            FAILED|CANCELLED)
                ERROR=$(aws athena get-query-execution \
                    --query-execution-id "$QUERY_ID" \
                    --query 'QueryExecution.Status.StateChangeReason' \
                    --output text)
                echo "   ❌ $description failed: $ERROR"
                return 1
                ;;
            RUNNING|QUEUED)
                echo "   ⏳ Status: $STATUS - waiting..."
                sleep 2
                ;;
        esac
    done
}

# Step 1: Drop existing table
echo "🗑️  STEP 1: Dropping existing table..."
DROP_QUERY="DROP TABLE IF EXISTS $TABLE_NAME;"

if ! execute_athena_query "$DROP_QUERY" "Drop existing table"; then
    echo "❌ Failed to drop existing table"
    exit 1
fi

# Step 2: Create table
echo ""
echo "🛠️  STEP 2: Creating fresh table..."

# Read DDL and customize for table type
DDL_CONTENT=$(cat create_athena_table.sql)

# Modify DDL based on table type
if [ "$TABLE_TYPE" = "test" ]; then
    # Replace table name and S3 location for test table
    DDL_CONTENT=$(echo "$DDL_CONTENT" | sed "s/CREATE EXTERNAL TABLE call_analysis/CREATE EXTERNAL TABLE call_analysis_test/")
    DDL_CONTENT=$(echo "$DDL_CONTENT" | sed "s|s3://starhub-totogi-poc/analysis/|s3://$S3_BUCKET/analysis-test/|")
    DDL_CONTENT=$(echo "$DDL_CONTENT" | sed "s|'storage.location.template'='s3://starhub-totogi-poc/analysis/|'storage.location.template'='s3://$S3_BUCKET/analysis-test/|")
else
    # Update S3 bucket if different from default
    DDL_CONTENT=$(echo "$DDL_CONTENT" | sed "s/starhub-totogi-poc/$S3_BUCKET/g")
fi

if ! execute_athena_query "$DDL_CONTENT" "Create table"; then
    echo "❌ Failed to create table"
    exit 1
fi

# Step 3: Repair partitions
echo ""
echo "🔧 STEP 3: Repairing partitions..."
REPAIR_QUERY="MSCK REPAIR TABLE $TABLE_NAME;"

if ! execute_athena_query "$REPAIR_QUERY" "Repair partitions"; then
    echo "⚠️  Warning: Failed to repair partitions (table may still work)"
fi

# Step 4: Validate table
echo ""
echo "🔍 STEP 4: Validating table..."

# Check if table exists
DESCRIBE_QUERY="DESCRIBE $TABLE_NAME;"
if execute_athena_query "$DESCRIBE_QUERY" "Describe table structure"; then
    echo "✅ Table structure validated"
else
    echo "❌ Table validation failed"
    exit 1
fi

# Count rows
COUNT_QUERY="SELECT COUNT(*) as total_rows FROM $TABLE_NAME;"
if execute_athena_query "$COUNT_QUERY" "Count table rows"; then
    # Get the result
    RESULT_QUERY_ID=$QUERY_ID
    sleep 2  # Wait a moment for results to be available
    
    ROW_COUNT=$(aws athena get-query-results \
        --query-execution-id "$RESULT_QUERY_ID" \
        --query 'ResultSet.Rows[1].Data[0].VarCharValue' \
        --output text 2>/dev/null || echo "0")
    
    echo "📊 Table contains $ROW_COUNT rows"
else
    echo "⚠️  Warning: Could not count rows"
fi

echo ""
echo "🎉 ATHENA TABLE SETUP COMPLETED SUCCESSFULLY!"
echo ""
echo "📋 Summary:"
echo "   ✅ Table: $TABLE_NAME"
echo "   ✅ Database: $DATABASE"
echo "   ✅ Data Path: $S3_PATH"
echo "   ✅ Rows: $ROW_COUNT"
echo ""
echo "🎯 You can now run queries against the $TABLE_NAME table:"
echo ""
echo "Example queries:"
echo "  SELECT COUNT(*) FROM $TABLE_NAME;"
echo "  SELECT call_id, agent_name, customer_company, transcript_s3_uri FROM $TABLE_NAME LIMIT 5;"
echo "  SELECT agent_name, COUNT(*) as calls, AVG(grading.total_score_percent) as avg_score"
echo "  FROM $TABLE_NAME GROUP BY agent_name;"
echo "  -- Query S3 URIs to linked files:"
echo "  SELECT call_id, transcript_s3_uri, sfdc_action_s3_uri, diarized_s3_uri FROM $TABLE_NAME LIMIT 3;"
echo ""

# Show next steps based on row count
if [ "$ROW_COUNT" = "0" ] || [ "$ROW_COUNT" = "null" ]; then
    echo "💡 Next steps (no data found):"
    echo "   1. Generate sample data: python3 call_data_generator.py --num-calls 20 --s3-bucket $S3_BUCKET"
    echo "   2. Run this script again to refresh the table"
    echo "   3. Verify files are created in: s3://$S3_BUCKET/analysis/"
elif [ "$TABLE_TYPE" = "test" ]; then
    echo "💡 Test table ready! You can now:"
    echo "   1. Run test queries against call_analysis_test"
    echo "   2. Generate more test data: python3 test_single_record.py"
else
    echo "💡 Production table ready! You can now:"
    echo "   1. Run analytics queries"
    echo "   2. Use sample queries from sample_queries.sql"
    echo "   3. Generate more data: python3 call_data_generator.py --s3-bucket $S3_BUCKET"
    echo "   4. Query S3 URIs: SELECT call_id, transcript_s3_uri, sfdc_action_s3_uri, diarized_s3_uri FROM $TABLE_NAME LIMIT 5;"
fi

echo ""
