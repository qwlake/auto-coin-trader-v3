from typing import Literal, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class TradingSettings(BaseModel):
    mode: Literal["sim", "testnet", "mainnet"] = "testnet"
    position_mode: Literal["HEDGE", "ONEWAY"] = "HEDGE"
    recv_window_ms: int = 5000
    ws_max_backoff_sec: int = 60


class DatabaseSettings(BaseModel):
    url: str = "sqlite:///./database/trader.db"


class LoggingSettings(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    console_enabled: bool = True
    file_enabled: bool = True
    json_format: bool = True


class SlackSettings(BaseModel):
    webhook_url: Optional[str] = None
    channel: str = "#trading-alerts"


class StreamlitSettings(BaseModel):
    port: int = 8501
    host: str = "0.0.0.0"


class Settings(BaseSettings):
    trading: TradingSettings = Field(default_factory=TradingSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    slack: SlackSettings = Field(default_factory=SlackSettings)
    streamlit: StreamlitSettings = Field(default_factory=StreamlitSettings)
    
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"