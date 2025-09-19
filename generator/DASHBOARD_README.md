# 📊 Starhub Call Analysis Dashboard

A comprehensive shell script that implements 5 critical business intelligence use cases from call analysis data with beautiful tabular formatting and comprehensive insights.

## 🚀 Quick Start

```bash
# Basic usage with defaults
bash call_analysis_dashboard.sh

# Custom database and output directory
bash call_analysis_dashboard.sh --database my-db --output-dir my-results

# Quiet mode (minimal output)
bash call_analysis_dashboard.sh --quiet

# Show help
bash call_analysis_dashboard.sh --help
```

## 📋 Implemented Use Cases

### 1. 📈 **Overall Calls Volume Analysis - Last Week**
- **Business Value**: Monitor call volume trends and capacity planning
- **Output**: Daily breakdown of call volumes, quality scores, and satisfaction rates
- **File**: `dashboard_results/call_volume_last_week.txt`

### 2. 👤 **Agent-wise Performance Summary** 
- **Business Value**: Identify top performers and coaching needs
- **Output**: Comprehensive agent rankings with quality metrics and pipeline values
- **File**: `dashboard_results/agent_performance.txt`

### 3. 😊 **Customer Satisfaction Trends**
- **Business Value**: Monitor customer experience over time
- **Output**: Weekly satisfaction trends with high/low satisfaction call counts
- **File**: `dashboard_results/satisfaction_trends.txt`

### 4. 💰 **Sales Pipeline Value Analysis**
- **Business Value**: Track revenue opportunities from calls
- **Output**: Pipeline values by agent and call type with probability weightings
- **File**: `dashboard_results/sales_pipeline.txt`

### 5. ⚖️ **PDPA Compliance Monitoring**
- **Business Value**: Ensure data protection compliance
- **Output**: Monthly compliance rates by agent with violation tracking
- **File**: `dashboard_results/pdpa_compliance.txt`

## 🎨 Features

✅ **Beautiful Formatting**: Color-coded output with icons and comprehensive tables  
✅ **Error Handling**: Graceful error handling with detailed feedback  
✅ **Progress Tracking**: Real-time query execution progress with visual indicators  
✅ **Configurable**: Customizable database, S3 paths, and output directories  
✅ **Production Ready**: Optimized Athena queries with proper filtering and limits  

## 📁 Output Structure

```
dashboard_results/
├── call_volume_last_week.txt    # Use Case 1: Call volume analysis
├── agent_performance.txt        # Use Case 2: Agent performance
├── satisfaction_trends.txt      # Use Case 3: Customer satisfaction
├── sales_pipeline.txt          # Use Case 4: Sales pipeline analysis
└── pdpa_compliance.txt         # Use Case 5: Compliance monitoring
```

## 🛠 Requirements

- **AWS CLI** configured with valid credentials
- **Amazon Athena** access to database `starhub-poc`
- **S3 permissions** for query results storage
- **Linux/Unix** environment with bash

## ⚙️ Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--database` | `starhub-poc` | Athena database name |
| `--s3-results` | `s3://starhub-totogi-poc/athena-results/` | S3 path for query results |
| `--output-dir` | `dashboard_results` | Local directory for output files |
| `--quiet` | `false` | Suppress progress messages |

## 🔍 Sample Output Preview

```
════════════════════════════════════════════════════════════════════════════════
📊 STARHUB CALL ANALYSIS DASHBOARD
════════════════════════════════════════════════════════════════════════════════

Configuration:
  Database: starhub-poc
  S3 Results: s3://starhub-totogi-poc/athena-results/
  Output Directory: dashboard_results

📈 USE CASE 1: OVERALL CALLS VOLUME ANALYSIS - LAST WEEK
────────────────────────────────────────────────────────────────────────────
  ⚡ Executing: Call Volume Analysis - Last Week...
  ✅ Completed successfully

📊 Call Volume Analysis - Last 7 Days
+------------+-------------+---------------+-------------------+-----------------+
| call_day   | total_calls | passing_calls | avg_quality_score | avg_satisfaction|
+------------+-------------+---------------+-------------------+-----------------+
| 2025-08-22 | 45          | 32            | 78.5              | 0.72            |
| 2025-08-21 | 52          | 38            | 81.2              | 0.75            |
...
```

## 📊 Business Intelligence Insights

Each report provides actionable insights:

- **Performance Monitoring**: Track KPIs and identify trends
- **Agent Development**: Spot coaching opportunities and top performers  
- **Customer Experience**: Monitor satisfaction and sentiment patterns
- **Revenue Optimization**: Analyze sales pipeline and deal probabilities
- **Risk Management**: Ensure compliance and data protection standards

## 🔄 Automation

For automated reporting, schedule with cron:

```bash
# Daily dashboard at 8 AM
0 8 * * * /path/to/call_analysis_dashboard.sh --quiet

# Weekly summary on Mondays
0 9 * * 1 /path/to/call_analysis_dashboard.sh --output-dir weekly_reports
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| AWS CLI not found | Install AWS CLI: `apt install awscli` |
| Permission denied | Check AWS credentials: `aws sts get-caller-identity` |
| Query timeout | Verify Athena service limits and query complexity |
| No data returned | Check database name and table existence |
| S3 access denied | Verify S3 bucket permissions for query results |

## 🎯 Next Steps

1. **Regular Monitoring**: Schedule daily/weekly dashboard runs
2. **Stakeholder Sharing**: Distribute reports to management and teams
3. **Action Planning**: Use insights for coaching and process improvement
4. **Custom Analysis**: Extend with additional use cases as needed
5. **Integration**: Connect to BI tools for advanced visualization

---

**Created by**: AI Assistant  
**Version**: 1.0  
**Last Updated**: 2025-08-23
