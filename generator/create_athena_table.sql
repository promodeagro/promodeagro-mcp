-- Athena DDL for Starhub Call Analysis Table
-- This DDL creates an external table that reads JSON files from S3
-- Generated for use with the Starhub Call Data Generator
-- Updated for new S3 architecture with separate folders and S3 URIs

CREATE EXTERNAL TABLE call_analysis (
  call_id STRING,
  call_date STRING,
  transcript_file STRING,
  sfdcaction_file STRING,
  diarized_file STRING,
  transcript_s3_uri STRING,
  sfdc_action_s3_uri STRING,
  diarized_s3_uri STRING,
  agent_name STRING,
  customer_company STRING,
  call_duration STRING,
  call_type STRING,

  -- Compliance information
  compliance STRUCT<
    pdpa_pass: BOOLEAN,
    breaches: ARRAY<STRING>
  >,

  -- Call grading and performance scores
  grading STRUCT<
    total_score_percent: DOUBLE,
    pass: BOOLEAN,
    elements: ARRAY<
      STRUCT<
        element: STRING,
        weight: INT,
        score: INT,
        evidence: STRING
      >
    >
  >,

  -- Qualifying questions asked and missed
  qualifying_questions STRUCT<
    asked: ARRAY<STRUCT<question: STRING, answer: STRING>>,
    missed: ARRAY<STRING>
  >,

  -- Call quality metrics
  call_metrics STRUCT<
    talk_to_listen_ratio: DOUBLE,
    customer_interruption_count: INT,
    silence_periods: INT,
    speaking_pace_wpm: INT,
    energy_level: DOUBLE,
    voice_clarity: DOUBLE
  >,

  -- Sentiment analysis results
  sentiment_analysis STRUCT<
    overall_sentiment: DOUBLE,
    customer_satisfaction: DOUBLE,
    sentiment_progression: ARRAY<DOUBLE>,
    key_sentiment_moments: ARRAY<
      STRUCT<
        timestamp: STRING, 
        sentiment: DOUBLE, 
        context: STRING
      >
    >
  >,

  -- Script adherence tracking
  script_adherence STRUCT<
    adherence_percentage: INT,
    missed_elements: ARRAY<STRING>,
    well_executed: ARRAY<STRING>
  >,

  -- Performance recommendations
  recommendations ARRAY<STRING>,

  -- Deal potential and value estimation
  deal_potential STRUCT<
    estimated_value: INT,
    probability: DOUBLE,
    risk_factors: ARRAY<STRING>,
    next_steps: ARRAY<STRING>
  >
)
PARTITIONED BY (
  year STRING, 
  month STRING, 
  day STRING
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://starhub-totogi-poc/analysis/'
TBLPROPERTIES (
  'projection.enabled'='true',
  'projection.year.type'='integer',
  'projection.year.range'='2020,2030', 
  'projection.year.interval'='1',
  'projection.month.type'='integer',
  'projection.month.range'='1,12',
  'projection.month.interval'='1',
  'projection.month.digits'='2',
  'projection.day.type'='integer', 
  'projection.day.range'='1,31',
  'projection.day.interval'='1',
  'projection.day.digits'='2',
  'storage.location.template'='s3://starhub-totogi-poc/analysis/year=${year}/month=${month}/day=${day}/'
);
