import asyncio
from typing import Optional, AsyncGenerator, Dict, Any
from contextlib import asynccontextmanager
from pathlib import Path

from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from utils.logging import get_logger, TradingLoggerAdapter
from config.settings import Settings


class DatabaseManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger: TradingLoggerAdapter = get_logger("database")
        
        self.engine: Optional[Engine] = None
        self.async_engine = None
        self.async_session_maker = None
        self._initialized = False
        
        # Extract database URL components
        self.database_url = settings.database.url
        
    def initialize(self):
        """Initialize synchronous database connection"""
        try:
            # Create database directory if using SQLite
            if self.database_url.startswith('sqlite'):
                db_path = self.database_url.replace('sqlite:///', '')
                if db_path.startswith('./'):
                    db_path = db_path[2:]
                
                db_file = Path(db_path)
                db_file.parent.mkdir(parents=True, exist_ok=True)
                
                self.logger.info(f"Using SQLite database: {db_file.absolute()}")
            
            # Create synchronous engine
            if self.database_url.startswith('sqlite'):
                # SQLite specific configuration
                self.engine = create_engine(
                    self.database_url,
                    echo=False,  # Set to True for SQL debugging
                    poolclass=StaticPool,
                    connect_args={
                        "check_same_thread": False,  # Allow multi-threading
                        "timeout": 20  # 20 second timeout
                    }
                )
            else:
                # PostgreSQL or other databases
                self.engine = create_engine(
                    self.database_url,
                    echo=False,
                    pool_pre_ping=True,
                    pool_recycle=3600
                )
            
            # Test connection
            with Session(self.engine) as session:
                session.exec(select(1))
            
            self._initialized = True
            self.logger.info("Database connection initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            return False
    
    async def initialize_async(self):
        """Initialize asynchronous database connection"""
        try:
            # Convert sync URL to async URL if needed
            if self.database_url.startswith('sqlite'):
                async_url = self.database_url.replace('sqlite:///', 'sqlite+aiosqlite:///')
            elif self.database_url.startswith('postgresql'):
                async_url = self.database_url.replace('postgresql://', 'postgresql+asyncpg://')
            else:
                async_url = self.database_url
            
            # Create async engine
            if async_url.startswith('sqlite'):
                self.async_engine = create_async_engine(
                    async_url,
                    echo=False,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False}
                )
            else:
                self.async_engine = create_async_engine(
                    async_url,
                    echo=False,
                    pool_pre_ping=True,
                    pool_recycle=3600
                )
            
            # Create session maker
            self.async_session_maker = async_sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            async with self.async_session_maker() as session:
                result = await session.exec(select(1))
                await result.fetchone()
            
            self.logger.info("Async database connection initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize async database: {e}")
            return False
    
    def create_tables(self):
        """Create all database tables"""
        try:
            if not self._initialized:
                raise Exception("Database not initialized")
            
            # Import all models to ensure they're registered
            from database.models import (
                Order, Fill, Position, Signal, Candle1m, AccountSnapshot
            )
            
            # Create all tables
            SQLModel.metadata.create_all(self.engine)
            
            self.logger.info("Database tables created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create tables: {e}")
            return False
    
    def get_session(self) -> Session:
        """Get synchronous database session"""
        if not self._initialized:
            raise Exception("Database not initialized")
        
        return Session(self.engine)
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get asynchronous database session context manager"""
        if not self.async_session_maker:
            raise Exception("Async database not initialized")
        
        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get database connection information"""
        return {
            "database_url": self.database_url,
            "initialized": self._initialized,
            "engine_type": type(self.engine).__name__ if self.engine else None,
            "async_engine_type": type(self.async_engine).__name__ if self.async_engine else None,
            "has_async": self.async_session_maker is not None
        }
    
    def close(self):
        """Close database connections"""
        try:
            if self.engine:
                self.engine.dispose()
                self.engine = None
            
            if self.async_engine:
                asyncio.create_task(self.async_engine.dispose())
                self.async_engine = None
                self.async_session_maker = None
            
            self._initialized = False
            self.logger.info("Database connections closed")
            
        except Exception as e:
            self.logger.error(f"Error closing database connections: {e}")
    
    def health_check(self) -> bool:
        """Check database connection health"""
        try:
            if not self._initialized:
                return False
            
            with Session(self.engine) as session:
                result = session.exec(select(1))
                result.one()  # Use .one() instead of .fetchone()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False
    
    async def async_health_check(self) -> bool:
        """Check async database connection health"""
        try:
            if not self.async_session_maker:
                return False
            
            async with self.get_async_session() as session:
                result = await session.exec(select(1))
                await result.one()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Async database health check failed: {e}")
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager(settings: Optional[Settings] = None) -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    
    if _db_manager is None:
        if settings is None:
            from config.settings import Settings
            settings = Settings()
        
        _db_manager = DatabaseManager(settings)
    
    return _db_manager


def initialize_database(settings: Optional[Settings] = None) -> bool:
    """Initialize database with tables"""
    db_manager = get_database_manager(settings)
    
    if not db_manager.initialize():
        return False
    
    if not db_manager.create_tables():
        return False
    
    return True


async def initialize_async_database(settings: Optional[Settings] = None) -> bool:
    """Initialize async database"""
    db_manager = get_database_manager(settings)
    
    return await db_manager.initialize_async()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Convenience function to get async database session"""
    db_manager = get_database_manager()
    async with db_manager.get_async_session() as session:
        yield session


def get_sync_db_session() -> Session:
    """Convenience function to get sync database session"""
    db_manager = get_database_manager()
    return db_manager.get_session()