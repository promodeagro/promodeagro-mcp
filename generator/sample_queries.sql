-- Sample Athena Queries for Starhub Call Analysis Data
-- Use these queries to analyze the generated call data
-- Updated for new S3 architecture with linked transcript, sfdcaction, and diarized files

-- =================================================================
-- 1. BASIC DATA EXPLORATION
-- =================================================================

-- Count total calls by date
SELECT year, month, day, COUNT(*) as call_count
FROM call_analysis 
WHERE year = '2025' 
GROUP BY year, month, day
ORDER BY year, month, day;

-- Overview of call types and volumes
SELECT 
  call_type,
  COUNT(*) as total_calls,
  AVG(grading.total_score_percent) as avg_score,
  COUNT(CASE WHEN grading.pass = true THEN 1 END) as passing_calls,
  ROUND(COUNT(CASE WHEN grading.pass = true THEN 1 END) * 100.0 / COUNT(*), 2) as pass_rate_percent
FROM call_analysis
WHERE year = '2025'
GROUP BY call_type
ORDER BY total_calls DESC;

-- =================================================================
-- 2. AGENT PERFORMANCE ANALYSIS  
-- =================================================================

-- Agent performance summary
SELECT 
  agent_name,
  COUNT(*) as total_calls,
  ROUND(AVG(grading.total_score_percent), 2) as avg_score,
  COUNT(CASE WHEN grading.pass = true THEN 1 END) as passing_calls,
  ROUND(COUNT(CASE WHEN grading.pass = true THEN 1 END) * 100.0 / COUNT(*), 2) as pass_rate,
  ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as avg_customer_satisfaction,
  ROUND(AVG(script_adherence.adherence_percentage), 2) as avg_script_adherence,
  SUM(deal_potential.estimated_value) as total_pipeline_value,
  ROUND(AVG(deal_potential.probability), 2) as avg_deal_probability
FROM call_analysis 
WHERE year = '2025'
GROUP BY agent_name
ORDER BY avg_score DESC;

-- Top performing agents by customer satisfaction
SELECT 
  agent_name,
  COUNT(*) as calls,
  ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as avg_satisfaction,
  ROUND(AVG(sentiment_analysis.overall_sentiment), 2) as avg_sentiment
FROM call_analysis
WHERE year = '2025'
GROUP BY agent_name
HAVING COUNT(*) >= 3  -- Only agents with 3+ calls
ORDER BY avg_satisfaction DESC;

-- =================================================================
-- 3. QUALITY AND COMPLIANCE MONITORING
-- =================================================================

-- Compliance issues summary
SELECT 
  COUNT(*) as total_calls,
  COUNT(CASE WHEN compliance.pdpa_pass = false THEN 1 END) as pdpa_failures,
  COUNT(CASE WHEN cardinality(compliance.breaches) > 0 THEN 1 END) as calls_with_breaches,
  ROUND(COUNT(CASE WHEN compliance.pdpa_pass = false THEN 1 END) * 100.0 / COUNT(*), 2) as pdpa_failure_rate
FROM call_analysis
WHERE year = '2025';

-- Calls with compliance issues
SELECT 
  call_id,
  agent_name,
  customer_company,
  call_date,
  compliance.pdpa_pass,
  compliance.breaches,
  grading.total_score_percent
FROM call_analysis 
WHERE year = '2025' 
  AND (compliance.pdpa_pass = false OR cardinality(compliance.breaches) > 0)
ORDER BY call_date DESC;

-- Quality score distribution
SELECT 
  CASE 
    WHEN grading.total_score_percent >= 90 THEN 'Excellent (90-100%)'
    WHEN grading.total_score_percent >= 80 THEN 'Good (80-89%)'
    WHEN grading.total_score_percent >= 70 THEN 'Acceptable (70-79%)'
    WHEN grading.total_score_percent >= 60 THEN 'Needs Improvement (60-69%)'
    ELSE 'Poor (<60%)'
  END as score_category,
  COUNT(*) as call_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM call_analysis
WHERE year = '2025'
GROUP BY 1
ORDER BY 
  CASE 
    WHEN grading.total_score_percent >= 90 THEN 1
    WHEN grading.total_score_percent >= 80 THEN 2
    WHEN grading.total_score_percent >= 70 THEN 3
    WHEN grading.total_score_percent >= 60 THEN 4
    ELSE 5
  END;

-- =================================================================
-- 4. GRADING ELEMENT ANALYSIS
-- =================================================================

-- Performance by grading element (requires unnesting)
SELECT 
  element.element,
  element.weight,
  COUNT(*) as total_evaluations,
  ROUND(AVG(element.score), 2) as avg_score,
  COUNT(CASE WHEN element.score >= 75 THEN 1 END) as good_performance_count,
  ROUND(COUNT(CASE WHEN element.score >= 75 THEN 1 END) * 100.0 / COUNT(*), 2) as good_performance_rate
FROM call_analysis
CROSS JOIN UNNEST(grading.elements) AS t(element)
WHERE year = '2025'
GROUP BY element.element, element.weight
ORDER BY avg_score DESC;

-- Lowest performing grading elements
SELECT 
  element.element,
  ROUND(AVG(element.score), 2) as avg_score,
  COUNT(CASE WHEN element.score = 0 THEN 1 END) as zero_score_count
FROM call_analysis
CROSS JOIN UNNEST(grading.elements) AS t(element)
WHERE year = '2025'
GROUP BY element.element
ORDER BY avg_score ASC
LIMIT 5;

-- =================================================================
-- 5. CUSTOMER SENTIMENT ANALYSIS
-- =================================================================

-- Sentiment trends by call type
SELECT 
  call_type,
  COUNT(*) as calls,
  ROUND(AVG(sentiment_analysis.overall_sentiment), 2) as avg_overall_sentiment,
  ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as avg_customer_satisfaction,
  COUNT(CASE WHEN sentiment_analysis.customer_satisfaction >= 0.7 THEN 1 END) as satisfied_customers,
  ROUND(COUNT(CASE WHEN sentiment_analysis.customer_satisfaction >= 0.7 THEN 1 END) * 100.0 / COUNT(*), 2) as satisfaction_rate
FROM call_analysis
WHERE year = '2025'
GROUP BY call_type
ORDER BY avg_customer_satisfaction DESC;

-- Calls with low customer satisfaction
SELECT 
  call_id,
  agent_name,
  customer_company,
  call_type,
  sentiment_analysis.overall_sentiment,
  sentiment_analysis.customer_satisfaction,
  grading.total_score_percent
FROM call_analysis
WHERE year = '2025' 
  AND sentiment_analysis.customer_satisfaction < 0.5
ORDER BY sentiment_analysis.customer_satisfaction ASC;

-- =================================================================
-- 6. BUSINESS IMPACT ANALYSIS
-- =================================================================

-- Pipeline value and conversion potential
SELECT 
  call_type,
  COUNT(*) as total_calls,
  SUM(deal_potential.estimated_value) as total_pipeline_value,
  ROUND(AVG(deal_potential.estimated_value), 0) as avg_deal_value,
  ROUND(AVG(deal_potential.probability), 2) as avg_conversion_probability,
  ROUND(SUM(deal_potential.estimated_value * deal_potential.probability), 0) as weighted_pipeline_value
FROM call_analysis
WHERE year = '2025'
GROUP BY call_type
ORDER BY weighted_pipeline_value DESC;

-- High-value opportunities with conversion risk
SELECT 
  call_id,
  agent_name,
  customer_company,
  call_type,
  deal_potential.estimated_value,
  deal_potential.probability,
  deal_potential.risk_factors,
  grading.total_score_percent
FROM call_analysis
WHERE year = '2025' 
  AND deal_potential.estimated_value > 50000
  AND deal_potential.probability < 0.6
ORDER BY deal_potential.estimated_value DESC;

-- =================================================================
-- 7. OPERATIONAL METRICS
-- =================================================================

-- Call duration and efficiency analysis
SELECT 
  agent_name,
  COUNT(*) as calls,
  AVG(CAST(REGEXP_REPLACE(call_duration, ' minutes', '') AS DOUBLE)) as avg_duration_minutes,
  ROUND(AVG(call_metrics.talk_to_listen_ratio), 2) as avg_talk_listen_ratio,
  ROUND(AVG(call_metrics.speaking_pace_wpm), 0) as avg_speaking_pace,
  ROUND(AVG(call_metrics.voice_clarity), 2) as avg_voice_clarity
FROM call_analysis
WHERE year = '2025'
GROUP BY agent_name
ORDER BY avg_duration_minutes;

-- Daily call volume and performance trends
SELECT 
  year, month, day,
  COUNT(*) as daily_calls,
  ROUND(AVG(grading.total_score_percent), 2) as avg_daily_score,
  ROUND(AVG(sentiment_analysis.customer_satisfaction), 2) as avg_daily_satisfaction,
  SUM(deal_potential.estimated_value) as daily_pipeline_value
FROM call_analysis
WHERE year = '2025'
GROUP BY year, month, day
ORDER BY year, month, day;

-- =================================================================
-- 8. TRAINING AND DEVELOPMENT INSIGHTS
-- =================================================================

-- Most common missed qualifying questions
SELECT 
  missed_question,
  COUNT(*) as frequency
FROM call_analysis
CROSS JOIN UNNEST(qualifying_questions.missed) AS t(missed_question)
WHERE year = '2025'
GROUP BY missed_question
ORDER BY frequency DESC;

-- Most frequent recommendations
SELECT 
  recommendation,
  COUNT(*) as frequency
FROM call_analysis
CROSS JOIN UNNEST(recommendations) AS t(recommendation) 
WHERE year = '2025'
GROUP BY recommendation
ORDER BY frequency DESC
LIMIT 10;

-- =================================================================
-- 7. S3 URIs AND LINKED DATA QUERIES
-- =================================================================

-- View S3 URIs for all related files
SELECT 
  call_id,
  agent_name,
  call_type,
  transcript_s3_uri,
  sfdc_action_s3_uri,
  diarized_s3_uri
FROM call_analysis
WHERE year = '2025'
LIMIT 10;

-- Calls with complete file linkage (all S3 URIs present)
SELECT 
  call_id,
  agent_name,
  customer_company,
  call_type,
  grading.total_score_percent as score,
  transcript_s3_uri IS NOT NULL as has_transcript,
  sfdc_action_s3_uri IS NOT NULL as has_sfdc_action,
  diarized_s3_uri IS NOT NULL as has_diarized
FROM call_analysis
WHERE year = '2025'
  AND transcript_s3_uri IS NOT NULL 
  AND sfdc_action_s3_uri IS NOT NULL
  AND diarized_s3_uri IS NOT NULL
ORDER BY grading.total_score_percent DESC
LIMIT 20;

-- File completeness report by agent
SELECT 
  agent_name,
  COUNT(*) as total_calls,
  COUNT(CASE WHEN transcript_s3_uri IS NOT NULL THEN 1 END) as has_transcript,
  COUNT(CASE WHEN sfdc_action_s3_uri IS NOT NULL THEN 1 END) as has_sfdc_action,
  COUNT(CASE WHEN diarized_s3_uri IS NOT NULL THEN 1 END) as has_diarized,
  ROUND(
    COUNT(CASE WHEN transcript_s3_uri IS NOT NULL AND sfdc_action_s3_uri IS NOT NULL AND diarized_s3_uri IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 
    2
  ) as complete_file_percentage
FROM call_analysis
WHERE year = '2025'
GROUP BY agent_name
ORDER BY complete_file_percentage DESC;

-- S3 bucket and path analysis
SELECT 
  SPLIT_PART(transcript_s3_uri, '/', 3) as s3_bucket,
  REGEXP_EXTRACT(transcript_s3_uri, 'transcript/(year=\d{4}/month=\d{2}/day=\d{2})') as date_partition,
  COUNT(*) as file_count
FROM call_analysis
WHERE year = '2025' 
  AND transcript_s3_uri IS NOT NULL
GROUP BY SPLIT_PART(transcript_s3_uri, '/', 3), 
         REGEXP_EXTRACT(transcript_s3_uri, 'transcript/(year=\d{4}/month=\d{2}/day=\d{2})')
ORDER BY date_partition DESC;
