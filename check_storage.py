#!/usr/bin/env python3
"""
Helper script to check where files are stored in Mira AI Agent
"""
import os
from pathlib import Path

# Get project root
project_root = Path(__file__).parent.absolute()

print("=" * 60)
print("Mira AI Agent - File Storage Locations")
print("=" * 60)
print(f"\n📁 Project Root: {project_root}")
print()

# Database
db_path = project_root / "mira.db"
print("📊 Database:")
if db_path.exists():
    size = db_path.stat().st_size
    print(f"  Location: {db_path}")
    print(f"  Size: {size:,} bytes ({size/1024:.1f} KB)")
else:
    print(f"  Location: {db_path} (not created yet)")
print()

# Generated outputs
outputs_dir = project_root / "outputs"
print("📤 Generated Outputs (Plans, Reports):")
if outputs_dir.exists():
    files = list(outputs_dir.glob("*"))
    file_count = len([f for f in files if f.is_file()])
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    print(f"  Location: {outputs_dir}")
    print(f"  Files: {file_count} files")
    print(f"  Total Size: {total_size:,} bytes ({total_size/1024:.1f} KB)")
    if file_count > 0:
        print(f"  Recent files:")
        recent = sorted([f for f in files if f.is_file()], key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        for f in recent:
            print(f"    - {f.name} ({f.stat().st_size:,} bytes)")
else:
    print(f"  Location: {outputs_dir} (not created yet)")
print()

# Uploaded files
uploads_dir = project_root / "uploads"
print("📥 Uploaded Files:")
if uploads_dir.exists():
    all_files = list(uploads_dir.rglob("*"))
    files = [f for f in all_files if f.is_file()]
    total_size = sum(f.stat().st_size for f in files)
    print(f"  Location: {uploads_dir}")
    print(f"  Files: {len(files)} files")
    print(f"  Total Size: {total_size:,} bytes ({total_size/1024:.1f} KB)")
    print(f"  Structure: uploads/{{company_id}}/{{user_id}}/{{sha256}}/{{filename}}")
    if files:
        print(f"  Sample files:")
        for f in files[:5]:
            rel_path = f.relative_to(project_root)
            print(f"    - {rel_path} ({f.stat().st_size:,} bytes)")
else:
    print(f"  Location: {uploads_dir} (created on first upload)")
    print(f"  Structure: uploads/{{company_id}}/{{user_id}}/{{sha256}}/{{filename}}")
print()

# Check database for document records
try:
    from dotenv import load_dotenv
    load_dotenv()
    from src.db import get_engine, documents
    from sqlalchemy import select
    
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(select(documents))
        doc_rows = result.fetchall()
        
    if doc_rows:
        print("📋 Documents in Database:")
        print(f"  Total records: {len(doc_rows)}")
        print(f"  Sample records:")
        for row in doc_rows[:5]:
            print(f"    - {row.filename} ({row.size:,} bytes)")
            print(f"      Path: {row.path}")
            print(f"      Uploaded: {row.uploaded_at}")
    else:
        print("📋 Documents in Database: No documents stored yet")
except Exception as e:
    print(f"📋 Documents in Database: Could not check (database not configured or error: {e})")

print()
print("=" * 60)
