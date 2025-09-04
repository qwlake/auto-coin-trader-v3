from typing import Optional, Dict, Any, Literal
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator


class KlineData(BaseModel):
    symbol: str
    open_time: int
    close_time: int
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    quote_volume: Decimal
    trades_count: int
    is_closed: bool
    interval: str
    first_trade_id: int
    last_trade_id: int
    base_asset_volume: Decimal
    quote_asset_volume: Decimal
    
    @validator('symbol')
    def symbol_uppercase(cls, v):
        return v.upper() if v else v
    
    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.open_time / 1000)
    
    @property
    def close_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.close_time / 1000)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.open_time,
            "open": float(self.open_price),
            "high": float(self.high_price),
            "low": float(self.low_price),
            "close": float(self.close_price),
            "volume": float(self.volume),
            "quote_volume": float(self.quote_volume),
            "trades": self.trades_count,
            "is_closed": self.is_closed
        }


class MarkPriceData(BaseModel):
    symbol: str
    mark_price: Decimal
    index_price: Decimal
    estimated_settle_price: Decimal
    funding_rate: Decimal
    next_funding_time: int
    event_time: int
    
    @validator('symbol')
    def symbol_uppercase(cls, v):
        return v.upper() if v else v
    
    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.event_time / 1000)
    
    @property
    def next_funding_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.next_funding_time / 1000)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.event_time,
            "mark_price": float(self.mark_price),
            "index_price": float(self.index_price),
            "funding_rate": float(self.funding_rate),
            "next_funding_time": self.next_funding_time
        }


class BalanceData(BaseModel):
    asset: str
    wallet_balance: Decimal
    unrealized_pnl: Decimal
    margin_balance: Decimal
    maint_margin: Decimal
    initial_margin: Decimal
    position_initial_margin: Decimal
    open_order_initial_margin: Decimal
    cross_wallet_balance: Decimal
    cross_unrealized_pnl: Decimal
    available_balance: Decimal
    max_withdraw_amount: Decimal
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset": self.asset,
            "wallet_balance": float(self.wallet_balance),
            "unrealized_pnl": float(self.unrealized_pnl),
            "margin_balance": float(self.margin_balance),
            "available_balance": float(self.available_balance)
        }


class PositionData(BaseModel):
    symbol: str
    position_amount: Decimal
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    maintenance_margin_required: Decimal
    isolated_wallet: Decimal
    position_side: Literal["BOTH", "LONG", "SHORT"]
    
    @validator('symbol')
    def symbol_uppercase(cls, v):
        return v.upper() if v else v
    
    @property
    def is_long(self) -> bool:
        return self.position_amount > 0
    
    @property
    def is_short(self) -> bool:
        return self.position_amount < 0
    
    @property
    def is_flat(self) -> bool:
        return self.position_amount == 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "position_amount": float(self.position_amount),
            "entry_price": float(self.entry_price),
            "mark_price": float(self.mark_price),
            "unrealized_pnl": float(self.unrealized_pnl),
            "position_side": self.position_side,
            "is_long": self.is_long,
            "is_short": self.is_short
        }


class OrderData(BaseModel):
    symbol: str
    client_order_id: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["LIMIT", "MARKET", "STOP", "STOP_MARKET", "TAKE_PROFIT", "TAKE_PROFIT_MARKET"]
    time_in_force: Literal["GTC", "IOC", "FOK", "GTX"]
    original_quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    execution_type: str
    order_status: Literal["NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"]
    order_id: int
    last_filled_quantity: Decimal = Decimal("0")
    cumulative_filled_quantity: Decimal = Decimal("0")
    last_filled_price: Optional[Decimal] = None
    commission_amount: Optional[Decimal] = None
    commission_asset: Optional[str] = None
    transaction_time: int
    trade_id: Optional[int] = None
    bids_notional: Optional[Decimal] = None
    ask_notional: Optional[Decimal] = None
    is_maker_side: Optional[bool] = None
    reduce_only: bool = False
    working_type: str = "CONTRACT_PRICE"
    original_order_type: Optional[str] = None
    position_side: Literal["BOTH", "LONG", "SHORT"] = "BOTH"
    close_all: bool = False
    activation_price: Optional[Decimal] = None
    callback_rate: Optional[Decimal] = None
    realized_profit: Optional[Decimal] = None
    
    @validator('symbol')
    def symbol_uppercase(cls, v):
        return v.upper() if v else v
    
    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.transaction_time / 1000)
    
    @property
    def is_filled(self) -> bool:
        return self.order_status == "FILLED"
    
    @property
    def is_partially_filled(self) -> bool:
        return self.order_status == "PARTIALLY_FILLED"
    
    @property
    def is_active(self) -> bool:
        return self.order_status in ["NEW", "PARTIALLY_FILLED"]
    
    @property
    def remaining_quantity(self) -> Decimal:
        return self.original_quantity - self.cumulative_filled_quantity
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "client_order_id": self.client_order_id,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": float(self.original_quantity),
            "price": float(self.price) if self.price else None,
            "status": self.order_status,
            "filled_quantity": float(self.cumulative_filled_quantity),
            "remaining_quantity": float(self.remaining_quantity),
            "timestamp": self.transaction_time
        }


class AccountUpdateData(BaseModel):
    event_time: int
    transaction_time: int
    balances: Dict[str, BalanceData] = Field(default_factory=dict)
    positions: Dict[str, PositionData] = Field(default_factory=dict)
    
    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.event_time / 1000)
    
    @property
    def transaction_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.transaction_time / 1000)
    
    def get_position(self, symbol: str) -> Optional[PositionData]:
        return self.positions.get(symbol.upper())
    
    def get_balance(self, asset: str) -> Optional[BalanceData]:
        return self.balances.get(asset.upper())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_time": self.event_time,
            "transaction_time": self.transaction_time,
            "balances": {k: v.to_dict() for k, v in self.balances.items()},
            "positions": {k: v.to_dict() for k, v in self.positions.items()}
        }


class MarketDataSnapshot(BaseModel):
    timestamp: int
    symbol: str
    kline: Optional[KlineData] = None
    mark_price: Optional[MarkPriceData] = None
    
    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000)
    
    @property
    def current_price(self) -> Optional[Decimal]:
        if self.mark_price:
            return self.mark_price.mark_price
        elif self.kline:
            return self.kline.close_price
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "current_price": float(self.current_price) if self.current_price else None
        }
        
        if self.kline:
            data["kline"] = self.kline.to_dict()
        
        if self.mark_price:
            data["mark_price"] = self.mark_price.to_dict()
        
        return data