"""Export SQLAlchemy models to clean, production-grade PostgreSQL DDL for Supabase SQL Editor."""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable, CreateIndex

from app.core.database import Base
# Import all models to register them in Base.metadata
import app.models  # noqa: F401


def generate_ddl() -> str:
    """Generate complete PostgreSQL DDL from SQLAlchemy metadata."""
    ddl_statements = []

    # 1. Header & Extensions
    ddl_statements.append("-- ========================================================")
    ddl_statements.append("-- ABDM & NABH Hospital Management System (HMS) Platform")
    ddl_statements.append("-- Supabase PostgreSQL DDL Schema")
    ddl_statements.append("-- Generated from SQLAlchemy Models & Pydantic Schema Definitions")
    ddl_statements.append("-- ========================================================\n")

    ddl_statements.append("-- 1. Enable required extensions")
    ddl_statements.append('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    ddl_statements.append('CREATE EXTENSION IF NOT EXISTS "pgcrypto";\n')

    # 2. Extract and create PostgreSQL ENUM types
    created_enums = set()
    enum_statements = []
    
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            if hasattr(column.type, "name") and hasattr(column.type, "enums"):
                enum_name = column.type.name
                if enum_name and enum_name not in created_enums:
                    created_enums.add(enum_name)
                    values = ", ".join(f"'{v}'" for v in column.type.enums)
                    enum_statements.append(
                        f"DO $$ BEGIN\n"
                        f"    CREATE TYPE {enum_name} AS ENUM ({values});\n"
                        f"EXCEPTION WHEN duplicate_object THEN null;\n"
                        f"END $$;\n"
                    )

    if enum_statements:
        ddl_statements.append("-- 2. Custom Enumerations (Enum Types)")
        ddl_statements.extend(enum_statements)

    # 3. Create Tables in topological foreign-key order
    ddl_statements.append("-- 3. Core Database Tables (Ordered by Dependency)")
    for table in Base.metadata.sorted_tables:
        create_table_stmt = CreateTable(table).compile(dialect=postgresql.dialect())
        clean_stmt = str(create_table_stmt).strip()
        ddl_statements.append(clean_stmt + ";\n")

    # 4. Create Indexes
    ddl_statements.append("-- 4. Performance & Audit Indexes")
    for table in Base.metadata.sorted_tables:
        for index in table.indexes:
            create_index_stmt = CreateIndex(index).compile(dialect=postgresql.dialect())
            ddl_statements.append(str(create_index_stmt).strip() + ";")

    return "\n".join(ddl_statements)


if __name__ == "__main__":
    output_path = Path(__file__).resolve().parent / "supabase_schema.sql"
    sql_content = generate_ddl()
    output_path.write_text(sql_content, encoding="utf-8")
    print(f"✅ Supabase DDL schema successfully exported to: {output_path}")

