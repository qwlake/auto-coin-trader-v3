from typing import List, Dict, Any, Callable
from datetime import datetime, UTC
import json

from sqlmodel import SQLModel, Field, Session, select, text
from sqlalchemy import Index, MetaData, Table
from sqlalchemy.schema import CreateIndex, DropIndex
from database.connection import get_database_manager
from utils.logging import get_logger, TradingLoggerAdapter


class MigrationRecord(SQLModel, table=True):
    __tablename__ = "schema_migrations"
    
    id: int = Field(primary_key=True)
    version: str = Field(index=True, description="Migration version")
    name: str = Field(description="Migration name")
    applied_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="When migration was applied")
    checksum: str = Field(description="Migration checksum for integrity")


class Migration:
    def __init__(self, version: str, name: str, up_func: Callable, down_func: Callable = None):
        self.version = version
        self.name = name
        self.up_func = up_func
        self.down_func = down_func
        self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        import hashlib
        import inspect
        
        up_source = inspect.getsource(self.up_func) if self.up_func else ""
        down_source = inspect.getsource(self.down_func) if self.down_func else ""
        content = f"{self.version}{self.name}{up_source}{down_source}"
        return hashlib.md5(content.encode()).hexdigest()


class MigrationManager:
    def __init__(self):
        self.logger: TradingLoggerAdapter = get_logger("migrations")
        self.migrations: List[Migration] = []
        self._register_default_migrations()
    
    def _register_default_migrations(self):
        """Register default migrations for initial schema setup"""
        
        def migration_001_up(engine):
            """Create additional performance indexes"""
            metadata = MetaData()
            
            # Create additional indexes using SQLAlchemy DDL
            orders_table = Table('orders', metadata, autoload_with=engine)
            fills_table = Table('fills', metadata, autoload_with=engine)
            signals_table = Table('signals', metadata, autoload_with=engine)
            candles_table = Table('candles_1m', metadata, autoload_with=engine)
            
            indexes = [
                Index('idx_orders_symbol_created_status', orders_table.c.symbol, orders_table.c.created_at, orders_table.c.status),
                Index('idx_fills_symbol_executed_price', fills_table.c.symbol, fills_table.c.executed_at, fills_table.c.price),
                Index('idx_signals_strategy_symbol_created', signals_table.c.strategy, signals_table.c.symbol, signals_table.c.created_at),
                Index('idx_candles_symbol_time_closed', candles_table.c.symbol, candles_table.c.open_time, candles_table.c.is_closed),
            ]
            
            for idx in indexes:
                try:
                    CreateIndex(idx, if_not_exists=True).execute(engine)
                except Exception as e:
                    # Index might already exist
                    pass
        
        def migration_001_down(engine):
            """Drop additional performance indexes"""
            metadata = MetaData()
            
            orders_table = Table('orders', metadata, autoload_with=engine)
            fills_table = Table('fills', metadata, autoload_with=engine)
            signals_table = Table('signals', metadata, autoload_with=engine)
            candles_table = Table('candles_1m', metadata, autoload_with=engine)
            
            indexes = [
                Index('idx_orders_symbol_created_status', orders_table.c.symbol, orders_table.c.created_at, orders_table.c.status),
                Index('idx_fills_symbol_executed_price', fills_table.c.symbol, fills_table.c.executed_at, fills_table.c.price),
                Index('idx_signals_strategy_symbol_created', signals_table.c.strategy, signals_table.c.symbol, signals_table.c.created_at),
                Index('idx_candles_symbol_time_closed', candles_table.c.symbol, candles_table.c.open_time, candles_table.c.is_closed),
            ]
            
            for idx in indexes:
                try:
                    DropIndex(idx, if_exists=True).execute(engine)
                except Exception as e:
                    # Index might not exist
                    pass
        
        # Register migration 001
        self.add_migration(
            version="001",
            name="create_additional_indexes",
            up_func=migration_001_up,
            down_func=migration_001_down
        )
        
        def migration_002_up(engine):
            """Add performance monitoring columns"""
            # For SQLite, we need to use ALTER TABLE statements
            with engine.connect() as conn:
                try:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN execution_duration_ms INTEGER DEFAULT NULL"))
                except Exception:
                    pass  # Column might already exist
                
                try:
                    conn.execute(text("ALTER TABLE orders ADD COLUMN slippage_bps INTEGER DEFAULT NULL"))
                except Exception:
                    pass  # Column might already exist
                
                try:
                    conn.execute(text("ALTER TABLE signals ADD COLUMN market_impact_bps INTEGER DEFAULT NULL"))
                except Exception:
                    pass  # Column might already exist
                
                try:
                    conn.execute(text("ALTER TABLE signals ADD COLUMN signal_delay_ms INTEGER DEFAULT NULL"))
                except Exception:
                    pass  # Column might already exist
                
                conn.commit()
        
        def migration_002_down(engine):
            """Remove performance monitoring columns"""
            # SQLite doesn't support DROP COLUMN, so we'll leave the columns
            # In a real migration system, we'd recreate the table without these columns
            pass
        
        # Register migration 002
        self.add_migration(
            version="002",
            name="add_performance_columns",
            up_func=migration_002_up,
            down_func=migration_002_down
        )
    
    def add_migration(self, version: str, name: str, up_func: Callable, down_func: Callable = None):
        """Add a new migration"""
        migration = Migration(version, name, up_func, down_func)
        self.migrations.append(migration)
        self.migrations.sort(key=lambda m: m.version)
    
    def _ensure_migration_table(self, session: Session):
        """Ensure migration tracking table exists"""
        try:
            # Try to create the migration table
            SQLModel.metadata.create_all(
                get_database_manager().engine,
                tables=[MigrationRecord.__table__]
            )
            session.commit()
        except Exception as e:
            self.logger.debug(f"Migration table may already exist: {e}")
            session.rollback()
    
    def get_applied_migrations(self, session: Session) -> List[str]:
        """Get list of applied migration versions"""
        try:
            statement = select(MigrationRecord.version).order_by(MigrationRecord.version)
            results = session.exec(statement).all()
            return list(results)
        except Exception:
            # Migration table doesn't exist yet
            return []
    
    def is_migration_applied(self, session: Session, version: str) -> bool:
        """Check if a migration version has been applied"""
        applied_migrations = self.get_applied_migrations(session)
        return version in applied_migrations
    
    def apply_migration(self, session: Session, migration: Migration) -> bool:
        """Apply a single migration"""
        try:
            if self.is_migration_applied(session, migration.version):
                self.logger.info(f"Migration {migration.version} already applied, skipping")
                return True
            
            self.logger.info(f"Applying migration {migration.version}: {migration.name}")
            
            # Execute migration function with engine
            if migration.up_func:
                db_manager = get_database_manager()
                migration.up_func(db_manager.engine)
            
            # Record migration as applied
            migration_record = MigrationRecord(
                version=migration.version,
                name=migration.name,
                checksum=migration.checksum
            )
            session.add(migration_record)
            session.commit()
            
            self.logger.info(f"Successfully applied migration {migration.version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply migration {migration.version}: {e}")
            session.rollback()
            return False
    
    def rollback_migration(self, session: Session, version: str) -> bool:
        """Rollback a specific migration"""
        try:
            migration = next((m for m in self.migrations if m.version == version), None)
            if not migration:
                self.logger.error(f"Migration {version} not found")
                return False
            
            if not self.is_migration_applied(session, version):
                self.logger.info(f"Migration {version} not applied, nothing to rollback")
                return True
            
            self.logger.info(f"Rolling back migration {version}: {migration.name}")
            
            # Execute rollback function
            if migration.down_func:
                db_manager = get_database_manager()
                migration.down_func(db_manager.engine)
            
            # Remove migration record
            statement = select(MigrationRecord).where(MigrationRecord.version == version)
            migration_record = session.exec(statement).first()
            if migration_record:
                session.delete(migration_record)
            
            session.commit()
            
            self.logger.info(f"Successfully rolled back migration {version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rollback migration {version}: {e}")
            session.rollback()
            return False
    
    def migrate_up(self, session: Session, target_version: str = None) -> bool:
        """Apply all pending migrations up to target version"""
        try:
            self._ensure_migration_table(session)
            
            applied_migrations = set(self.get_applied_migrations(session))
            
            success = True
            for migration in self.migrations:
                if target_version and migration.version > target_version:
                    break
                
                if migration.version not in applied_migrations:
                    if not self.apply_migration(session, migration):
                        success = False
                        break
            
            return success
            
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return False
    
    def get_migration_status(self, session: Session) -> Dict[str, Any]:
        """Get current migration status"""
        try:
            self._ensure_migration_table(session)
            
            applied_migrations = set(self.get_applied_migrations(session))
            pending_migrations = [m for m in self.migrations if m.version not in applied_migrations]
            
            return {
                "total_migrations": len(self.migrations),
                "applied_count": len(applied_migrations),
                "pending_count": len(pending_migrations),
                "applied_migrations": sorted(list(applied_migrations)),
                "pending_migrations": [{"version": m.version, "name": m.name} for m in pending_migrations],
                "latest_version": max([m.version for m in self.migrations]) if self.migrations else None,
                "current_version": max(applied_migrations) if applied_migrations else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get migration status: {e}")
            return {"error": str(e)}


# Global migration manager
migration_manager = MigrationManager()


def run_migrations() -> bool:
    """Run all pending migrations"""
    db_manager = get_database_manager()
    
    if not db_manager._initialized:
        if not db_manager.initialize():
            return False
    
    with db_manager.get_session() as session:
        return migration_manager.migrate_up(session)


def get_migration_status() -> Dict[str, Any]:
    """Get current migration status"""
    db_manager = get_database_manager()
    
    if not db_manager._initialized:
        if not db_manager.initialize():
            return {"error": "Database not initialized"}
    
    with db_manager.get_session() as session:
        return migration_manager.get_migration_status(session)