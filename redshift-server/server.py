#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#     "fastmcp>=2.10",
#     "uvicorn>=0.35",
#     "boto3>=1.35",
#     "pydantic>=2.11",
#     "starlette>=0.40"
# ]
# ///
"""
AWS Redshift MCP Server - Enterprise data access with governance controls

This MCP server provides secure access to AWS Redshift clusters for enterprise
AI agent governance demonstrations. Implements read-only access patterns with
comprehensive security controls.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("AWS Redshift MCP Server")

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
REDSHIFT_CLUSTER_ID = os.getenv('REDSHIFT_CLUSTER_ID')
REDSHIFT_DATABASE = os.getenv('REDSHIFT_DATABASE')
REDSHIFT_USER = os.getenv('REDSHIFT_USER')

# Mock data for demo purposes when AWS credentials not available
MOCK_MODE = os.getenv('MOCK_MODE', 'true').lower() == 'true'

class RedshiftClient:
    """Wrapper for AWS Redshift operations with mock fallback"""
    
    def __init__(self):
        self.mock_mode = MOCK_MODE
        self.redshift_client = None
        self.redshift_data_client = None
        
        if not self.mock_mode:
            try:
                # Initialize AWS clients
                self.redshift_client = boto3.client('redshift', region_name=AWS_REGION)
                self.redshift_data_client = boto3.client('redshift-data', region_name=AWS_REGION)
                logger.info("AWS Redshift clients initialized successfully")
            except NoCredentialsError:
                logger.warning("AWS credentials not found, falling back to mock mode")
                self.mock_mode = True
        else:
            logger.info("Running in mock mode for demo purposes")
    
    def get_mock_clusters(self) -> List[Dict[str, Any]]:
        """Generate mock cluster data for demo"""
        return [
            {
                "ClusterIdentifier": "production-cluster",
                "NodeType": "dc2.large",
                "ClusterStatus": "available",
                "MasterUsername": "admin",
                "DBName": "production_db",
                "Endpoint": {
                    "Address": "production-cluster.abcd1234.us-east-1.redshift.amazonaws.com",
                    "Port": 5439
                },
                "VpcId": "vpc-1234567890abcdef0",
                "CreationTime": datetime.now(timezone.utc),
                "AutomatedSnapshotRetentionPeriod": 7,
                "PubliclyAccessible": False,
                "Encrypted": True
            },
            {
                "ClusterIdentifier": "analytics-cluster",
                "NodeType": "ra3.xlplus",
                "ClusterStatus": "available",
                "MasterUsername": "analytics_user",
                "DBName": "analytics_db",
                "Endpoint": {
                    "Address": "analytics-cluster.xyz9876.us-east-1.redshift.amazonaws.com",
                    "Port": 5439
                },
                "VpcId": "vpc-1234567890abcdef0",
                "CreationTime": datetime.now(timezone.utc),
                "AutomatedSnapshotRetentionPeriod": 1,
                "PubliclyAccessible": False,
                "Encrypted": True
            }
        ]
    
    def get_mock_databases(self) -> List[str]:
        """Generate mock database list"""
        return ["production_db", "analytics_db", "staging_db", "customer_data"]
    
    def get_mock_schemas(self, database: str) -> List[str]:
        """Generate mock schema list for a database"""
        base_schemas = ["public", "information_schema", "pg_catalog"]
        if "production" in database:
            return base_schemas + ["sales", "customers", "inventory", "finance"]
        elif "analytics" in database:
            return base_schemas + ["reports", "metrics", "aggregations", "ml_models"]
        else:
            return base_schemas + ["test_data", "staging"]
    
    def get_mock_tables(self, database: str, schema: str) -> List[Dict[str, str]]:
        """Generate mock table list for a schema"""
        if schema == "customers":
            return [
                {"table_name": "customer_profiles", "table_type": "TABLE"},
                {"table_name": "customer_segments", "table_type": "TABLE"},
                {"table_name": "customer_interactions", "table_type": "TABLE"},
                {"table_name": "pii_customer_data", "table_type": "TABLE"}  # Sensitive table
            ]
        elif schema == "sales":
            return [
                {"table_name": "transactions", "table_type": "TABLE"},
                {"table_name": "order_details", "table_type": "TABLE"},
                {"table_name": "product_catalog", "table_type": "TABLE"},
                {"table_name": "sales_metrics", "table_type": "VIEW"}
            ]
        elif schema == "finance":
            return [
                {"table_name": "revenue_data", "table_type": "TABLE"},
                {"table_name": "cost_centers", "table_type": "TABLE"},
                {"table_name": "budget_allocations", "table_type": "TABLE"}
            ]
        else:
            return [
                {"table_name": "sample_table", "table_type": "TABLE"},
                {"table_name": "test_view", "table_type": "VIEW"}
            ]
    
    def get_mock_columns(self, database: str, schema: str, table: str) -> List[Dict[str, Any]]:
        """Generate mock column definitions"""
        if table == "customer_profiles":
            return [
                {"column_name": "customer_id", "data_type": "integer", "is_nullable": "NO"},
                {"column_name": "email", "data_type": "varchar(255)", "is_nullable": "NO"},
                {"column_name": "first_name", "data_type": "varchar(100)", "is_nullable": "YES"},
                {"column_name": "last_name", "data_type": "varchar(100)", "is_nullable": "YES"},
                {"column_name": "created_at", "data_type": "timestamp", "is_nullable": "NO"}
            ]
        elif table == "pii_customer_data":
            return [
                {"column_name": "customer_id", "data_type": "integer", "is_nullable": "NO"},
                {"column_name": "ssn", "data_type": "varchar(11)", "is_nullable": "YES"},  # PII
                {"column_name": "phone_number", "data_type": "varchar(20)", "is_nullable": "YES"},  # PII
                {"column_name": "address", "data_type": "text", "is_nullable": "YES"}  # PII
            ]
        elif table == "transactions":
            return [
                {"column_name": "transaction_id", "data_type": "bigint", "is_nullable": "NO"},
                {"column_name": "customer_id", "data_type": "integer", "is_nullable": "NO"},
                {"column_name": "amount", "data_type": "decimal(10,2)", "is_nullable": "NO"},
                {"column_name": "transaction_date", "data_type": "timestamp", "is_nullable": "NO"}
            ]
        else:
            return [
                {"column_name": "id", "data_type": "integer", "is_nullable": "NO"},
                {"column_name": "name", "data_type": "varchar(255)", "is_nullable": "YES"},
                {"column_name": "created_at", "data_type": "timestamp", "is_nullable": "NO"}
            ]

# Initialize Redshift client
redshift = RedshiftClient()

@mcp.tool
async def list_clusters() -> str:
    """List available Redshift clusters with basic information"""
    try:
        if redshift.mock_mode:
            clusters = redshift.get_mock_clusters()
        else:
            response = redshift.redshift_client.describe_clusters()
            clusters = response['Clusters']
        
        cluster_info = []
        for cluster in clusters:
            info = {
                "cluster_id": cluster.get("ClusterIdentifier", "unknown"),
                "status": cluster.get("ClusterStatus", "unknown"),
                "node_type": cluster.get("NodeType", "unknown"),
                "database": cluster.get("DBName", "unknown"),
                "endpoint": cluster.get("Endpoint", {}).get("Address", "unknown"),
                "encrypted": cluster.get("Encrypted", False),
                "publicly_accessible": cluster.get("PubliclyAccessible", False)
            }
            cluster_info.append(info)
        
        return json.dumps({
            "status": "success",
            "clusters": cluster_info,
            "total_count": len(cluster_info),
            "mode": "mock" if redshift.mock_mode else "live"
        }, indent=2, default=str)
        
    except Exception as e:
        logger.error(f"Error listing clusters: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "message": "Failed to retrieve cluster information"
        })

@mcp.tool
async def list_databases() -> str:
    """List available databases in Redshift clusters"""
    try:
        if redshift.mock_mode:
            databases = redshift.get_mock_databases()
        else:
            # In real implementation, would query information_schema
            databases = ["dev", "prod", "analytics"]
        
        return json.dumps({
            "status": "success",
            "databases": databases,
            "total_count": len(databases),
            "mode": "mock" if redshift.mock_mode else "live"
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error listing databases: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "message": "Failed to retrieve database information"
        })

@mcp.tool
async def list_schemas(database: str) -> str:
    """List available schemas in a specific database"""
    try:
        if redshift.mock_mode:
            schemas = redshift.get_mock_schemas(database)
        else:
            # In real implementation, would query information_schema.schemata
            schemas = ["public", "information_schema", "pg_catalog"]
        
        return json.dumps({
            "status": "success",
            "database": database,
            "schemas": schemas,
            "total_count": len(schemas),
            "mode": "mock" if redshift.mock_mode else "live"
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error listing schemas for database {database}: {e}")
        return json.dumps({
            "status": "error",
            "database": database,
            "error": str(e),
            "message": f"Failed to retrieve schema information for database {database}"
        })

@mcp.tool
async def list_tables(database: str, schema: str = "public") -> str:
    """List available tables and views in a specific schema"""
    try:
        if redshift.mock_mode:
            tables = redshift.get_mock_tables(database, schema)
        else:
            # In real implementation, would query information_schema.tables
            tables = [
                {"table_name": "sample_table", "table_type": "TABLE"},
                {"table_name": "sample_view", "table_type": "VIEW"}
            ]
        
        return json.dumps({
            "status": "success",
            "database": database,
            "schema": schema,
            "tables": tables,
            "total_count": len(tables),
            "mode": "mock" if redshift.mock_mode else "live"
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error listing tables for {database}.{schema}: {e}")
        return json.dumps({
            "status": "error",
            "database": database,
            "schema": schema,
            "error": str(e),
            "message": f"Failed to retrieve table information for {database}.{schema}"
        })

@mcp.tool
async def list_columns(database: str, schema: str, table: str) -> str:
    """List column definitions for a specific table"""
    try:
        if redshift.mock_mode:
            columns = redshift.get_mock_columns(database, schema, table)
        else:
            # In real implementation, would query information_schema.columns
            columns = [
                {"column_name": "id", "data_type": "integer", "is_nullable": "NO"},
                {"column_name": "name", "data_type": "varchar(255)", "is_nullable": "YES"}
            ]
        
        return json.dumps({
            "status": "success",
            "database": database,
            "schema": schema,
            "table": table,
            "columns": columns,
            "total_count": len(columns),
            "mode": "mock" if redshift.mock_mode else "live"
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error listing columns for {database}.{schema}.{table}: {e}")
        return json.dumps({
            "status": "error",
            "database": database,
            "schema": schema,
            "table": table,
            "error": str(e),
            "message": f"Failed to retrieve column information for {database}.{schema}.{table}"
        })

def validate_sql_query(query: str) -> tuple[bool, str]:
    """Basic SQL validation for security - only allow SELECT queries"""
    query_upper = query.strip().upper()
    
    # Block dangerous operations
    dangerous_keywords = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 
        'TRUNCATE', 'GRANT', 'REVOKE', 'COPY', 'UNLOAD'
    ]
    
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            return False, f"Query contains prohibited keyword: {keyword}"
    
    # Only allow SELECT statements
    if not query_upper.startswith('SELECT'):
        return False, "Only SELECT queries are allowed"
    
    # Basic length check
    if len(query) > 5000:
        return False, "Query too long (max 5000 characters)"
    
    return True, "Query validation passed"

@mcp.tool
async def execute_query(query: str, database: str = "production_db", limit: int = 100) -> str:
    """Execute a read-only SQL query with governance controls"""
    try:
        # Validate the query first
        is_valid, validation_message = validate_sql_query(query)
        if not is_valid:
            return json.dumps({
                "status": "blocked",
                "reason": "security_validation_failed",
                "message": validation_message,
                "query": query[:100] + "..." if len(query) > 100 else query
            })
        
        # Apply row limit
        limited_query = f"{query.rstrip(';')} LIMIT {min(limit, 1000)}"
        
        if redshift.mock_mode:
            # Generate mock results based on query content
            if "customer" in query.lower():
                mock_results = [
                    {"customer_id": 1001, "email": "john@example.com", "first_name": "John", "last_name": "Doe"},
                    {"customer_id": 1002, "email": "jane@example.com", "first_name": "Jane", "last_name": "Smith"},
                    {"customer_id": 1003, "email": "bob@example.com", "first_name": "Bob", "last_name": "Johnson"}
                ]
            elif "transaction" in query.lower():
                mock_results = [
                    {"transaction_id": 2001, "customer_id": 1001, "amount": 149.99, "transaction_date": "2024-01-15 10:30:00"},
                    {"transaction_id": 2002, "customer_id": 1002, "amount": 89.50, "transaction_date": "2024-01-15 14:22:00"},
                    {"transaction_id": 2003, "customer_id": 1001, "amount": 299.99, "transaction_date": "2024-01-16 09:15:00"}
                ]
            else:
                mock_results = [
                    {"id": 1, "name": "Sample Record 1", "created_at": "2024-01-01 12:00:00"},
                    {"id": 2, "name": "Sample Record 2", "created_at": "2024-01-02 12:00:00"}
                ]
            
            return json.dumps({
                "status": "success",
                "database": database,
                "query": limited_query,
                "results": mock_results,
                "row_count": len(mock_results),
                "execution_time_ms": 45,
                "mode": "mock",
                "security_note": "Query executed with read-only permissions and row limits"
            }, indent=2, default=str)
        
        else:
            # In real implementation, would use redshift.redshift_data_client.execute_statement
            return json.dumps({
                "status": "error",
                "message": "Real Redshift execution not implemented in demo",
                "suggestion": "Set MOCK_MODE=true for demo functionality"
            })
        
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "message": "Failed to execute query",
            "query": query[:100] + "..." if len(query) > 100 else query
        })

# Health check and info endpoints
@mcp.custom_route(path="/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint"""
    from starlette.responses import JSONResponse
    return JSONResponse({
        "status": "healthy",
        "service": "redshift-mcp-server",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "aws_region": AWS_REGION,
        "mock_mode": redshift.mock_mode,
        "available_tools": ["list_clusters", "list_databases", "list_schemas", "list_tables", "list_columns", "execute_query"]
    })

@mcp.custom_route(path="/info", methods=["GET"])
async def server_info(request):
    """Server information endpoint"""
    from starlette.responses import JSONResponse
    return JSONResponse({
        "name": "AWS Redshift MCP Server",
        "description": "Enterprise data access with governance controls",
        "version": "1.0.0",
        "available_tools": [
            "list_clusters",
            "list_databases", 
            "list_schemas",
            "list_tables",
            "list_columns",
            "execute_query"
        ],
        "security_features": [
            "Read-only query execution",
            "SQL injection prevention",
            "Row limit enforcement",
            "Query validation",
            "Dangerous operation blocking"
        ],
        "mock_mode": redshift.mock_mode,
        "aws_region": AWS_REGION
    })

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('SERVER_PORT', 8000))
    
    logger.info(f"Starting AWS Redshift MCP Server on port {port}")
    logger.info(f"Mock mode: {redshift.mock_mode}")
    logger.info(f"AWS Region: {AWS_REGION}")
    
    # Run with FastMCP
    mcp.run(transport="http", host="0.0.0.0", port=port)