#!/bin/bash

# ====================================================================
# STARHUB CALL ANALYSIS DASHBOARD
# ====================================================================
# Comprehensive dashboard implementing ALL 20 use cases from call analysis
# with beautifully formatted tabular output and comprehensive insights
# 
# Organized in 7 logical sections:
# • Performance Monitoring & KPIs (1-4)
# • Sales & Revenue Intelligence (5-7) 
# • Customer Experience & Sentiment (8-10)
# • Compliance & Quality Assurance (11-13)
# • Training & Development Insights (14-15)
# • Communication & Behavioral Analysis (16-17)
# • Operational Excellence (18-20)
#
# Author: AI Assistant
# Date: 2025
# ====================================================================

set -e

# Color definitions for beautiful output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
DEFAULT_DATABASE="starhub-poc"
DEFAULT_S3_RESULTS="s3://starhub-totogi-poc/athena-results/"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Parse command line arguments
DATABASE="$DEFAULT_DATABASE"
S3_RESULTS="$DEFAULT_S3_RESULTS"
OUTPUT_DIR="dashboard_results"
QUIET=false

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
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --help)
            echo "📊 Starhub Call Analysis Dashboard"
            echo "=================================="
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --database NAME       Athena database name (default: starhub-poc)"
            echo "  --s3-results PATH     S3 path for query results (default: s3://starhub-totogi-poc/athena-results/)"
            echo "  --output-dir DIR      Output directory for results (default: dashboard_results)"
            echo "  --quiet              Suppress progress messages"
            echo "  --help               Show this help message"
            echo ""
            echo "Implemented Use Cases (20 Total):"
            echo ""
            echo "📊 Performance Monitoring & KPIs:"
            echo "  1. 📈 Overall Calls Volume Analysis - Last Week"
            echo "  2. 👤 Agent-wise Performance Summary"
            echo "  3. 📅 Agent-wise Daily Performance Details"
            echo "  4. 📊 Quality Score Distribution Analysis"
            echo ""
            echo "🎯 Sales & Revenue Intelligence:"
            echo "  5. 💰 Sales Pipeline Value Analysis"
            echo "  6. 💎 High-Value Deal Identification"
            echo "  7. 📈 Call Type Performance & Conversion"
            echo ""
            echo "😊 Customer Experience & Sentiment:"
            echo "  8. 📊 Customer Satisfaction Trends"
            echo "  9. 🎭 Sentiment Analysis by Agent"
            echo " 10. 🔍 Low Satisfaction Call Deep Dive"
            echo ""
            echo "⚖️ Compliance & Quality Assurance:"
            echo " 11. 🛡️ PDPA Compliance Monitoring"
            echo " 12. 📜 Script Adherence Analysis"
            echo " 13. ⚠️ Quality Failures Root Cause Analysis"
            echo ""
            echo "📚 Training & Development:"
            echo " 14. 🎯 Training Needs Assessment"
            echo " 15. 📋 Most Common Performance Recommendations"
            echo ""
            echo "💬 Communication & Behavioral:"
            echo " 16. 🗣️ Talk-to-Listen Ratio Analysis"
            echo " 17. ✋ Customer Interruption Pattern Analysis"
            echo ""
            echo "📈 Operational Excellence:"
            echo " 18. ⏱️ Call Duration vs Quality Correlation"
            echo " 19. 🔍 S3 Data Completeness Audit"
            echo " 20. ⏰ Peak Performance Period Analysis"
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

# Function to print colored headers
print_header() {
    local icon="$1"
    local title="$2"
    local color="$3"
    
    echo ""
    echo -e "${color}${BOLD}════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${color}${BOLD}${icon} ${title}${NC}"
    echo -e "${color}${BOLD}════════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Function to print section headers
print_section() {
    local icon="$1"
    local title="$2"
    local color="$3"
    
    echo ""
    echo -e "${color}${BOLD}${icon} ${title}${NC}"
    echo -e "${color}────────────────────────────────────────────────────────────────────────────${NC}"
}

# Function to print category headers
print_category() {
    local icon="$1"
    local title="$2"
    local color="$3"
    
    echo ""
    echo -e "${color}${BOLD}╔════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${color}${BOLD}║ ${icon} ${title}${NC}${color}${BOLD}║${NC}"
    echo -e "${color}${BOLD}╚════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Function to execute Athena query and format results
execute_athena_query() {
    local query="$1"
    local description="$2"
    local output_file="$3"
    
    if [[ "$QUIET" != "true" ]]; then
        echo -e "  ${CYAN}⚡ Executing: ${description}...${NC}"
    fi
    
    # Start query execution
    local query_id
    query_id=$(aws athena start-query-execution \
        --query-string "$query" \
        --query-execution-context Database="$DATABASE" \
        --result-configuration OutputLocation="$S3_RESULTS" \
        --query 'QueryExecutionId' \
        --output text 2>/dev/null)
    
    if [[ $? -ne 0 ]] || [[ -z "$query_id" ]]; then
        echo -e "  ${RED}❌ Failed to start query: $description${NC}"
        return 1
    fi
    
    if [[ "$QUIET" != "true" ]]; then
        echo -e "  ${GRAY}   Query ID: $query_id${NC}"
    fi
    
    # Wait for completion with minimal progress indicator
    while true; do
        local status
        status=$(aws athena get-query-execution \
            --query-execution-id "$query_id" \
            --query 'QueryExecution.Status.State' \
            --output text 2>/dev/null)
        
        case $status in
            SUCCEEDED)
                if [[ "$QUIET" != "true" ]]; then
                    echo -e "  ${GREEN}✅ Completed${NC}"
                fi
                break
                ;;
            FAILED|CANCELLED)
                local error
                error=$(aws athena get-query-execution \
                    --query-execution-id "$query_id" \
                    --query 'QueryExecution.Status.StateChangeReason' \
                    --output text 2>/dev/null)
                echo -e "  ${RED}❌ Query failed: $error${NC}"
                return 1
                ;;
            RUNNING|QUEUED)
                sleep 2
                ;;
        esac
    done
    
    # Get results in JSON format and convert to readable table
    local json_results
    json_results=$(aws athena get-query-results \
        --query-execution-id "$query_id" \
        --output json 2>/dev/null)
    
    if [[ $? -eq 0 ]] && [[ -n "$json_results" ]]; then
        # Convert JSON to clean table format
        echo "$json_results" | python3 -c "
import json, sys
import re

try:
    data = json.load(sys.stdin)
    result_set = data.get('ResultSet', {})
    rows = result_set.get('Rows', [])
    
    if len(rows) < 1:
        print('No data available')
        sys.exit(0)
    
    # Get headers from first row
    headers = [col.get('VarCharValue', '') for col in rows[0].get('Data', [])]
    
    if len(rows) < 2:
        print('No data rows available')
        sys.exit(0)
    
    # Calculate column widths
    col_widths = [len(header) for header in headers]
    
    # Check data rows for width
    for row in rows[1:]:
        data_row = [col.get('VarCharValue', '') for col in row.get('Data', [])]
        for i, cell in enumerate(data_row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Print table
    # Top border
    border_line = '+' + '+'.join(['-' * (w + 2) for w in col_widths]) + '+'
    print(border_line)
    
    # Headers
    header_line = '|'
    for i, header in enumerate(headers):
        if i < len(col_widths):
            header_line += f' {header:<{col_widths[i]}} |'
    print(header_line)
    print(border_line)
    
    # Data rows
    for row in rows[1:]:
        data_row = [col.get('VarCharValue', '') for col in row.get('Data', [])]
        row_line = '|'
        for i, cell in enumerate(data_row):
            if i < len(col_widths):
                row_line += f' {str(cell):<{col_widths[i]}} |'
        print(row_line)
    
    # Bottom border
    print(border_line)
    
except Exception as e:
    print(f'Error formatting results: {e}')
    sys.exit(1)
" > "$output_file" 2>/dev/null
    else
        echo "Error: Failed to get query results" > "$output_file"
        return 1
    fi
    
    return 0
}

# Function to format table output with colors and formatting
format_table_output() {
    local file="$1"
    local title="$2"
    local icon="$3"
    local color="$4"
    
    if [[ ! -f "$file" ]] || [[ ! -s "$file" ]]; then
        echo -e "  ${RED}❌ No data available${NC}"
        return 1
    fi
    
    echo -e "${color}${BOLD}${icon} ${title}${NC}"
    echo ""
    
    # Check if file contains error message
    if grep -q "Error" "$file"; then
        echo -e "${RED}❌ $(cat "$file")${NC}"
        return 1
    fi
    
    # Process the table to add colors and formatting
    local line_num=0
    local is_data_row=false
    
    while IFS= read -r line; do
        line_num=$((line_num + 1))
        
        if [[ $line =~ ^[+].*[+]$ ]]; then
            # Table borders (+ characters)
            echo -e "${color}${BOLD}$line${NC}"
        elif [[ $line =~ ^[|].*[|]$ ]] && [[ $line_num -eq 2 ]]; then
            # Header row (first data row after border)
            echo -e "${WHITE}${BOLD}$line${NC}"
            is_data_row=true
        elif [[ $line =~ ^[|].*[|]$ ]] && [[ $is_data_row == true ]]; then
            # Data rows - alternate colors for readability
            if [[ $((line_num % 2)) -eq 0 ]]; then
                echo -e "${WHITE}$line${NC}"
            else
                echo -e "${GRAY}$line${NC}"
            fi
        else
            # Other lines (like error messages)
            echo -e "${WHITE}$line${NC}"
        fi
    done < "$file"
    echo ""
}

# Function to create summary stats
create_summary_stats() {
    local output_dir="$1"
    
    print_section "📋" "EXECUTIVE SUMMARY" "$PURPLE"
    
    echo -e "${WHITE}${BOLD}Dashboard Generated: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${WHITE}${BOLD}Database: ${DATABASE}${NC}"
    echo -e "${WHITE}${BOLD}Results Location: ${output_dir}${NC}"
    echo ""
    
    # Count total files generated
    local file_count
    file_count=$(find "$output_dir" -name "*.txt" | wc -l)
    echo -e "${GREEN}✅ Successfully generated $file_count reports${NC}"
    echo ""
    
    echo -e "${CYAN}${BOLD}Reports Generated by Category:${NC}"
    echo -e "${GREEN}📊 Performance Monitoring & KPIs:${NC}"
    echo -e "${WHITE}  • 📈 Call Volume Analysis${NC}"
    echo -e "${WHITE}  • 👤 Agent Performance Analysis${NC}"
    echo -e "${WHITE}  • 📅 Agent Daily Performance${NC}"
    echo -e "${WHITE}  • 📊 Quality Score Distribution${NC}"
    echo -e "${PURPLE}🎯 Sales & Revenue Intelligence:${NC}"
    echo -e "${WHITE}  • 💰 Sales Pipeline Analysis${NC}"
    echo -e "${WHITE}  • 💎 High-Value Deal Identification${NC}"
    echo -e "${WHITE}  • 📈 Call Type Performance${NC}"
    echo -e "${YELLOW}😊 Customer Experience & Sentiment:${NC}"
    echo -e "${WHITE}  • 📊 Customer Satisfaction Trends${NC}"
    echo -e "${WHITE}  • 🎭 Sentiment Analysis by Agent${NC}"
    echo -e "${WHITE}  • 🔍 Low Satisfaction Call Analysis${NC}"
    echo -e "${CYAN}⚖️ Compliance & Quality Assurance:${NC}"
    echo -e "${WHITE}  • 🛡️ PDPA Compliance Monitoring${NC}"
    echo -e "${WHITE}  • 📜 Script Adherence Analysis${NC}"
    echo -e "${WHITE}  • ⚠️ Quality Failures Root Cause${NC}"
    echo -e "${BLUE}📚 Training & Development:${NC}"
    echo -e "${WHITE}  • 🎯 Training Needs Assessment${NC}"
    echo -e "${WHITE}  • 📋 Performance Recommendations${NC}"
    echo -e "${WHITE}💬 Communication & Behavioral:${NC}"
    echo -e "${WHITE}  • 🗣️ Talk-to-Listen Ratio Analysis${NC}"
    echo -e "${WHITE}  • ✋ Customer Interruption Patterns${NC}"
    echo -e "${GREEN}📈 Operational Excellence:${NC}"
    echo -e "${WHITE}  • ⏱️ Call Duration vs Quality${NC}"
    echo -e "${WHITE}  • 🔍 S3 Data Completeness Audit${NC}"
    echo -e "${WHITE}  • ⏰ Peak Performance Periods${NC}"
}

# Main execution starts here
print_header "📊" "STARHUB CALL ANALYSIS DASHBOARD" "$BLUE"

echo -e "${WHITE}${BOLD}Configuration:${NC}"
echo -e "${WHITE}  Database: ${GREEN}$DATABASE${NC}"
echo -e "${WHITE}  S3 Results: ${GREEN}$S3_RESULTS${NC}"
echo -e "${WHITE}  Output Directory: ${GREEN}$OUTPUT_DIR${NC}"
echo ""

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ Error: AWS CLI is required but not installed${NC}"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ Error: AWS credentials not configured or invalid${NC}"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

# █████████████████████████████████████████████████████████████████████████████████
# 📊 SECTION 1: PERFORMANCE MONITORING & KPIs
# █████████████████████████████████████████████████████████████████████████████████

print_category "📊" "PERFORMANCE MONITORING & KPIs" "$GREEN"

# =============================================================================
# USE CASE 1: Overall Calls Volume Analysis - Last Week
# =============================================================================
print_section "📈" "USE CASE 1: OVERALL CALLS VOLUME ANALYSIS - LAST WEEK" "$GREEN"

QUERY_1="SELECT 
    CAST(FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) AS DATE) as date,
    COUNT(*) as calls,
    ROUND(AVG(grading.total_score_percent), 1) as avg_score,
    ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as satisfaction,
    ROUND(COUNT(CASE WHEN grading.pass = true THEN 1 END) * 100.0 / COUNT(*), 0) as pass_rate
FROM call_analysis
WHERE FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) >= current_date - interval '7' day
GROUP BY CAST(FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) AS DATE)
ORDER BY date DESC;"

if execute_athena_query "$QUERY_1" "Call Volume Analysis - Last Week" "$OUTPUT_DIR/call_volume_last_week.txt"; then
    format_table_output "$OUTPUT_DIR/call_volume_last_week.txt" "📈 Call Volume - Last 7 Days" "📊" "$GREEN"
fi

# =============================================================================
# USE CASE 2: Agent-wise Performance Summary
# =============================================================================
print_section "👤" "USE CASE 2: AGENT-WISE PERFORMANCE SUMMARY" "$BLUE"

QUERY_2="SELECT 
    agent_name as agent,
    COUNT(*) as calls,
    ROUND(AVG(grading.total_score_percent), 1) as score,
    ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as csat,
    ROUND(AVG(script_adherence.adherence_percentage), 0) as script_adh,
    ROUND(SUM(deal_potential.estimated_value)/1000, 0) as pipeline_k,
    ROUND(AVG(deal_potential.probability), 2) as deal_prob
FROM call_analysis
WHERE year = CAST(year(current_date) AS VARCHAR)
GROUP BY agent_name
ORDER BY score DESC
LIMIT 10;"

if execute_athena_query "$QUERY_2" "Agent Performance Summary" "$OUTPUT_DIR/agent_performance.txt"; then
    format_table_output "$OUTPUT_DIR/agent_performance.txt" "👤 Agent Performance Rankings" "🏆" "$BLUE"
fi

# =============================================================================
# USE CASE 3: Agent-wise Daily Performance Details
# =============================================================================
print_section "📅" "USE CASE 3: AGENT-WISE DAILY PERFORMANCE DETAILS" "$GREEN"

QUERY_3_NEW="SELECT 
    agent_name as agent,
    CAST(FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) AS DATE) as date,
    COUNT(*) as calls,
    ROUND(AVG(grading.total_score_percent), 1) as avg_score,
    COUNT(CASE WHEN grading.pass = true THEN 1 END) as passing,
    ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as csat,
    ROUND(AVG(call_metrics.talk_to_listen_ratio), 2) as talk_ratio
FROM call_analysis
WHERE FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) >= current_date - interval '30' day
GROUP BY agent_name, CAST(FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) AS DATE)
ORDER BY agent, date DESC
LIMIT 50;"

if execute_athena_query "$QUERY_3_NEW" "Agent Daily Performance Details" "$OUTPUT_DIR/agent_daily_performance.txt"; then
    format_table_output "$OUTPUT_DIR/agent_daily_performance.txt" "📅 Agent Daily Performance (Last 30 Days)" "📊" "$GREEN"
fi

# =============================================================================
# USE CASE 4: Quality Score Distribution Analysis
# =============================================================================
print_section "📊" "USE CASE 4: QUALITY SCORE DISTRIBUTION ANALYSIS" "$GREEN"

QUERY_4_NEW="SELECT 
    CASE 
        WHEN grading.total_score_percent >= 90 THEN 'Excellent (90-100)'
        WHEN grading.total_score_percent >= 80 THEN 'Good (80-89)'
        WHEN grading.total_score_percent >= 70 THEN 'Satisfactory (70-79)'
        WHEN grading.total_score_percent >= 60 THEN 'Needs Improvement (60-69)'
        ELSE 'Poor (<60)'
    END as quality_band,
    COUNT(*) as call_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage,
    ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as avg_csat
FROM call_analysis
WHERE year = CAST(year(current_date) AS VARCHAR)
GROUP BY 
    CASE 
        WHEN grading.total_score_percent >= 90 THEN 'Excellent (90-100)'
        WHEN grading.total_score_percent >= 80 THEN 'Good (80-89)'
        WHEN grading.total_score_percent >= 70 THEN 'Satisfactory (70-79)'
        WHEN grading.total_score_percent >= 60 THEN 'Needs Improvement (60-69)'
        ELSE 'Poor (<60)'
    END
ORDER BY quality_band DESC;"

if execute_athena_query "$QUERY_4_NEW" "Quality Score Distribution Analysis" "$OUTPUT_DIR/quality_distribution.txt"; then
    format_table_output "$OUTPUT_DIR/quality_distribution.txt" "📊 Quality Score Distribution" "📈" "$GREEN"
fi

# █████████████████████████████████████████████████████████████████████████████████
# 🎯 SECTION 2: SALES & REVENUE INTELLIGENCE
# █████████████████████████████████████████████████████████████████████████████████

print_category "🎯" "SALES & REVENUE INTELLIGENCE" "$PURPLE"

# =============================================================================
# USE CASE 5: Sales Pipeline Value Analysis
# =============================================================================
print_section "💰" "USE CASE 5: SALES PIPELINE VALUE ANALYSIS" "$PURPLE"

QUERY_4="SELECT 
    agent_name as agent,
    call_type as type,
    COUNT(*) as calls,
    ROUND(SUM(deal_potential.estimated_value)/1000, 0) as pipeline_k,
    ROUND(AVG(deal_potential.probability), 2) as avg_prob,
    COUNT(CASE WHEN deal_potential.probability > 0.7 THEN 1 END) as high_prob
FROM call_analysis
WHERE deal_potential.estimated_value > 0
  AND year = CAST(year(current_date) AS VARCHAR)
GROUP BY agent_name, call_type
HAVING COUNT(*) >= 1
ORDER BY pipeline_k DESC
LIMIT 15;"

if execute_athena_query "$QUERY_4" "Sales Pipeline Analysis" "$OUTPUT_DIR/sales_pipeline.txt"; then
    format_table_output "$OUTPUT_DIR/sales_pipeline.txt" "💰 Sales Pipeline Analysis" "💎" "$PURPLE"
fi

# =============================================================================
# USE CASE 6: High-Value Deal Identification
# =============================================================================
print_section "💎" "USE CASE 6: HIGH-VALUE DEAL IDENTIFICATION" "$PURPLE"

QUERY_6="SELECT 
    call_id,
    agent_name as agent,
    customer_company as company,
    call_type as type,
    deal_potential.estimated_value as deal_value,
    deal_potential.probability as prob,
    ROUND(deal_potential.estimated_value * deal_potential.probability, 0) as weighted_value,
    grading.total_score_percent as quality,
    sentiment_analysis.customer_satisfaction as csat
FROM call_analysis
WHERE deal_potential.estimated_value >= 100000
  AND deal_potential.probability >= 0.6
  AND year = CAST(year(current_date) AS VARCHAR)
ORDER BY weighted_value DESC
LIMIT 20;"

if execute_athena_query "$QUERY_6" "High-Value Deal Identification" "$OUTPUT_DIR/high_value_deals.txt"; then
    format_table_output "$OUTPUT_DIR/high_value_deals.txt" "💎 High-Value Deal Opportunities" "🎯" "$PURPLE"
fi

# =============================================================================
# USE CASE 7: Call Type Performance & Conversion Analysis
# =============================================================================
print_section "📈" "USE CASE 7: CALL TYPE PERFORMANCE & CONVERSION ANALYSIS" "$PURPLE"

QUERY_7="SELECT 
    call_type as type,
    COUNT(*) as calls,
    COUNT(CASE WHEN grading.pass = true THEN 1 END) as quality_calls,
    ROUND(COUNT(CASE WHEN grading.pass = true THEN 1 END) * 100.0 / COUNT(*), 1) as quality_rate,
    ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as avg_csat,
    COUNT(CASE WHEN deal_potential.probability > 0.7 THEN 1 END) as high_prob_deals,
    ROUND(SUM(deal_potential.estimated_value)/1000, 0) as pipeline_k,
    ROUND(AVG(deal_potential.estimated_value), 0) as avg_deal_size
FROM call_analysis
WHERE year = CAST(year(current_date) AS VARCHAR)
GROUP BY call_type
ORDER BY pipeline_k DESC;"

if execute_athena_query "$QUERY_7" "Call Type Performance Analysis" "$OUTPUT_DIR/call_type_performance.txt"; then
    format_table_output "$OUTPUT_DIR/call_type_performance.txt" "📈 Call Type Performance & Conversion" "🎯" "$PURPLE"
fi

# █████████████████████████████████████████████████████████████████████████████████
# 😊 SECTION 3: CUSTOMER EXPERIENCE & SENTIMENT
# █████████████████████████████████████████████████████████████████████████████████

print_category "😊" "CUSTOMER EXPERIENCE & SENTIMENT" "$YELLOW"

# =============================================================================
# USE CASE 8: Customer Satisfaction Trends
# =============================================================================
print_section "📊" "USE CASE 8: CUSTOMER SATISFACTION TRENDS" "$YELLOW"

QUERY_8="SELECT 
    CAST(FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) AS DATE) as call_date,
    COUNT(*) as calls,
    ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as avg_csat,
    ROUND(AVG(sentiment_analysis.overall_sentiment), 2) as avg_sentiment,
    COUNT(CASE WHEN sentiment_analysis.customer_satisfaction >= 0.8 THEN 1 END) as high_csat,
    COUNT(CASE WHEN sentiment_analysis.customer_satisfaction <= 0.3 THEN 1 END) as low_csat
FROM call_analysis
WHERE FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) >= current_date - interval '30' day
GROUP BY CAST(FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) AS DATE)
ORDER BY call_date DESC
LIMIT 15;"

if execute_athena_query "$QUERY_8" "Customer Satisfaction Trends" "$OUTPUT_DIR/satisfaction_trends_weekly.txt"; then
    format_table_output "$OUTPUT_DIR/satisfaction_trends_weekly.txt" "📊 Customer Satisfaction Daily Trends" "📈" "$YELLOW"
fi

# =============================================================================
# USE CASE 9: Sentiment Analysis by Agent
# =============================================================================
print_section "🎭" "USE CASE 9: SENTIMENT ANALYSIS BY AGENT" "$YELLOW"

QUERY_9="SELECT 
    agent_name as agent,
    COUNT(*) as calls,
    ROUND(AVG(sentiment_analysis.customer_satisfaction), 3) as avg_csat,
    ROUND(AVG(sentiment_analysis.overall_sentiment), 3) as avg_sentiment,
    COUNT(CASE WHEN sentiment_analysis.customer_satisfaction >= 0.8 THEN 1 END) as excellent,
    COUNT(CASE WHEN sentiment_analysis.customer_satisfaction <= 0.3 THEN 1 END) as poor,
    ROUND(AVG(call_metrics.customer_interruption_count), 1) as avg_interrupts
FROM call_analysis
WHERE year = CAST(year(current_date) AS VARCHAR)
GROUP BY agent_name
HAVING COUNT(*) >= 10
ORDER BY avg_csat DESC;"

if execute_athena_query "$QUERY_9" "Sentiment Analysis by Agent" "$OUTPUT_DIR/sentiment_by_agent.txt"; then
    format_table_output "$OUTPUT_DIR/sentiment_by_agent.txt" "🎭 Sentiment Analysis by Agent" "😊" "$YELLOW"
fi

# =============================================================================
# USE CASE 10: Low Satisfaction Call Deep Dive
# =============================================================================
print_section "🔍" "USE CASE 10: LOW SATISFACTION CALL DEEP DIVE" "$YELLOW"

QUERY_10="SELECT 
    call_id,
    agent_name as agent,
    customer_company as company,
    call_type as type,
    sentiment_analysis.customer_satisfaction as csat,
    sentiment_analysis.overall_sentiment as sentiment,
    grading.total_score_percent as quality,
    call_metrics.customer_interruption_count as interrupts,
    ROUND(call_metrics.talk_to_listen_ratio, 2) as talk_ratio
FROM call_analysis
WHERE sentiment_analysis.customer_satisfaction <= 0.3
  AND FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) >= current_date - interval '30' day
ORDER BY sentiment_analysis.customer_satisfaction ASC
LIMIT 50;"

if execute_athena_query "$QUERY_10" "Low Satisfaction Call Deep Dive" "$OUTPUT_DIR/low_satisfaction_calls.txt"; then
    format_table_output "$OUTPUT_DIR/low_satisfaction_calls.txt" "🔍 Low Satisfaction Calls Analysis" "⚠️" "$YELLOW"
fi

# █████████████████████████████████████████████████████████████████████████████████
# ⚖️ SECTION 4: COMPLIANCE & QUALITY ASSURANCE
# █████████████████████████████████████████████████████████████████████████████████

print_category "⚖️" "COMPLIANCE & QUALITY ASSURANCE" "$CYAN"

# =============================================================================
# USE CASE 11: PDPA Compliance Monitoring
# =============================================================================
print_section "🛡️" "USE CASE 11: PDPA COMPLIANCE MONITORING" "$CYAN"

QUERY_11="SELECT 
    agent_name as agent,
    COUNT(*) as calls,
    COUNT(CASE WHEN compliance.pdpa_pass = true THEN 1 END) as compliant,
    COUNT(CASE WHEN compliance.pdpa_pass = false THEN 1 END) as violations,
    ROUND(COUNT(CASE WHEN compliance.pdpa_pass = true THEN 1 END) * 100.0 / COUNT(*), 0) as compliance_rate,
    COUNT(CASE WHEN cardinality(compliance.breaches) > 0 THEN 1 END) as breaches
FROM call_analysis
WHERE FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) >= current_date - interval '3' month
GROUP BY agent_name
HAVING COUNT(*) >= 1
ORDER BY compliance_rate DESC
LIMIT 15;"

if execute_athena_query "$QUERY_11" "PDPA Compliance Monitoring" "$OUTPUT_DIR/pdpa_compliance.txt"; then
    format_table_output "$OUTPUT_DIR/pdpa_compliance.txt" "🛡️ PDPA Compliance Status" "⚖️" "$CYAN"
fi

# =============================================================================
# USE CASE 12: Script Adherence Analysis
# =============================================================================
print_section "📜" "USE CASE 12: SCRIPT ADHERENCE ANALYSIS" "$CYAN"

QUERY_12="SELECT 
    agent_name as agent,
    COUNT(*) as calls,
    ROUND(AVG(script_adherence.adherence_percentage), 1) as avg_adherence,
    COUNT(CASE WHEN script_adherence.adherence_percentage >= 90 THEN 1 END) as excellent,
    COUNT(CASE WHEN script_adherence.adherence_percentage < 70 THEN 1 END) as poor
FROM call_analysis
WHERE year = CAST(year(current_date) AS VARCHAR)
GROUP BY agent_name
HAVING COUNT(*) >= 5
ORDER BY avg_adherence DESC;"

if execute_athena_query "$QUERY_12" "Script Adherence Analysis" "$OUTPUT_DIR/script_adherence.txt"; then
    format_table_output "$OUTPUT_DIR/script_adherence.txt" "📜 Script Adherence Analysis" "✅" "$CYAN"
fi

# =============================================================================
# USE CASE 13: Quality Failures by Agent
# =============================================================================
print_section "⚠️" "USE CASE 13: QUALITY FAILURES BY AGENT" "$CYAN"

QUERY_13="SELECT 
    agent_name as agent,
    COUNT(*) as total_calls,
    COUNT(CASE WHEN grading.pass = false THEN 1 END) as failed_calls,
    ROUND(AVG(grading.total_score_percent), 1) as avg_score,
    COUNT(CASE WHEN grading.total_score_percent < 50 THEN 1 END) as poor_quality_calls,
    ROUND(COUNT(CASE WHEN grading.pass = false THEN 1 END) * 100.0 / COUNT(*), 1) as failure_rate
FROM call_analysis
WHERE FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) >= current_date - interval '30' day
GROUP BY agent_name
HAVING COUNT(CASE WHEN grading.pass = false THEN 1 END) > 0
ORDER BY failure_rate DESC
LIMIT 10;"

if execute_athena_query "$QUERY_13" "Quality Failures by Agent" "$OUTPUT_DIR/quality_failures.txt"; then
    format_table_output "$OUTPUT_DIR/quality_failures.txt" "⚠️ Quality Failures by Agent" "🔍" "$CYAN"
fi

# █████████████████████████████████████████████████████████████████████████████████
# 📚 SECTION 5: TRAINING & DEVELOPMENT INSIGHTS
# █████████████████████████████████████████████████████████████████████████████████

print_category "📚" "TRAINING & DEVELOPMENT INSIGHTS" "$BLUE"

# =============================================================================
# USE CASE 14: Training Needs Assessment
# =============================================================================
print_section "🎯" "USE CASE 14: TRAINING NEEDS ASSESSMENT" "$BLUE"

QUERY_14="SELECT 
    agent_name as agent,
    COUNT(*) as calls,
    ROUND(AVG(grading.total_score_percent), 1) as current_performance,
    COUNT(CASE WHEN grading.total_score_percent < 70 THEN 1 END) as needs_improvement
FROM call_analysis
WHERE FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) >= current_date - interval '30' day
GROUP BY agent_name
HAVING COUNT(*) >= 5
ORDER BY current_performance ASC;"

if execute_athena_query "$QUERY_14" "Training Needs Assessment" "$OUTPUT_DIR/training_needs.txt"; then
    format_table_output "$OUTPUT_DIR/training_needs.txt" "🎯 Training Needs Assessment" "📚" "$BLUE"
fi

# =============================================================================
# USE CASE 15: Performance Issues by Agent
# =============================================================================
print_section "📋" "USE CASE 15: PERFORMANCE ISSUES BY AGENT" "$BLUE"

QUERY_15="SELECT 
    agent_name as agent,
    COUNT(*) as total_calls,
    COUNT(CASE WHEN grading.total_score_percent < 70 THEN 1 END) as needs_training,
    COUNT(CASE WHEN sentiment_analysis.customer_satisfaction < 0.5 THEN 1 END) as low_satisfaction,
    COUNT(CASE WHEN script_adherence.adherence_percentage < 80 THEN 1 END) as script_issues,
    COUNT(CASE WHEN call_metrics.customer_interruption_count > 3 THEN 1 END) as communication_issues,
    ROUND(AVG(grading.total_score_percent), 1) as avg_performance
FROM call_analysis
WHERE year = CAST(year(current_date) AS VARCHAR)
GROUP BY agent_name
HAVING COUNT(CASE WHEN grading.total_score_percent < 70 THEN 1 END) > 0
ORDER BY needs_training DESC
LIMIT 15;"

if execute_athena_query "$QUERY_15" "Performance Issues Analysis" "$OUTPUT_DIR/performance_recommendations.txt"; then
    format_table_output "$OUTPUT_DIR/performance_recommendations.txt" "📋 Performance Issues by Agent" "💡" "$BLUE"
fi

# █████████████████████████████████████████████████████████████████████████████████
# 💬 SECTION 6: COMMUNICATION & BEHAVIORAL ANALYSIS
# █████████████████████████████████████████████████████████████████████████████████

print_category "💬" "COMMUNICATION & BEHAVIORAL ANALYSIS" "$WHITE"

# =============================================================================
# USE CASE 16: Talk-to-Listen Ratio Analysis
# =============================================================================
print_section "🗣️" "USE CASE 16: TALK-TO-LISTEN RATIO ANALYSIS" "$WHITE"

QUERY_16="SELECT 
    CASE 
        WHEN call_metrics.talk_to_listen_ratio <= 0.4 THEN 'Mostly Listening (<=0.4)'
        WHEN call_metrics.talk_to_listen_ratio <= 0.6 THEN 'Balanced (0.4-0.6)'
        WHEN call_metrics.talk_to_listen_ratio <= 0.8 THEN 'Talk Heavy (0.6-0.8)'
        ELSE 'Very Talk Heavy (>0.8)'
    END as conversation_style,
    COUNT(*) as call_count,
    ROUND(AVG(grading.total_score_percent), 1) as avg_quality,
    ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as avg_csat,
    ROUND(AVG(deal_potential.probability), 2) as avg_deal_prob
FROM call_analysis
WHERE call_metrics.talk_to_listen_ratio IS NOT NULL
  AND year = CAST(year(current_date) AS VARCHAR)
GROUP BY 
    CASE 
        WHEN call_metrics.talk_to_listen_ratio <= 0.4 THEN 'Mostly Listening (<=0.4)'
        WHEN call_metrics.talk_to_listen_ratio <= 0.6 THEN 'Balanced (0.4-0.6)'
        WHEN call_metrics.talk_to_listen_ratio <= 0.8 THEN 'Talk Heavy (0.6-0.8)'
        ELSE 'Very Talk Heavy (>0.8)'
    END
ORDER BY avg_csat DESC;"

if execute_athena_query "$QUERY_16" "Talk-to-Listen Ratio Analysis" "$OUTPUT_DIR/talk_listen_ratio.txt"; then
    format_table_output "$OUTPUT_DIR/talk_listen_ratio.txt" "🗣️ Talk-to-Listen Ratio Analysis" "🎧" "$WHITE"
fi

# =============================================================================
# USE CASE 17: Customer Interruption Pattern Analysis
# =============================================================================
print_section "✋" "USE CASE 17: CUSTOMER INTERRUPTION PATTERN ANALYSIS" "$WHITE"

QUERY_17="SELECT 
    agent_name as agent,
    COUNT(*) as calls,
    ROUND(AVG(call_metrics.customer_interruption_count), 1) as avg_interruptions,
    COUNT(CASE WHEN call_metrics.customer_interruption_count >= 5 THEN 1 END) as high_interrupt_calls,
    ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as avg_csat,
    ROUND(AVG(grading.total_score_percent), 1) as avg_quality
FROM call_analysis
WHERE call_metrics.customer_interruption_count IS NOT NULL
  AND year = CAST(year(current_date) AS VARCHAR)
GROUP BY agent_name
HAVING COUNT(*) >= 10
ORDER BY avg_interruptions DESC;"

if execute_athena_query "$QUERY_17" "Customer Interruption Pattern Analysis" "$OUTPUT_DIR/interruption_patterns.txt"; then
    format_table_output "$OUTPUT_DIR/interruption_patterns.txt" "✋ Customer Interruption Patterns" "⚠️" "$WHITE"
fi

# █████████████████████████████████████████████████████████████████████████████████
# 📈 SECTION 7: OPERATIONAL EXCELLENCE
# █████████████████████████████████████████████████████████████████████████████████

print_category "📈" "OPERATIONAL EXCELLENCE" "$GREEN"

# =============================================================================
# USE CASE 18: Call Duration vs Quality Correlation
# =============================================================================
print_section "⏱️" "USE CASE 18: CALL DURATION VS QUALITY CORRELATION" "$GREEN"

QUERY_18="WITH call_duration_parsed AS (
    SELECT *,
        CASE 
            WHEN regexp_extract(call_duration, '(\\d+\\.?\\d*)', 1) != '' 
            THEN CAST(regexp_extract(call_duration, '(\\d+\\.?\\d*)', 1) AS DOUBLE)
            ELSE NULL
        END as duration_minutes
    FROM call_analysis
    WHERE year = CAST(year(current_date) AS VARCHAR)
)
SELECT 
    CASE 
        WHEN duration_minutes <= 5 THEN 'Very Short (<=5 min)'
        WHEN duration_minutes <= 10 THEN 'Short (5-10 min)'
        WHEN duration_minutes <= 15 THEN 'Medium (10-15 min)'
        WHEN duration_minutes <= 20 THEN 'Long (15-20 min)'
        ELSE 'Very Long (>20 min)'
    END as duration_category,
    COUNT(*) as call_count,
    ROUND(AVG(grading.total_score_percent), 1) as avg_quality,
    ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as avg_csat,
    ROUND(AVG(deal_potential.probability), 2) as avg_deal_prob
FROM call_duration_parsed
WHERE duration_minutes IS NOT NULL
GROUP BY 
    CASE 
        WHEN duration_minutes <= 5 THEN 'Very Short (<=5 min)'
        WHEN duration_minutes <= 10 THEN 'Short (5-10 min)'
        WHEN duration_minutes <= 15 THEN 'Medium (10-15 min)'
        WHEN duration_minutes <= 20 THEN 'Long (15-20 min)'
        ELSE 'Very Long (>20 min)'
    END
ORDER BY avg_quality DESC;"

if execute_athena_query "$QUERY_18" "Call Duration vs Quality Correlation" "$OUTPUT_DIR/duration_quality.txt"; then
    format_table_output "$OUTPUT_DIR/duration_quality.txt" "⏱️ Call Duration vs Quality" "📊" "$GREEN"
fi

# =============================================================================
# USE CASE 19: S3 Data Completeness Audit
# =============================================================================
print_section "🔍" "USE CASE 19: S3 DATA COMPLETENESS AUDIT" "$GREEN"

QUERY_19="SELECT 
    year,
    month,
    COUNT(*) as total_calls,
    COUNT(transcript_s3_uri) as has_transcript,
    COUNT(sfdc_action_s3_uri) as has_sfdc_action,
    COUNT(diarized_s3_uri) as has_diarized,
    ROUND(COUNT(transcript_s3_uri) * 100.0 / COUNT(*), 1) as transcript_completeness,
    ROUND(COUNT(sfdc_action_s3_uri) * 100.0 / COUNT(*), 1) as sfdc_completeness,
    ROUND(COUNT(diarized_s3_uri) * 100.0 / COUNT(*), 1) as diarized_completeness,
    COUNT(CASE WHEN transcript_s3_uri IS NOT NULL AND sfdc_action_s3_uri IS NOT NULL AND diarized_s3_uri IS NOT NULL THEN 1 END) as complete_records
FROM call_analysis
WHERE year = CAST(year(current_date) AS VARCHAR)
GROUP BY year, month
ORDER BY year DESC, month DESC;"

if execute_athena_query "$QUERY_19" "S3 Data Completeness Audit" "$OUTPUT_DIR/data_completeness.txt"; then
    format_table_output "$OUTPUT_DIR/data_completeness.txt" "🔍 S3 Data Completeness Audit" "📋" "$GREEN"
fi

# =============================================================================
# USE CASE 20: Peak Performance Period Analysis
# =============================================================================
print_section "⏰" "USE CASE 20: PEAK PERFORMANCE PERIOD ANALYSIS" "$GREEN"

QUERY_20="SELECT 
    EXTRACT(hour FROM FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', ''))) as call_hour,
    COUNT(*) as call_count,
    ROUND(AVG(grading.total_score_percent), 1) as avg_quality,
    ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as avg_csat,
    ROUND(AVG(deal_potential.probability), 2) as avg_deal_prob,
    RANK() OVER (ORDER BY AVG(grading.total_score_percent) DESC) as quality_rank
FROM call_analysis
WHERE FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')) >= current_date - interval '30' day
GROUP BY EXTRACT(hour FROM FROM_ISO8601_TIMESTAMP(REGEXP_REPLACE(call_date, '\\.[0-9]+', '')))
HAVING COUNT(*) >= 5
ORDER BY avg_quality DESC
LIMIT 20;"

if execute_athena_query "$QUERY_20" "Peak Performance Period Analysis" "$OUTPUT_DIR/peak_performance.txt"; then
    format_table_output "$OUTPUT_DIR/peak_performance.txt" "⏰ Peak Performance Periods" "🏆" "$GREEN"
fi

# =============================================================================
# EXECUTIVE SUMMARY
# =============================================================================
create_summary_stats "$OUTPUT_DIR"

# =============================================================================
# COMPLETION SUMMARY
# =============================================================================
print_header "🎉" "DASHBOARD GENERATION COMPLETED" "$GREEN"

echo -e "${WHITE}${BOLD}📁 All results saved to: ${GREEN}$OUTPUT_DIR/${NC}"
echo ""
echo -e "${WHITE}${BOLD}📋 Generated Reports (20 Use Cases):${NC}"
echo ""
echo -e "${GREEN}📊 Performance Monitoring & KPIs:${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/call_volume_last_week.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/agent_performance.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/agent_daily_performance.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/quality_distribution.txt${NC}"
echo ""
echo -e "${PURPLE}🎯 Sales & Revenue Intelligence:${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/sales_pipeline.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/high_value_deals.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/call_type_performance.txt${NC}"
echo ""
echo -e "${YELLOW}😊 Customer Experience & Sentiment:${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/satisfaction_trends_weekly.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/sentiment_by_agent.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/low_satisfaction_calls.txt${NC}"
echo ""
echo -e "${CYAN}⚖️ Compliance & Quality Assurance:${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/pdpa_compliance.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/script_adherence.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/quality_failures.txt${NC}"
echo ""
echo -e "${BLUE}📚 Training & Development:${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/training_needs.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/performance_recommendations.txt${NC}"
echo ""
echo -e "${WHITE}💬 Communication & Behavioral:${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/talk_listen_ratio.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/interruption_patterns.txt${NC}"
echo ""
echo -e "${GREEN}📈 Operational Excellence:${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/duration_quality.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/data_completeness.txt${NC}"
echo -e "${GREEN}  ✅ $OUTPUT_DIR/peak_performance.txt${NC}"
echo ""

echo -e "${YELLOW}${BOLD}💡 Next Steps:${NC}"
echo -e "${WHITE}  • Review individual report files for detailed insights across all 20 use cases${NC}"
echo -e "${WHITE}  • Share results with stakeholders: management, training, compliance teams${NC}"
echo -e "${WHITE}  • Schedule regular dashboard updates based on business needs:${NC}"
echo -e "${GRAY}    - Daily: Call volume, agent performance, satisfaction trends${NC}"
echo -e "${GRAY}    - Weekly: Sales pipeline, compliance monitoring, quality analysis${NC}"
echo -e "${GRAY}    - Monthly: Training needs, recommendations, operational insights${NC}"
echo -e "${WHITE}  • Use insights for comprehensive business improvements:${NC}"
echo -e "${GRAY}    - Agent coaching and training programs${NC}"
echo -e "${GRAY}    - Sales process optimization${NC}"
echo -e "${GRAY}    - Customer experience enhancement${NC}"
echo -e "${GRAY}    - Compliance and quality assurance${NC}"
echo ""

echo -e "${BLUE}${BOLD}🔄 To regenerate this dashboard:${NC}"
echo -e "${GRAY}  bash $0 --database $DATABASE --s3-results $S3_RESULTS${NC}"
echo ""

print_header "✨" "COMPREHENSIVE 20-USE CASE CALL ANALYSIS DASHBOARD COMPLETE" "$GREEN"
