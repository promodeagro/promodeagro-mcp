# Starhub Call Analysis Data Generator

This generator creates realistic sample call analysis data for the Starhub reporting architecture. It generates three types of files for each call:

1. **Call Analysis** (`call-id-analysis.json`) - Detailed analysis including grading, sentiment, and recommendations
2. **SFDC Actions** (`call-id-sfdcaction.json`) - Salesforce CRM actions and validations 
3. **Transcripts** (`call-id-transcript.json`) - Conversation transcripts with timestamps

The generated data follows the S3 partitioning structure for Athena analysis:
```
s3://starhub-totogi-poc/call-analysis/year=2025/month=01/day=17/
├── CHR-2025-001-analysis.json
├── CHR-2025-001-sfdcaction.json
└── CHR-2025-001-transcript.json
```

## Features

- ✅ Generates realistic call data matching production formats
- ✅ Supports multiple call types (upgrades, renewals, new inquiries, support, billing)
- ✅ Variable agent performance and customer scenarios
- ✅ Partitioned S3 structure for Athena compatibility 
- ✅ Local file generation and optional S3 upload
- ✅ Configurable date ranges and volume
- ✅ Realistic conversation transcripts
- ✅ Comprehensive grading and sentiment analysis

## Quick Start

### Prerequisites

1. Python 3.8+
2. AWS credentials (optional, for S3 upload)

### Installation

```bash
cd /opt/mycode/trilogy/starhub-mcp-server/generator
pip install -r requirements.txt
```

### Basic Usage

Generate 10 sample call records (local files only):
```bash
python call_data_generator.py
```

Generate 25 calls for the last 14 days:
```bash
python call_data_generator.py --num-calls 25 --days-back 14
```

Generate and upload to S3:
```bash
python call_data_generator.py --num-calls 50 --upload-s3
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--num-calls` | Number of call records to generate | 10 |
| `--days-back` | Generate calls for the last N days | 7 |
| `--s3-bucket` | S3 bucket name | starhub-totogi-poc |
| `--local-only` | Only save locally, don't upload to S3 | False |
| `--upload-s3` | Upload to S3 (requires AWS credentials) | False |

## Generated Data Structure

### Call Analysis JSON
Contains comprehensive call performance data:
- **Call metadata**: ID, date, duration, participants
- **Grading**: 16 weighted performance elements with scores
- **Compliance**: PDPA and other regulatory checks
- **Sentiment analysis**: Overall sentiment and key moments
- **Qualifying questions**: Asked and missed questions
- **Call metrics**: Talk ratios, interruptions, pace, clarity
- **Recommendations**: Performance improvement suggestions
- **Deal potential**: Value estimation and next steps

### SFDC Actions JSON
Tracks Salesforce CRM integration:
- **Metadata**: Call processing information
- **Validation**: Customer verification and requirements
- **Actions**: Records created/updated in Salesforce
- **Search results**: Existing contact/account matches
- **Next actions**: Follow-up tasks and timelines

### Transcript JSON
Detailed conversation flow:
- **Turn-by-turn dialogue**: Agent and customer exchanges
- **Timestamps**: Precise timing for each statement
- **Speaker identification**: Agent and customer IDs
- **Confidence scores**: Transcript accuracy ratings
- **Duration tracking**: Length of each speaking turn

## Sample Output Structure

```
output/
└── call-analysis/
    └── year=2025/
        └── month=01/
            └── day=17/
                ├── CHR-2025-001-analysis.json
                ├── CHR-2025-001-sfdcaction.json
                ├── CHR-2025-001-transcript.json
                ├── CHR-2025-002-analysis.json
                ├── CHR-2025-002-sfdcaction.json
                └── CHR-2025-002-transcript.json
```

## AWS S3 Setup

To upload directly to S3, configure your AWS credentials:

### Method 1: AWS CLI
```bash
aws configure
```

### Method 2: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=ap-southeast-1
```

### Method 3: IAM Role
If running on EC2, use an IAM role with S3 permissions.

## Athena Table Creation

After generating data, create an Athena table to query the results:

```sql
CREATE EXTERNAL TABLE call_analysis (
  call_id string,
  call_date string,
  agent_name string,
  customer_company string,
  call_duration string,
  call_type string,
  compliance struct<
    pdpa_pass: boolean,
    breaches: array<string>
  >,
  grading struct<
    total_score_percent: double,
    pass: boolean,
    elements: array<struct<
      element: string,
      weight: int,
      score: int,
      evidence: string
    >>
  >,
  sentiment_analysis struct<
    overall_sentiment: double,
    customer_satisfaction: double,
    sentiment_progression: array<double>
  >,
  deal_potential struct<
    estimated_value: int,
    probability: double,
    risk_factors: array<string>,
    next_steps: array<string>
  >
)
PARTITIONED BY (
  year int,
  month int, 
  day int
)
STORED AS JSON
LOCATION 's3://starhub-totogi-poc/call-analysis/'
```

## Example Queries

### Agent Performance Summary
```sql
SELECT 
  agent_name,
  COUNT(*) as total_calls,
  AVG(grading.total_score_percent) as avg_score,
  AVG(sentiment_analysis.customer_satisfaction) as avg_satisfaction,
  SUM(deal_potential.estimated_value) as total_pipeline
FROM call_analysis 
WHERE year = 2025 AND month = 1
GROUP BY agent_name
ORDER BY avg_score DESC;
```

### Daily Call Volume and Quality
```sql
SELECT 
  year, month, day,
  COUNT(*) as call_count,
  AVG(grading.total_score_percent) as avg_quality_score,
  SUM(CASE WHEN grading.pass = true THEN 1 ELSE 0 END) as passing_calls
FROM call_analysis
GROUP BY year, month, day
ORDER BY year, month, day;
```

### Compliance Issues
```sql
SELECT 
  call_id, agent_name, customer_company,
  compliance.pdpa_pass,
  compliance.breaches
FROM call_analysis 
WHERE compliance.pdpa_pass = false 
   OR cardinality(compliance.breaches) > 0;
```

## Customization

### Adding New Agents
Edit the `agents` list in `call_data_generator.py`:
```python
self.agents = [
    {"name": "YourAgent", "id": "agent-006"},
    # ... existing agents
]
```

### Adding New Call Types
Edit the `call_types` list and add corresponding templates:
```python
self.call_types = [
    "Your New Call Type",
    # ... existing types  
]
```

### Modifying Customer Data
Edit the `customers` list with your test customer data:
```python
self.customers = [
    {"name": "Customer", "email": "test@company.com", "company": "Test Corp"},
    # ... existing customers
]
```

## Troubleshooting

### Common Issues

**1. AWS Credentials Error**
```
Error: Unable to locate credentials
```
Solution: Configure AWS credentials using one of the methods above.

**2. S3 Permission Denied**
```
Error: Access Denied
```
Solution: Ensure your AWS user/role has `s3:PutObject` permissions for the bucket.

**3. Module Import Errors**
```
Error: No module named 'boto3'
```
Solution: Install requirements: `pip install -r requirements.txt`

### Verification

Check generated files:
```bash
# List generated files
ls -la output/call-analysis/year=2025/month=*/day=*/

# Validate JSON format
python -m json.tool output/call-analysis/year=2025/month=01/day=17/CHR-2025-001-analysis.json

# Check S3 uploads
aws s3 ls s3://starhub-totogi-poc/call-analysis/ --recursive
```

## Integration with BSS Magic Studio

This generator creates data that matches the expected format for:
- ✅ BSS Magic Studio call processing workflows
- ✅ S3-based data lake architecture  
- ✅ Athena table partitioning scheme
- ✅ Dashboard UI data consumption
- ✅ MCP Server fallback processing

The generated data can be used for:
- Testing dashboard visualizations
- Validating Athena queries
- Training machine learning models
- Load testing the reporting pipeline
- Demonstrating the complete solution

## Support

For questions or issues:
1. Check the troubleshooting section above
2. Verify your AWS credentials and permissions
3. Ensure all prerequisites are installed
4. Check the generated JSON files for format validation

---
**Generated by AI Assistant for Starhub MCP Server Project**
