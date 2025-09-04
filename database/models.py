from typing import Optional, List
from datetime import datetime, UTC
from decimal import Decimal
from enum import Enum

from sqlmodel import SQLModel, Field, Relationship, Column, Integer, String, DateTime, Text
from sqlalchemy import DECIMAL, Index
from pydantic import validator


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"


class OrderStatus(str, Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PositionSide(str, Enum):
    BOTH = "BOTH"
    LONG = "LONG"
    SHORT = "SHORT"


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"


# Database Models
class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Binance order info
    binance_order_id: int = Field(index=True, description="Binance order ID")
    binance_client_order_id: str = Field(index=True, description="Client order ID")
    
    # Symbol and basic info
    symbol: str = Field(index=True, description="Trading pair symbol")
    side: OrderSide = Field(description="Order side")
    order_type: OrderType = Field(description="Order type")
    time_in_force: str = Field(default="GTC", description="Time in force")
    
    # Quantities and prices (using DECIMAL for precision)
    original_quantity: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Original order quantity")
    executed_quantity: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(20, 8)), description="Executed quantity")
    price: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(20, 8)), description="Order price")
    stop_price: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(20, 8)), description="Stop price")
    
    # Status and timing
    status: OrderStatus = Field(description="Order status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Order creation time")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last update time")
    binance_created_at: Optional[datetime] = Field(default=None, description="Binance order time")
    
    # Position and risk management
    position_side: PositionSide = Field(default=PositionSide.BOTH, description="Position side")
    reduce_only: bool = Field(default=False, description="Reduce only flag")
    
    # Strategy context
    strategy: Optional[str] = Field(default=None, index=True, description="Strategy name")
    signal_id: Optional[int] = Field(default=None, foreign_key="signals.id", description="Related signal")
    
    # Relationships
    signal: Optional["Signal"] = Relationship(back_populates="orders")
    fills: List["Fill"] = Relationship(back_populates="order")
    
    @validator('original_quantity', 'executed_quantity', 'price', 'stop_price', pre=True)
    def convert_to_decimal(cls, v):
        if v is None:
            return v
        return Decimal(str(v))

    class Config:
        arbitrary_types_allowed = True

    # Indexes
    __table_args__ = (
        Index("idx_order_symbol_status", "symbol", "status"),
        Index("idx_order_strategy_created", "strategy", "created_at"),
        Index("idx_order_binance_id", "binance_order_id"),
    )


class Fill(SQLModel, table=True):
    __tablename__ = "fills"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Order relationship
    order_id: int = Field(foreign_key="orders.id", index=True, description="Related order ID")
    
    # Binance fill info
    binance_trade_id: int = Field(index=True, description="Binance trade ID")
    
    # Symbol and execution details
    symbol: str = Field(index=True, description="Trading pair symbol")
    side: OrderSide = Field(description="Fill side")
    
    # Execution details
    quantity: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Fill quantity")
    price: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Fill price")
    commission: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Commission paid")
    commission_asset: str = Field(description="Commission asset")
    
    # Timing
    executed_at: datetime = Field(description="Execution time")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Record creation time")
    
    # Trading info
    is_maker: bool = Field(description="Is maker trade")
    realized_pnl: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(20, 8)), description="Realized PnL")
    
    # Relationships
    order: Order = Relationship(back_populates="fills")
    
    @validator('quantity', 'price', 'commission', 'realized_pnl', pre=True)
    def convert_to_decimal(cls, v):
        if v is None:
            return v
        return Decimal(str(v))

    class Config:
        arbitrary_types_allowed = True

    # Indexes
    __table_args__ = (
        Index("idx_fill_symbol_executed", "symbol", "executed_at"),
        Index("idx_fill_binance_trade", "binance_trade_id"),
    )


class Position(SQLModel, table=True):
    __tablename__ = "positions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Symbol and position info
    symbol: str = Field(index=True, description="Trading pair symbol")
    position_side: PositionSide = Field(description="Position side")
    
    # Position quantities
    position_amount: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Position size")
    entry_price: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Average entry price")
    mark_price: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Current mark price")
    
    # PnL and margin
    unrealized_pnl: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Unrealized PnL")
    percentage: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(10, 4)), description="PnL percentage")
    
    # Margin requirements
    isolated_wallet: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(20, 8)), description="Isolated margin")
    maintenance_margin: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(20, 8)), description="Maintenance margin")
    initial_margin: Decimal = Field(default=Decimal("0"), sa_column=Column(DECIMAL(20, 8)), description="Initial margin")
    
    # Position settings
    leverage: int = Field(default=1, description="Position leverage")
    max_notional_value: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(20, 8)), description="Max notional")
    
    # Timestamps
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last update time")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Position creation time")
    
    # Strategy context
    strategy: Optional[str] = Field(default=None, index=True, description="Strategy name")
    
    @validator('position_amount', 'entry_price', 'mark_price', 'unrealized_pnl', 
              'percentage', 'isolated_wallet', 'maintenance_margin', 'initial_margin', 
              'max_notional_value', pre=True)
    def convert_to_decimal(cls, v):
        if v is None:
            return v
        return Decimal(str(v))

    class Config:
        arbitrary_types_allowed = True

    # Indexes
    __table_args__ = (
        Index("idx_position_symbol_side", "symbol", "position_side"),
        Index("idx_position_strategy_updated", "strategy", "updated_at"),
    )


class Signal(SQLModel, table=True):
    __tablename__ = "signals"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Signal identification
    strategy: str = Field(index=True, description="Strategy name that generated signal")
    symbol: str = Field(index=True, description="Trading pair symbol")
    signal_type: SignalType = Field(description="Signal type")
    
    # Signal data
    price: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Price when signal generated")
    quantity: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(20, 8)), description="Suggested quantity")
    confidence: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(5, 4)), description="Signal confidence 0-1")
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True, description="Signal creation time")
    valid_until: Optional[datetime] = Field(default=None, description="Signal expiry time")
    
    # Context and metadata
    market_conditions: Optional[str] = Field(default=None, sa_column=Column(Text), description="Market conditions JSON")
    indicators: Optional[str] = Field(default=None, sa_column=Column(Text), description="Technical indicators JSON")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    
    # Execution tracking
    executed: bool = Field(default=False, index=True, description="Signal executed flag")
    executed_at: Optional[datetime] = Field(default=None, description="Execution time")
    execution_price: Optional[Decimal] = Field(default=None, sa_column=Column(DECIMAL(20, 8)), description="Actual execution price")
    
    # Relationships
    orders: List[Order] = Relationship(back_populates="signal")
    
    @validator('price', 'quantity', 'confidence', 'execution_price', pre=True)
    def convert_to_decimal(cls, v):
        if v is None:
            return v
        return Decimal(str(v))

    class Config:
        arbitrary_types_allowed = True

    # Indexes
    __table_args__ = (
        Index("idx_signal_strategy_symbol", "strategy", "symbol"),
        Index("idx_signal_created_executed", "created_at", "executed"),
        Index("idx_signal_symbol_type_created", "symbol", "signal_type", "created_at"),
    )


class Candle1m(SQLModel, table=True):
    __tablename__ = "candles_1m"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Symbol and timing
    symbol: str = Field(index=True, description="Trading pair symbol")
    open_time: datetime = Field(index=True, description="Candle open time")
    close_time: datetime = Field(description="Candle close time")
    
    # OHLCV data
    open_price: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Open price")
    high_price: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="High price")
    low_price: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Low price")
    close_price: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Close price")
    volume: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Base asset volume")
    quote_volume: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Quote asset volume")
    
    # Trading statistics
    trades_count: int = Field(description="Number of trades")
    taker_buy_base_volume: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Taker buy base volume")
    taker_buy_quote_volume: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Taker buy quote volume")
    
    # Metadata
    is_closed: bool = Field(default=True, description="Candle is closed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Record creation time")
    
    @validator('open_price', 'high_price', 'low_price', 'close_price', 
              'volume', 'quote_volume', 'taker_buy_base_volume', 'taker_buy_quote_volume', pre=True)
    def convert_to_decimal(cls, v):
        if v is None:
            return v
        return Decimal(str(v))

    class Config:
        arbitrary_types_allowed = True

    # Indexes
    __table_args__ = (
        Index("idx_candle_symbol_time", "symbol", "open_time"),
        Index("idx_candle_symbol_closed", "symbol", "is_closed", "open_time"),
    )


# Account and performance tracking tables
class AccountSnapshot(SQLModel, table=True):
    __tablename__ = "account_snapshots"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Account balance info
    total_wallet_balance: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Total wallet balance")
    total_unrealized_pnl: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Total unrealized PnL")
    total_margin_balance: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Total margin balance")
    total_initial_margin: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Total initial margin")
    total_maintenance_margin: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Total maintenance margin")
    
    # Risk metrics
    max_withdraw_amount: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Max withdraw amount")
    available_balance: Decimal = Field(sa_column=Column(DECIMAL(20, 8)), description="Available balance")
    
    # Timestamp
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True, description="Snapshot time")
    
    @validator('total_wallet_balance', 'total_unrealized_pnl', 'total_margin_balance',
              'total_initial_margin', 'total_maintenance_margin', 'max_withdraw_amount',
              'available_balance', pre=True)
    def convert_to_decimal(cls, v):
        if v is None:
            return v
        return Decimal(str(v))

    class Config:
        arbitrary_types_allowed = True