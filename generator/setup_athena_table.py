#!/usr/bin/env python3
"""
Athena Table Setup Script for Starhub Call Analysis

This script helps create the Athena table and run basic validation queries
for the generated call analysis data.

Author: AI Assistant  
Date: 2025
"""

import boto3
import time
import json
from pathlib import Path
import argparse

class AthenaTableSetup:
    def __init__(self, database='starhub-poc', s3_results_location='s3://starhub-totogi-poc/athena-results/', force_recreate=False):
        self.athena_client = boto3.client('athena')
        self.database = database
        self.s3_results_location = s3_results_location
        self.force_recreate = force_recreate
        
    def execute_query(self, query_string, description="Query"):
        """Execute an Athena query and wait for results"""
        print(f"Executing: {description}")
        print(f"Query: {query_string[:100]}...")
        
        try:
            response = self.athena_client.start_query_execution(
                QueryString=query_string,
                QueryExecutionContext={'Database': self.database},
                ResultConfiguration={'OutputLocation': self.s3_results_location}
            )
            
            query_execution_id = response['QueryExecutionId']
            print(f"Query execution ID: {query_execution_id}")
            
            # Wait for query completion
            while True:
                response = self.athena_client.get_query_execution(
                    QueryExecutionId=query_execution_id
                )
                
                status = response['QueryExecution']['Status']['State']
                
                if status in ['SUCCEEDED']:
                    print(f"✅ {description} completed successfully")
                    return query_execution_id
                elif status in ['FAILED', 'CANCELLED']:
                    error = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                    print(f"❌ {description} failed: {error}")
                    return None
                else:
                    print(f"⏳ Status: {status} - waiting...")
                    time.sleep(2)
                    
        except Exception as e:
            print(f"❌ Error executing {description}: {str(e)}")
            return None
    
    def get_query_results(self, query_execution_id, max_results=10):
        """Get results from a completed query"""
        try:
            response = self.athena_client.get_query_results(
                QueryExecutionId=query_execution_id,
                MaxResults=max_results
            )
            
            # Extract column names
            columns = [col['Name'] for col in response['ResultSet']['ResultSetMetadata']['ColumnInfo']]
            
            # Extract data rows
            rows = []
            for row_data in response['ResultSet']['Rows'][1:]:  # Skip header row
                row = [field.get('VarCharValue', '') for field in row_data['Data']]
                rows.append(dict(zip(columns, row)))
            
            return rows
            
        except Exception as e:
            print(f"❌ Error getting query results: {str(e)}")
            return []
    
    def table_exists(self, table_name='call_analysis'):
        """Check if the specified table exists"""
        try:
            describe_query = f"DESCRIBE {table_name}"
            query_id = self.execute_query(describe_query, f"Check if {table_name} exists")
            return query_id is not None
        except Exception:
            return False
    
    def drop_table(self, table_name='call_analysis'):
        """Drop the specified table if it exists"""
        drop_query = f"DROP TABLE IF EXISTS {table_name}"
        query_id = self.execute_query(drop_query, f"Drop existing {table_name} table")
        return query_id is not None
    
    def get_user_confirmation(self, message):
        """Get user confirmation for an action"""
        if self.force_recreate:
            print(f"🔄 Force mode enabled: {message}")
            return True
            
        while True:
            response = input(f"\n{message} [y/N]: ").strip().lower()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no', '']:
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    def create_table(self, table_name='call_analysis'):
        """Create the call_analysis table with existence checking"""
        
        # Check if table already exists
        if self.table_exists(table_name):
            print(f"\n⚠️  Table '{table_name}' already exists in database '{self.database}'")
            
            if not self.get_user_confirmation(f"Do you want to recreate the table '{table_name}'? This will delete all existing data."):
                print(f"❌ Table creation cancelled by user.")
                return False
            
            # Drop existing table
            print(f"\n🗑️  Dropping existing table '{table_name}'...")
            if not self.drop_table(table_name):
                print(f"❌ Failed to drop existing table '{table_name}'")
                return False
        
        # Create new table
        ddl_file = Path(__file__).parent / "create_athena_table.sql"
        
        if not ddl_file.exists():
            print(f"❌ DDL file not found: {ddl_file}")
            return False
            
        with open(ddl_file, 'r') as f:
            ddl_query = f.read()
        
        # Replace table name if not default
        if table_name != 'call_analysis':
            ddl_query = ddl_query.replace('CREATE EXTERNAL TABLE call_analysis', f'CREATE EXTERNAL TABLE {table_name}')
        
        print(f"\n🛠️  Creating table '{table_name}'...")
        query_id = self.execute_query(ddl_query, f"Create {table_name} table")
        return query_id is not None
    
    def validate_table(self, table_name='call_analysis'):
        """Run validation queries against the table"""
        
        validation_queries = [
            {
                "name": "Table exists check",
                "query": f"DESCRIBE {table_name}",
                "description": "Verify table structure"
            },
            {
                "name": "Row count",
                "query": f"SELECT COUNT(*) as total_rows FROM {table_name}",
                "description": "Check total number of records"
            },
            {
                "name": "Date range",
                "query": f"""
                SELECT 
                    MIN(call_date) as earliest_call,
                    MAX(call_date) as latest_call,
                    COUNT(DISTINCT year) as unique_years,
                    COUNT(DISTINCT month) as unique_months,
                    COUNT(DISTINCT day) as unique_days
                FROM {table_name}
                """,
                "description": "Check date range and partitions"
            },
            {
                "name": "Agent summary",
                "query": f"""
                SELECT 
                    agent_name,
                    COUNT(*) as calls,
                    ROUND(AVG(grading.total_score_percent), 2) as avg_score
                FROM {table_name} 
                GROUP BY agent_name 
                ORDER BY calls DESC
                """,
                "description": "Agent performance summary"
            },
            {
                "name": "Call type distribution", 
                "query": f"""
                SELECT 
                    call_type,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
                FROM {table_name}
                GROUP BY call_type
                ORDER BY count DESC
                """,
                "description": "Distribution of call types"
            },
            {
                "name": "S3 URI validation",
                "query": f"""
                SELECT 
                    COUNT(*) as total_calls,
                    COUNT(transcript_s3_uri) as has_transcript_uri,
                    COUNT(sfdc_action_s3_uri) as has_sfdc_uri,
                    COUNT(diarized_s3_uri) as has_diarized_uri,
                    ROUND(COUNT(transcript_s3_uri) * 100.0 / COUNT(*), 1) as transcript_uri_percentage
                FROM {table_name}
                """,
                "description": "Check S3 URI field completeness"
            }
        ]
        
        print("\n🔍 Running validation queries...")
        print("=" * 50)
        
        for query_info in validation_queries:
            print(f"\n📊 {query_info['name']}: {query_info['description']}")
            query_id = self.execute_query(query_info['query'], query_info['name'])
            
            if query_id:
                results = self.get_query_results(query_id)
                if results:
                    print("Results:")
                    for i, row in enumerate(results[:5], 1):  # Show first 5 results
                        print(f"  {i}. {json.dumps(row, indent=4)}")
                    if len(results) > 5:
                        print(f"  ... and {len(results) - 5} more rows")
                else:
                    print("  No results returned")
            
            print("-" * 30)
        
    def repair_partitions(self, table_name='call_analysis'):
        """Add any missing partitions to the table"""
        repair_query = f"MSCK REPAIR TABLE {table_name}"
        query_id = self.execute_query(repair_query, f"Repair {table_name} partitions")
        return query_id is not None

    def show_sample_queries(self):
        """Display some useful sample queries"""
        sample_queries_file = Path(__file__).parent / "sample_queries.sql"
        
        if sample_queries_file.exists():
            print("\n📝 Sample queries are available in:")
            print(f"   {sample_queries_file}")
            print("\nSome useful queries to try:")
            print("1. Agent performance summary")
            print("2. Quality score distribution") 
            print("3. Customer satisfaction trends")
            print("4. Pipeline value analysis")
            print("5. S3 URI validation and file linkage queries")
            print("\nOpen sample_queries.sql for complete examples!")
        else:
            print("❌ Sample queries file not found")

def main():
    parser = argparse.ArgumentParser(description="Setup Athena table for Starhub call analysis")
    parser.add_argument("--database", default="starhub-poc", help="Athena database name")
    parser.add_argument("--s3-results", default="s3://starhub-totogi-poc/athena-results/", 
                       help="S3 location for Athena query results")
    parser.add_argument("--table-name", default="call_analysis", help="Name of the table to create/validate")
    parser.add_argument("--create-only", action="store_true", help="Only create table, skip validation")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing table")
    parser.add_argument("--repair-partitions", action="store_true", help="Repair table partitions")
    parser.add_argument("--force", action="store_true", help="Force recreate table without confirmation")
    
    args = parser.parse_args()
    
    print("🚀 Starhub Athena Table Setup")
    print("=" * 40)
    print(f"Database: {args.database}")
    print(f"Table: {args.table_name}")
    print(f"S3 Results: {args.s3_results}")
    print(f"Force Mode: {'Yes' if args.force else 'No'}")
    print()
    
    setup = AthenaTableSetup(database=args.database, s3_results_location=args.s3_results, force_recreate=args.force)
    
    if args.validate_only:
        setup.validate_table(args.table_name)
    elif args.repair_partitions:
        setup.repair_partitions(args.table_name)
    else:
        # Create table
        if setup.create_table(args.table_name):
            print(f"✅ Table '{args.table_name}' created successfully!")
            
            # Add partitions
            if setup.repair_partitions(args.table_name):
                print("✅ Partitions repaired!")
            
            # Run validation unless create-only is specified
            if not args.create_only:
                setup.validate_table(args.table_name)
        else:
            print(f"❌ Failed to create table '{args.table_name}'")
            return
    
    # Show sample queries info
    setup.show_sample_queries()
    
    print("\n🎉 Setup complete!")
    print(f"You can now query your call analysis data in Athena using the '{args.table_name}' table.")

if __name__ == "__main__":
    main()
