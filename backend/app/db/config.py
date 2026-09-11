"""Database configuration for VPP Simulator."""
import os


class DatabaseConfig:
    """Database connection configuration."""
    
    # Connection settings - can be overridden via environment variables
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "ParolaServer")
    DB_NAME = os.getenv("DB_NAME", "vpp_simulator")
    
    # Connection pool settings
    POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
    MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes
    
    # Echo SQL statements (for debugging)
    ECHO_SQL = os.getenv("DB_ECHO_SQL", "false").lower() == "true"
    
    @classmethod
    def get_async_url(cls) -> str:
        """Get async database URL for aiomysql."""
        return (
            f"mysql+aiomysql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )
    
    @classmethod
    def get_sync_url(cls) -> str:
        """Get sync database URL for PyMySQL (used for migrations/setup)."""
        return (
            f"mysql+pymysql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )
    
    @classmethod
    def get_server_url(cls) -> str:
        """Get server URL without database name (for creating database)."""
        return (
            f"mysql+pymysql://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}"
        )
