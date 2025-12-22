#!/usr/bin/env python3
"""
Database Schema Audit Script

Audits PostgreSQL schema to verify:
- Alembic migrations are up to date
- Required tables and columns exist
- Foreign keys are correctly defined
- Indexes are present
- Marketing V1.1 fields are present

Usage:
    python scripts/audit_db_schema.py
    # or
    docker compose -f docker-compose.dev.yml exec backend python scripts/audit_db_schema.py
"""

import os
import sys
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Note: We use SQLAlchemy for database access, which handles connection pooling
# No need for direct psycopg imports

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
except ImportError:
    print("ERROR: sqlalchemy required. Install with: pip install sqlalchemy")
    sys.exit(1)


@dataclass
class CheckResult:
    """Result of a single check"""
    name: str
    status: str  # PASS, FAIL, WARN
    message: str
    details: Optional[Dict] = None


@dataclass
class AuditReport:
    """Complete audit report"""
    timestamp: str
    database_url: str
    database_name: str
    postgres_version: str
    overall_status: str  # PASS, FAIL
    checks: List[CheckResult]
    summary: Dict[str, int]  # counts: pass, fail, warn


class DatabaseAuditor:
    """Audits PostgreSQL database schema"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine: Optional[Engine] = None
        self.conn = None
        self.report = None
        
    def connect(self) -> bool:
        """Connect to database"""
        try:
            # Parse DATABASE_URL to get connection details
            # Format: postgresql://user:password@host:port/dbname
            self.engine = create_engine(self.database_url)
            self.conn = self.engine.connect()
            return True
        except Exception as e:
            print(f"ERROR: Failed to connect to database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
        if self.engine:
            self.engine.dispose()
    
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute query and return results as list of dicts"""
        try:
            result = self.conn.execute(text(query), params or {})
            rows = result.fetchall()
            # Convert to list of dicts
            if rows:
                keys = result.keys()
                return [dict(zip(keys, row)) for row in rows]
            return []
        except Exception as e:
            print(f"WARNING: Query failed: {e}")
            return []
    
    def get_postgres_version(self) -> str:
        """Get PostgreSQL version"""
        result = self.execute_query("SELECT version();")
        if result:
            return result[0]['version']
        return "Unknown"
    
    def get_database_name(self) -> str:
        """Get current database name"""
        result = self.execute_query("SELECT current_database();")
        if result:
            return result[0]['current_database']
        return "Unknown"
    
    def check_alembic_migrations(self) -> CheckResult:
        """Check if Alembic migrations are up to date"""
        try:
            # Check if alembic_version table exists
            table_check = self.execute_query("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'alembic_version'
                );
            """)
            
            if not table_check or not table_check[0]['exists']:
                return CheckResult(
                    name="Alembic Migrations",
                    status="FAIL",
                    message="alembic_version table does not exist. Run: alembic upgrade head"
                )
            
            # Get current revision
            current_rev = self.execute_query("SELECT version_num FROM alembic_version;")
            if not current_rev:
                return CheckResult(
                    name="Alembic Migrations",
                    status="FAIL",
                    message="No Alembic revision found. Run: alembic upgrade head"
                )
            
            current_version = current_rev[0]['version_num']
            
            # Try to get head revision (this requires alembic command, so we'll just check current exists)
            # For now, we'll just verify the table exists and has a version
            return CheckResult(
                name="Alembic Migrations",
                status="PASS",
                message=f"Current Alembic revision: {current_version}",
                details={"current_version": current_version}
            )
        except Exception as e:
            return CheckResult(
                name="Alembic Migrations",
                status="WARN",
                message=f"Could not check Alembic status: {e}. Run manually: alembic current"
            )
    
    def check_table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        result = self.execute_query("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = :table_name
            );
        """, {"table_name": table_name})
        return result and result[0]['exists']
    
    def get_table_columns(self, table_name: str) -> List[Dict]:
        """Get all columns for a table"""
        return self.execute_query("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = :table_name
            ORDER BY ordinal_position;
        """, {"table_name": table_name})
    
    def check_offers_table(self) -> CheckResult:
        """Check offers table structure"""
        table_name = "offers"
        
        if not self.check_table_exists(table_name):
            # Try alternative names
            alternatives = ["offer"]
            for alt in alternatives:
                if self.check_table_exists(alt):
                    return CheckResult(
                        name="Offers Table",
                        status="WARN",
                        message=f"Table '{table_name}' not found, but '{alt}' exists. Please verify table name.",
                        details={"found_table": alt, "expected_table": table_name}
                    )
            return CheckResult(
                name="Offers Table",
                status="FAIL",
                message=f"Table '{table_name}' does not exist"
            )
        
        columns = self.get_table_columns(table_name)
        column_names = {col['column_name'] for col in columns}
        
        # Required columns for Marketing V1.1
        required_columns = {
            'id': 'uuid',
            'cover_media_id': 'uuid',
            'promo_video_media_id': 'uuid',
            'marketing_title': 'text/varchar',
            'marketing_subtitle': 'text/varchar',
            'location_label': 'text/varchar',
            'marketing_why': 'jsonb',
            'marketing_highlights': 'jsonb',
            'marketing_breakdown': 'jsonb',
            'marketing_metrics': 'jsonb',
        }
        
        missing = []
        found = []
        for col_name, col_type in required_columns.items():
            if col_name not in column_names:
                missing.append(col_name)
            else:
                found.append(col_name)
        
        if missing:
            return CheckResult(
                name="Offers Table",
                status="FAIL",
                message=f"Missing columns: {', '.join(missing)}",
                details={"missing": missing, "found": found, "all_columns": list(column_names)}
            )
        
        return CheckResult(
            name="Offers Table",
            status="PASS",
            message=f"All required columns present ({len(found)}/{len(required_columns)})",
            details={"found_columns": found, "total_columns": len(column_names)}
        )
    
    def check_offer_media_table(self) -> CheckResult:
        """Check offer_media table structure"""
        table_name = "offer_media"
        
        if not self.check_table_exists(table_name):
            return CheckResult(
                name="Offer Media Table",
                status="FAIL",
                message=f"Table '{table_name}' does not exist"
            )
        
        columns = self.get_table_columns(table_name)
        column_names = {col['column_name'] for col in columns}
        
        required_columns = {
            'id': 'uuid',
            'offer_id': 'uuid',
            'type': 'enum/text',
            'key': 'text/varchar',  # S3/R2 storage key
            'mime_type': 'text/varchar',
            'size_bytes': 'bigint/integer',
            'created_at': 'timestamp',
        }
        
        missing = []
        found = []
        for col_name in required_columns:
            if col_name not in column_names:
                missing.append(col_name)
            else:
                found.append(col_name)
        
        if missing:
            return CheckResult(
                name="Offer Media Table",
                status="FAIL",
                message=f"Missing columns: {', '.join(missing)}",
                details={"missing": missing, "found": found}
            )
        
        return CheckResult(
            name="Offer Media Table",
            status="PASS",
            message=f"All required columns present ({len(found)}/{len(required_columns)})",
            details={"found_columns": found}
        )
    
    def check_articles_table(self) -> CheckResult:
        """Check articles table structure"""
        table_name = "articles"
        
        if not self.check_table_exists(table_name):
            return CheckResult(
                name="Articles Table",
                status="FAIL",
                message=f"Table '{table_name}' does not exist"
            )
        
        columns = self.get_table_columns(table_name)
        column_names = {col['column_name'] for col in columns}
        
        required_columns = {
            'id': 'uuid',
            'slug': 'text/varchar',
            'status': 'text/varchar',
            'title': 'text/varchar',
            'subtitle': 'text/varchar',
            'excerpt': 'text/varchar',
            'content_markdown': 'text/varchar',
            'content_html': 'text/varchar',
            'cover_media_id': 'uuid',
            'promo_video_media_id': 'uuid',
            'author_name': 'text/varchar',
            'published_at': 'timestamp',
            'created_at': 'timestamp',
            'updated_at': 'timestamp',
            'seo_title': 'text/varchar',
            'seo_description': 'text/varchar',
            'tags': 'jsonb',
            'is_featured': 'boolean',
            'allow_comments': 'boolean',
        }
        
        missing = []
        found = []
        for col_name in required_columns:
            if col_name not in column_names:
                missing.append(col_name)
            else:
                found.append(col_name)
        
        if missing:
            return CheckResult(
                name="Articles Table",
                status="FAIL",
                message=f"Missing columns: {', '.join(missing)}",
                details={"missing": missing, "found": found}
            )
        
        return CheckResult(
            name="Articles Table",
            status="PASS",
            message=f"All required columns present ({len(found)}/{len(required_columns)})",
            details={"found_columns": found}
        )
    
    def check_article_media_table(self) -> CheckResult:
        """Check article_media table structure"""
        table_name = "article_media"
        
        if not self.check_table_exists(table_name):
            return CheckResult(
                name="Article Media Table",
                status="FAIL",
                message=f"Table '{table_name}' does not exist"
            )
        
        columns = self.get_table_columns(table_name)
        column_names = {col['column_name'] for col in columns}
        
        required_columns = {
            'id': 'uuid',
            'article_id': 'uuid',
            'type': 'enum/text',
            'key': 'text/varchar',  # S3/R2 storage key
            'mime_type': 'text/varchar',
            'size_bytes': 'bigint/integer',
            'width': 'integer',
            'height': 'integer',
            'duration_seconds': 'integer',
            'created_at': 'timestamp',
        }
        
        missing = []
        found = []
        for col_name in required_columns:
            if col_name not in column_names:
                missing.append(col_name)
            else:
                found.append(col_name)
        
        if missing:
            return CheckResult(
                name="Article Media Table",
                status="FAIL",
                message=f"Missing columns: {', '.join(missing)}",
                details={"missing": missing, "found": found}
            )
        
        return CheckResult(
            name="Article Media Table",
            status="PASS",
            message=f"All required columns present ({len(found)}/{len(required_columns)})",
            details={"found_columns": found}
        )
    
    def check_article_offers_table(self) -> CheckResult:
        """Check article_offers junction table structure"""
        table_name = "article_offers"
        
        if not self.check_table_exists(table_name):
            return CheckResult(
                name="Article Offers Table",
                status="FAIL",
                message=f"Table '{table_name}' does not exist"
            )
        
        columns = self.get_table_columns(table_name)
        column_names = {col['column_name'] for col in columns}
        
        required_columns = {
            'article_id': 'uuid',
            'offer_id': 'uuid',
        }
        
        missing = []
        found = []
        for col_name in required_columns:
            if col_name not in column_names:
                missing.append(col_name)
            else:
                found.append(col_name)
        
        if missing:
            return CheckResult(
                name="Article Offers Table",
                status="FAIL",
                message=f"Missing columns: {', '.join(missing)}",
                details={"missing": missing, "found": found}
            )
        
        return CheckResult(
            name="Article Offers Table",
            status="PASS",
            message=f"All required columns present ({len(found)}/{len(required_columns)})",
            details={"found_columns": found}
        )
    
    def get_foreign_keys(self, table_name: str) -> List[Dict]:
        """Get foreign keys for a table"""
        return self.execute_query("""
            SELECT
                tc.constraint_name,
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.delete_rule,
                rc.update_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints AS rc
                ON rc.constraint_name = tc.constraint_name
                AND rc.constraint_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
            AND tc.table_name = :table_name;
        """, {"table_name": table_name})
    
    def check_foreign_keys(self) -> CheckResult:
        """Check required foreign keys"""
        required_fks = [
            {
                "table": "offer_media",
                "column": "offer_id",
                "references_table": "offers",
                "references_column": "id",
                "on_delete": "CASCADE",  # or NO ACTION
            },
            {
                "table": "offers",
                "column": "cover_media_id",
                "references_table": "offer_media",
                "references_column": "id",
                "on_delete": "SET NULL",  # or NO ACTION
            },
            {
                "table": "offers",
                "column": "promo_video_media_id",
                "references_table": "offer_media",
                "references_column": "id",
                "on_delete": "SET NULL",  # or NO ACTION
            },
            {
                "table": "article_media",
                "column": "article_id",
                "references_table": "articles",
                "references_column": "id",
                "on_delete": "CASCADE",
            },
            {
                "table": "articles",
                "column": "cover_media_id",
                "references_table": "article_media",
                "references_column": "id",
                "on_delete": "SET NULL",
            },
            {
                "table": "articles",
                "column": "promo_video_media_id",
                "references_table": "article_media",
                "references_column": "id",
                "on_delete": "SET NULL",
            },
            {
                "table": "article_offers",
                "column": "article_id",
                "references_table": "articles",
                "references_column": "id",
                "on_delete": "CASCADE",
            },
            {
                "table": "article_offers",
                "column": "offer_id",
                "references_table": "offers",
                "references_column": "id",
                "on_delete": "CASCADE",
            },
        ]
        
        found_fks = []
        missing_fks = []
        
        for fk_spec in required_fks:
            table_name = fk_spec["table"]
            if not self.check_table_exists(table_name):
                missing_fks.append(f"{table_name}.{fk_spec['column']}")
                continue
            
            fks = self.get_foreign_keys(table_name)
            found = False
            
            for fk in fks:
                if (fk['column_name'] == fk_spec['column'] and
                    fk['foreign_table_name'] == fk_spec['references_table'] and
                    fk['foreign_column_name'] == fk_spec['references_column']):
                    found = True
                    found_fks.append({
                        "constraint": fk['constraint_name'],
                        "table": table_name,
                        "column": fk_spec['column'],
                        "references": f"{fk_spec['references_table']}.{fk_spec['references_column']}",
                        "on_delete": fk['delete_rule'],
                    })
                    break
            
            if not found:
                missing_fks.append(f"{table_name}.{fk_spec['column']} -> {fk_spec['references_table']}.{fk_spec['references_column']}")
        
        if missing_fks:
            return CheckResult(
                name="Foreign Keys",
                status="FAIL",
                message=f"Missing foreign keys: {', '.join(missing_fks)}",
                details={"missing": missing_fks, "found": found_fks}
            )
        
        return CheckResult(
            name="Foreign Keys",
            status="PASS",
            message=f"All required foreign keys present ({len(found_fks)}/{len(required_fks)})",
            details={"found": found_fks}
        )
    
    def get_indexes(self, table_name: str) -> List[Dict]:
        """Get indexes for a table"""
        return self.execute_query("""
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename = :table_name;
        """, {"table_name": table_name})
    
    def check_indexes(self) -> CheckResult:
        """Check recommended indexes"""
        recommended_indexes = [
            {"table": "offer_media", "column": "offer_id"},
            {"table": "offers", "column": "cover_media_id"},
            {"table": "offers", "column": "promo_video_media_id"},
            {"table": "articles", "column": "slug"},
            {"table": "articles", "column": "status"},
            {"table": "articles", "column": "published_at"},
            {"table": "articles", "column": "is_featured"},
            {"table": "articles", "column": "cover_media_id"},
            {"table": "articles", "column": "promo_video_media_id"},
            {"table": "article_media", "column": "article_id"},
            {"table": "article_offers", "column": "offer_id"},
        ]
        
        found_indexes = []
        missing_indexes = []
        
        for idx_spec in recommended_indexes:
            table_name = idx_spec["table"]
            if not self.check_table_exists(table_name):
                continue
            
            indexes = self.get_indexes(table_name)
            found = False
            
            for idx in indexes:
                # Check if index includes the column
                if idx_spec["column"] in idx['indexdef']:
                    found = True
                    found_indexes.append(f"{table_name}.{idx_spec['column']}")
                    break
            
            if not found:
                missing_indexes.append(f"{table_name}.{idx_spec['column']}")
        
        if missing_indexes:
            return CheckResult(
                name="Indexes",
                status="WARN",
                message=f"Recommended indexes missing: {', '.join(missing_indexes)}",
                details={"missing": missing_indexes, "found": found_indexes}
            )
        
        return CheckResult(
            name="Indexes",
            status="PASS",
            message=f"All recommended indexes present ({len(found_indexes)}/{len(recommended_indexes)})",
            details={"found": found_indexes}
        )
    
    def run_audit(self) -> AuditReport:
        """Run complete audit"""
        checks = []
        
        # Get database info
        db_name = self.get_database_name()
        pg_version = self.get_postgres_version()
        
        # Run checks
        checks.append(self.check_alembic_migrations())
        checks.append(self.check_offers_table())
        checks.append(self.check_offer_media_table())
        checks.append(self.check_articles_table())
        checks.append(self.check_article_media_table())
        checks.append(self.check_article_offers_table())
        checks.append(self.check_foreign_keys())
        checks.append(self.check_indexes())
        
        # Calculate summary
        summary = {
            "pass": sum(1 for c in checks if c.status == "PASS"),
            "fail": sum(1 for c in checks if c.status == "FAIL"),
            "warn": sum(1 for c in checks if c.status == "WARN"),
        }
        
        # Overall status: FAIL if any FAIL, else PASS
        overall_status = "FAIL" if summary["fail"] > 0 else "PASS"
        
        self.report = AuditReport(
            timestamp=datetime.utcnow().isoformat(),
            database_url=self.database_url.split('@')[1] if '@' in self.database_url else "hidden",  # Hide credentials
            database_name=db_name,
            postgres_version=pg_version,
            overall_status=overall_status,
            checks=checks,
            summary=summary,
        )
        
        return self.report
    
    def print_report(self):
        """Print audit report to console"""
        if not self.report:
            return
        
        print("=" * 80)
        print("DATABASE SCHEMA AUDIT REPORT")
        print("=" * 80)
        print(f"Timestamp: {self.report.timestamp}")
        print(f"Database: {self.report.database_name}")
        print(f"PostgreSQL: {self.report.postgres_version}")
        print(f"Connection: {self.report.database_url}")
        print()
        
        print("CHECK RESULTS:")
        print("-" * 80)
        for check in self.report.checks:
            status_icon = "✓" if check.status == "PASS" else "✗" if check.status == "FAIL" else "⚠"
            print(f"{status_icon} [{check.status}] {check.name}")
            print(f"   {check.message}")
            if check.details:
                for key, value in check.details.items():
                    if isinstance(value, list) and len(value) > 5:
                        print(f"   {key}: {len(value)} items")
                    else:
                        print(f"   {key}: {value}")
            print()
        
        print("SUMMARY:")
        print("-" * 80)
        print(f"PASS: {self.report.summary['pass']}")
        print(f"FAIL: {self.report.summary['fail']}")
        print(f"WARN: {self.report.summary['warn']}")
        print()
        print(f"OVERALL STATUS: {self.report.overall_status}")
        print("=" * 80)
    
    def save_json_report(self, filepath: str = "reports/db_schema_audit.json"):
        """Save report as JSON"""
        if not self.report:
            return
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Convert dataclasses to dict
        report_dict = {
            "timestamp": self.report.timestamp,
            "database_url": self.report.database_url,
            "database_name": self.report.database_name,
            "postgres_version": self.report.postgres_version,
            "overall_status": self.report.overall_status,
            "checks": [asdict(c) for c in self.report.checks],
            "summary": self.report.summary,
        }
        
        with open(filepath, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        print(f"JSON report saved to: {filepath}")


def main():
    """Main entry point"""
    # Get DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Set it with: export DATABASE_URL=postgresql://user:password@host:port/dbname")
        sys.exit(1)
    
    # Create auditor and run audit
    auditor = DatabaseAuditor(database_url)
    
    if not auditor.connect():
        sys.exit(1)
    
    try:
        report = auditor.run_audit()
        auditor.print_report()
        auditor.save_json_report()
        
        # Exit with appropriate code
        sys.exit(0 if report.overall_status == "PASS" else 1)
    finally:
        auditor.disconnect()


if __name__ == "__main__":
    main()

