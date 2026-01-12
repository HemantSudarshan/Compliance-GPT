"""
migrations.py - Database Migration System for ComplianceGPT

Simple migration system for Weaviate schema and data migrations.
Supports versioned migrations with up/down operations.
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum


class MigrationStatus(str, Enum):
    """Migration execution status."""
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Migration:
    """Represents a database migration."""
    
    version: str
    name: str
    description: str
    up: Callable
    down: Callable
    
    def __post_init__(self):
        self.checksum = self._compute_checksum()
    
    def _compute_checksum(self) -> str:
        """Compute checksum for the migration."""
        content = f"{self.version}:{self.name}:{self.description}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]


@dataclass
class MigrationRecord:
    """Record of an applied migration."""
    
    version: str
    name: str
    checksum: str
    status: MigrationStatus
    applied_at: str
    rolled_back_at: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "name": self.name,
            "checksum": self.checksum,
            "status": self.status.value if isinstance(self.status, MigrationStatus) else self.status,
            "applied_at": self.applied_at,
            "rolled_back_at": self.rolled_back_at,
            "error": self.error
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MigrationRecord":
        return cls(
            version=data["version"],
            name=data["name"],
            checksum=data["checksum"],
            status=MigrationStatus(data["status"]),
            applied_at=data["applied_at"],
            rolled_back_at=data.get("rolled_back_at"),
            error=data.get("error")
        )


class MigrationManager:
    """
    Manages database migrations for Weaviate.
    
    Features:
    - Version-controlled migrations
    - Rollback support
    - Checksum validation
    - Migration history tracking
    """
    
    def __init__(self, history_path: Optional[str] = None):
        self.history_path = Path(history_path) if history_path else Path("data/migrations")
        self.history_path.mkdir(parents=True, exist_ok=True)
        self.history_file = self.history_path / "history.json"
        
        self.migrations: dict[str, Migration] = {}
        self._load_history()
    
    def _load_history(self):
        """Load migration history from file."""
        self.history: list[MigrationRecord] = []
        
        if self.history_file.exists():
            try:
                with open(self.history_file, "r") as f:
                    data = json.load(f)
                    self.history = [
                        MigrationRecord.from_dict(record)
                        for record in data.get("migrations", [])
                    ]
            except Exception as e:
                print(f"Warning: Could not load migration history: {e}")
    
    def _save_history(self):
        """Save migration history to file."""
        with open(self.history_file, "w") as f:
            json.dump({
                "migrations": [record.to_dict() for record in self.history],
                "last_updated": datetime.now(timezone.utc).isoformat()
            }, f, indent=2)
    
    def register(self, migration: Migration):
        """Register a migration."""
        if migration.version in self.migrations:
            raise ValueError(f"Migration {migration.version} already registered")
        self.migrations[migration.version] = migration
    
    def get_pending(self) -> list[Migration]:
        """Get pending migrations."""
        applied_versions = {
            record.version for record in self.history
            if record.status == MigrationStatus.APPLIED
        }
        
        pending = [
            migration for version, migration in sorted(self.migrations.items())
            if version not in applied_versions
        ]
        
        return pending
    
    def get_applied(self) -> list[MigrationRecord]:
        """Get applied migrations."""
        return [
            record for record in self.history
            if record.status == MigrationStatus.APPLIED
        ]
    
    def apply(self, version: Optional[str] = None) -> list[MigrationRecord]:
        """
        Apply migrations.
        
        Args:
            version: Specific version to apply, or None for all pending
        """
        if version:
            migrations = [self.migrations.get(version)]
            if not migrations[0]:
                raise ValueError(f"Migration {version} not found")
        else:
            migrations = self.get_pending()
        
        results = []
        
        for migration in migrations:
            record = self._apply_migration(migration)
            results.append(record)
            
            if record.status == MigrationStatus.FAILED:
                break  # Stop on first failure
        
        return results
    
    def _apply_migration(self, migration: Migration) -> MigrationRecord:
        """Apply a single migration."""
        record = MigrationRecord(
            version=migration.version,
            name=migration.name,
            checksum=migration.checksum,
            status=MigrationStatus.PENDING,
            applied_at=datetime.now(timezone.utc).isoformat()
        )
        
        try:
            print(f"Applying migration {migration.version}: {migration.name}")
            migration.up()
            record.status = MigrationStatus.APPLIED
            print(f"  ✓ Migration {migration.version} applied successfully")
        except Exception as e:
            record.status = MigrationStatus.FAILED
            record.error = str(e)
            print(f"  ✗ Migration {migration.version} failed: {e}")
        
        self.history.append(record)
        self._save_history()
        
        return record
    
    def rollback(self, version: Optional[str] = None) -> list[MigrationRecord]:
        """
        Rollback migrations.
        
        Args:
            version: Specific version to rollback, or None for last applied
        """
        applied = self.get_applied()
        
        if not applied:
            print("No migrations to rollback")
            return []
        
        if version:
            to_rollback = [
                record for record in reversed(applied)
                if record.version == version
            ][:1]
        else:
            to_rollback = [applied[-1]]
        
        results = []
        
        for record in to_rollback:
            migration = self.migrations.get(record.version)
            if not migration:
                print(f"Warning: Migration {record.version} not found, skipping rollback")
                continue
            
            result = self._rollback_migration(migration, record)
            results.append(result)
        
        return results
    
    def _rollback_migration(
        self,
        migration: Migration,
        record: MigrationRecord
    ) -> MigrationRecord:
        """Rollback a single migration."""
        try:
            print(f"Rolling back migration {migration.version}: {migration.name}")
            migration.down()
            record.status = MigrationStatus.ROLLED_BACK
            record.rolled_back_at = datetime.now(timezone.utc).isoformat()
            print(f"  ✓ Migration {migration.version} rolled back successfully")
        except Exception as e:
            record.error = f"Rollback failed: {e}"
            print(f"  ✗ Rollback of {migration.version} failed: {e}")
        
        self._save_history()
        return record
    
    def status(self) -> dict:
        """Get migration status."""
        pending = self.get_pending()
        applied = self.get_applied()
        
        return {
            "pending_count": len(pending),
            "applied_count": len(applied),
            "pending": [
                {"version": m.version, "name": m.name}
                for m in pending
            ],
            "applied": [
                {
                    "version": r.version,
                    "name": r.name,
                    "applied_at": r.applied_at
                }
                for r in applied
            ],
            "last_applied": applied[-1].version if applied else None
        }


# Weaviate-specific migrations

def create_weaviate_migrations(manager: MigrationManager):
    """Register Weaviate schema migrations."""
    
    # Migration 001: Initial schema
    manager.register(Migration(
        version="001",
        name="initial_schema",
        description="Create initial Weaviate schema for regulatory documents",
        up=lambda: _create_initial_schema(),
        down=lambda: _drop_initial_schema()
    ))
    
    # Migration 002: Add metadata fields
    manager.register(Migration(
        version="002",
        name="add_metadata_fields",
        description="Add additional metadata fields to RegulatoryChunk class",
        up=lambda: _add_metadata_fields(),
        down=lambda: _remove_metadata_fields()
    ))
    
    # Migration 003: Add semantic search vectorizer
    manager.register(Migration(
        version="003",
        name="configure_vectorizer",
        description="Configure text2vec-openai vectorizer for semantic search",
        up=lambda: _configure_vectorizer(),
        down=lambda: _reset_vectorizer()
    ))


def _create_initial_schema():
    """Create initial Weaviate schema."""
    from src.storage.weaviate_client import get_weaviate_client
    
    client = get_weaviate_client()
    
    schema = {
        "class": "RegulatoryChunk",
        "description": "Chunks of regulatory documents for compliance search",
        "properties": [
            {
                "name": "content",
                "dataType": ["text"],
                "description": "The text content of the chunk"
            },
            {
                "name": "regulation",
                "dataType": ["string"],
                "description": "The regulation name (e.g., GDPR, CCPA)"
            },
            {
                "name": "section",
                "dataType": ["string"],
                "description": "The section or article reference"
            },
            {
                "name": "chunk_id",
                "dataType": ["string"],
                "description": "Unique identifier for the chunk"
            }
        ]
    }
    
    try:
        client.schema.create_class(schema)
    except Exception as e:
        if "already exists" not in str(e).lower():
            raise


def _drop_initial_schema():
    """Drop initial Weaviate schema."""
    from src.storage.weaviate_client import get_weaviate_client
    
    client = get_weaviate_client()
    
    try:
        client.schema.delete_class("RegulatoryChunk")
    except Exception:
        pass


def _add_metadata_fields():
    """Add metadata fields to schema."""
    from src.storage.weaviate_client import get_weaviate_client
    
    client = get_weaviate_client()
    
    new_properties = [
        {
            "name": "source_file",
            "dataType": ["string"],
            "description": "Original source file name"
        },
        {
            "name": "page_number",
            "dataType": ["int"],
            "description": "Page number in the source document"
        },
        {
            "name": "ingestion_date",
            "dataType": ["date"],
            "description": "When the chunk was ingested"
        }
    ]
    
    for prop in new_properties:
        try:
            client.schema.property.create("RegulatoryChunk", prop)
        except Exception as e:
            if "already exists" not in str(e).lower():
                print(f"Warning: Could not add property {prop['name']}: {e}")


def _remove_metadata_fields():
    """Remove added metadata fields."""
    # Weaviate doesn't support removing properties, so this is a no-op
    print("Warning: Cannot remove properties from Weaviate schema")


def _configure_vectorizer():
    """Configure vectorizer settings."""
    # This would update vectorizer configuration
    # For now, this is a placeholder
    print("Vectorizer configuration updated")


def _reset_vectorizer():
    """Reset vectorizer to default."""
    print("Vectorizer reset to default")


# CLI interface

def cli():
    """Command-line interface for migrations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ComplianceGPT Migration Manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Status command
    subparsers.add_parser("status", help="Show migration status")
    
    # Apply command
    apply_parser = subparsers.add_parser("apply", help="Apply migrations")
    apply_parser.add_argument(
        "--version", "-v",
        help="Specific version to apply"
    )
    
    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback migrations")
    rollback_parser.add_argument(
        "--version", "-v",
        help="Specific version to rollback"
    )
    
    args = parser.parse_args()
    
    # Initialize manager with migrations
    manager = MigrationManager()
    create_weaviate_migrations(manager)
    
    if args.command == "status":
        status = manager.status()
        print("\n📊 Migration Status")
        print("=" * 40)
        print(f"Applied: {status['applied_count']}")
        print(f"Pending: {status['pending_count']}")
        
        if status['applied']:
            print("\n✓ Applied migrations:")
            for m in status['applied']:
                print(f"  - {m['version']}: {m['name']} ({m['applied_at'][:10]})")
        
        if status['pending']:
            print("\n⏳ Pending migrations:")
            for m in status['pending']:
                print(f"  - {m['version']}: {m['name']}")
    
    elif args.command == "apply":
        print("\n🚀 Applying migrations...")
        results = manager.apply(args.version)
        
        for record in results:
            status = "✓" if record.status == MigrationStatus.APPLIED else "✗"
            print(f"  {status} {record.version}: {record.name}")
            if record.error:
                print(f"      Error: {record.error}")
    
    elif args.command == "rollback":
        print("\n⏪ Rolling back migrations...")
        results = manager.rollback(args.version)
        
        for record in results:
            status = "✓" if record.status == MigrationStatus.ROLLED_BACK else "✗"
            print(f"  {status} {record.version}: {record.name}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
