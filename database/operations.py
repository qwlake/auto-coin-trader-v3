from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, UTC
from decimal import Decimal

from sqlmodel import Session, select, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, text

from database.models import (
    Order, Fill, Position, Signal, Candle1m, AccountSnapshot,
    OrderStatus, OrderSide, SignalType, PositionSide
)
from database.connection import get_sync_db_session, get_db_session
from utils.logging import get_logger, TradingLoggerAdapter


class OrderOperations:
    def __init__(self):
        self.logger: TradingLoggerAdapter = get_logger("order_ops")
    
    def create_order(self, session: Session, order_data: Dict[str, Any]) -> Order:
        """Create a new order"""
        order = Order(**order_data)
        session.add(order)
        session.commit()
        session.refresh(order)
        
        self.logger.info(f"Created order: {order.symbol} {order.side} {order.original_quantity}",
                        extra_data={"order_id": order.id, "binance_order_id": order.binance_order_id})
        
        return order
    
    def get_order_by_binance_id(self, session: Session, binance_order_id: int) -> Optional[Order]:
        """Get order by Binance order ID"""
        statement = select(Order).where(Order.binance_order_id == binance_order_id)
        return session.exec(statement).first()
    
    def get_orders_by_symbol(self, session: Session, symbol: str, 
                           status: Optional[OrderStatus] = None,
                           limit: int = 100) -> List[Order]:
        """Get orders by symbol with optional status filter"""
        statement = select(Order).where(Order.symbol == symbol)
        
        if status:
            statement = statement.where(Order.status == status)
        
        statement = statement.order_by(desc(Order.created_at)).limit(limit)
        
        return list(session.exec(statement).all())
    
    def get_active_orders(self, session: Session, symbol: Optional[str] = None) -> List[Order]:
        """Get all active orders"""
        active_statuses = [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]
        statement = select(Order).where(Order.status.in_(active_statuses))
        
        if symbol:
            statement = statement.where(Order.symbol == symbol)
        
        return list(session.exec(statement).all())
    
    def update_order_status(self, session: Session, order_id: int, 
                          status: OrderStatus, executed_quantity: Optional[Decimal] = None) -> Optional[Order]:
        """Update order status and executed quantity"""
        order = session.get(Order, order_id)
        if not order:
            return None
        
        order.status = status
        order.updated_at = datetime.now(UTC)
        
        if executed_quantity is not None:
            order.executed_quantity = executed_quantity
        
        session.add(order)
        session.commit()
        session.refresh(order)
        
        self.logger.info(f"Updated order {order_id}: {status}",
                        extra_data={"order_id": order_id, "status": status.value})
        
        return order


class FillOperations:
    def __init__(self):
        self.logger: TradingLoggerAdapter = get_logger("fill_ops")
    
    def create_fill(self, session: Session, fill_data: Dict[str, Any]) -> Fill:
        """Create a new fill"""
        fill = Fill(**fill_data)
        session.add(fill)
        session.commit()
        session.refresh(fill)
        
        self.logger.info(f"Created fill: {fill.symbol} {fill.quantity} @ {fill.price}",
                        extra_data={"fill_id": fill.id, "trade_id": fill.binance_trade_id})
        
        return fill
    
    def get_fills_by_order(self, session: Session, order_id: int) -> List[Fill]:
        """Get all fills for an order"""
        statement = select(Fill).where(Fill.order_id == order_id).order_by(Fill.executed_at)
        return list(session.exec(statement).all())
    
    def get_fills_by_symbol(self, session: Session, symbol: str,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          limit: int = 100) -> List[Fill]:
        """Get fills by symbol with date range"""
        statement = select(Fill).where(Fill.symbol == symbol)
        
        if start_date:
            statement = statement.where(Fill.executed_at >= start_date)
        if end_date:
            statement = statement.where(Fill.executed_at <= end_date)
        
        statement = statement.order_by(desc(Fill.executed_at)).limit(limit)
        
        return list(session.exec(statement).all())
    
    def get_fill_statistics(self, session: Session, symbol: str,
                          start_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get fill statistics for a symbol"""
        statement = select(Fill).where(Fill.symbol == symbol)
        
        if start_date:
            statement = statement.where(Fill.executed_at >= start_date)
        
        fills = list(session.exec(statement).all())
        
        if not fills:
            return {"total_fills": 0, "total_volume": Decimal("0"), "avg_price": None}
        
        total_volume = sum(fill.quantity for fill in fills)
        volume_weighted_price = sum(fill.price * fill.quantity for fill in fills) / total_volume if total_volume > 0 else Decimal("0")
        total_commission = sum(fill.commission for fill in fills)
        
        return {
            "total_fills": len(fills),
            "total_volume": total_volume,
            "avg_price": volume_weighted_price,
            "total_commission": total_commission,
            "buy_fills": len([f for f in fills if f.side == OrderSide.BUY]),
            "sell_fills": len([f for f in fills if f.side == OrderSide.SELL])
        }


class PositionOperations:
    def __init__(self):
        self.logger: TradingLoggerAdapter = get_logger("position_ops")
    
    def upsert_position(self, session: Session, position_data: Dict[str, Any]) -> Position:
        """Create or update position"""
        symbol = position_data["symbol"]
        position_side = position_data.get("position_side", PositionSide.BOTH)
        
        # Try to find existing position
        statement = select(Position).where(
            and_(Position.symbol == symbol, Position.position_side == position_side)
        )
        existing_position = session.exec(statement).first()
        
        if existing_position:
            # Update existing position
            for key, value in position_data.items():
                setattr(existing_position, key, value)
            existing_position.updated_at = datetime.now(UTC)
            
            session.add(existing_position)
            session.commit()
            session.refresh(existing_position)
            
            self.logger.debug(f"Updated position: {symbol} {existing_position.position_amount}")
            return existing_position
        else:
            # Create new position
            position = Position(**position_data)
            position.created_at = datetime.now(UTC)
            position.updated_at = datetime.now(UTC)
            
            session.add(position)
            session.commit()
            session.refresh(position)
            
            self.logger.info(f"Created position: {symbol} {position.position_amount}")
            return position
    
    def get_position(self, session: Session, symbol: str, 
                    position_side: PositionSide = PositionSide.BOTH) -> Optional[Position]:
        """Get position by symbol and side"""
        statement = select(Position).where(
            and_(Position.symbol == symbol, Position.position_side == position_side)
        )
        return session.exec(statement).first()
    
    def get_all_positions(self, session: Session, active_only: bool = True) -> List[Position]:
        """Get all positions"""
        statement = select(Position)
        
        if active_only:
            statement = statement.where(Position.position_amount != 0)
        
        return list(session.exec(statement).all())
    
    def close_position(self, session: Session, symbol: str, 
                      position_side: PositionSide = PositionSide.BOTH) -> bool:
        """Close a position by setting amount to 0"""
        position = self.get_position(session, symbol, position_side)
        if not position:
            return False
        
        position.position_amount = Decimal("0")
        position.unrealized_pnl = Decimal("0")
        position.updated_at = datetime.now(UTC)
        
        session.add(position)
        session.commit()
        
        self.logger.info(f"Closed position: {symbol}")
        return True


class SignalOperations:
    def __init__(self):
        self.logger: TradingLoggerAdapter = get_logger("signal_ops")
    
    def create_signal(self, session: Session, signal_data: Dict[str, Any]) -> Signal:
        """Create a new signal"""
        signal = Signal(**signal_data)
        session.add(signal)
        session.commit()
        session.refresh(signal)
        
        self.logger.info(f"Created signal: {signal.strategy} {signal.symbol} {signal.signal_type}",
                        extra_data={"signal_id": signal.id, "price": float(signal.price)})
        
        return signal
    
    def get_recent_signals(self, session: Session, strategy: Optional[str] = None,
                         symbol: Optional[str] = None, limit: int = 50) -> List[Signal]:
        """Get recent signals with optional filters"""
        statement = select(Signal)
        
        if strategy:
            statement = statement.where(Signal.strategy == strategy)
        if symbol:
            statement = statement.where(Signal.symbol == symbol)
        
        statement = statement.order_by(desc(Signal.created_at)).limit(limit)
        
        return list(session.exec(statement).all())
    
    def get_pending_signals(self, session: Session, symbol: Optional[str] = None) -> List[Signal]:
        """Get signals that haven't been executed yet"""
        statement = select(Signal).where(Signal.executed == False)
        
        if symbol:
            statement = statement.where(Signal.symbol == symbol)
        
        # Only get signals that are still valid
        statement = statement.where(
            or_(Signal.valid_until.is_(None), Signal.valid_until > datetime.now(UTC))
        )
        
        return list(session.exec(statement).all())
    
    def mark_signal_executed(self, session: Session, signal_id: int, 
                           execution_price: Decimal) -> Optional[Signal]:
        """Mark signal as executed"""
        signal = session.get(Signal, signal_id)
        if not signal:
            return None
        
        signal.executed = True
        signal.executed_at = datetime.now(UTC)
        signal.execution_price = execution_price
        
        session.add(signal)
        session.commit()
        session.refresh(signal)
        
        self.logger.info(f"Marked signal {signal_id} as executed @ {execution_price}")
        
        return signal
    
    def get_signal_performance(self, session: Session, strategy: str, 
                             symbol: Optional[str] = None,
                             days: int = 30) -> Dict[str, Any]:
        """Get signal performance statistics"""
        start_date = datetime.now(UTC) - timedelta(days=days)
        
        statement = select(Signal).where(
            and_(
                Signal.strategy == strategy,
                Signal.created_at >= start_date,
                Signal.executed == True
            )
        )
        
        if symbol:
            statement = statement.where(Signal.symbol == symbol)
        
        signals = list(session.exec(statement).all())
        
        if not signals:
            return {"total_signals": 0, "execution_rate": 0}
        
        return {
            "total_signals": len(signals),
            "buy_signals": len([s for s in signals if s.signal_type == SignalType.BUY]),
            "sell_signals": len([s for s in signals if s.signal_type == SignalType.SELL]),
            "avg_confidence": sum(s.confidence for s in signals if s.confidence) / len([s for s in signals if s.confidence]) if any(s.confidence for s in signals) else None,
            "execution_rate": 1.0  # All queried signals are executed
        }


class CandleOperations:
    def __init__(self):
        self.logger: TradingLoggerAdapter = get_logger("candle_ops")
    
    def upsert_candle(self, session: Session, candle_data: Dict[str, Any]) -> Candle1m:
        """Create or update candle data"""
        symbol = candle_data["symbol"]
        open_time = candle_data["open_time"]
        
        # Try to find existing candle
        statement = select(Candle1m).where(
            and_(Candle1m.symbol == symbol, Candle1m.open_time == open_time)
        )
        existing_candle = session.exec(statement).first()
        
        if existing_candle:
            # Update existing candle
            for key, value in candle_data.items():
                setattr(existing_candle, key, value)
            
            session.add(existing_candle)
            session.commit()
            session.refresh(existing_candle)
            
            return existing_candle
        else:
            # Create new candle
            candle = Candle1m(**candle_data)
            session.add(candle)
            session.commit()
            session.refresh(candle)
            
            self.logger.debug(f"Stored candle: {symbol} {open_time} OHLC: {candle.open_price}/{candle.high_price}/{candle.low_price}/{candle.close_price}")
            
            return candle
    
    def get_recent_candles(self, session: Session, symbol: str, 
                          limit: int = 100, closed_only: bool = True) -> List[Candle1m]:
        """Get recent candles for a symbol"""
        statement = select(Candle1m).where(Candle1m.symbol == symbol)
        
        if closed_only:
            statement = statement.where(Candle1m.is_closed == True)
        
        statement = statement.order_by(desc(Candle1m.open_time)).limit(limit)
        
        return list(session.exec(statement).all())
    
    def get_candles_range(self, session: Session, symbol: str,
                         start_time: datetime, end_time: datetime) -> List[Candle1m]:
        """Get candles within a time range"""
        statement = select(Candle1m).where(
            and_(
                Candle1m.symbol == symbol,
                Candle1m.open_time >= start_time,
                Candle1m.open_time <= end_time
            )
        ).order_by(Candle1m.open_time)
        
        return list(session.exec(statement).all())
    
    def cleanup_old_candles(self, session: Session, days_to_keep: int = 30) -> int:
        """Clean up old candle data"""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_to_keep)
        
        # Get count before deletion
        count_statement = select(func.count()).select_from(Candle1m).where(
            Candle1m.open_time < cutoff_date
        )
        count = session.exec(count_statement).one()
        
        # Delete old candles
        delete_statement = text(
            "DELETE FROM candles_1m WHERE open_time < :cutoff_date"
        )
        session.exec(delete_statement, {"cutoff_date": cutoff_date})
        session.commit()
        
        self.logger.info(f"Cleaned up {count} old candles (older than {days_to_keep} days)")
        
        return count


class AccountOperations:
    def __init__(self):
        self.logger: TradingLoggerAdapter = get_logger("account_ops")
    
    def create_snapshot(self, session: Session, snapshot_data: Dict[str, Any]) -> AccountSnapshot:
        """Create account snapshot"""
        snapshot = AccountSnapshot(**snapshot_data)
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
        
        self.logger.debug(f"Created account snapshot: balance={snapshot.total_wallet_balance}")
        
        return snapshot
    
    def get_latest_snapshot(self, session: Session) -> Optional[AccountSnapshot]:
        """Get the most recent account snapshot"""
        statement = select(AccountSnapshot).order_by(desc(AccountSnapshot.created_at)).limit(1)
        return session.exec(statement).first()
    
    def get_snapshots_range(self, session: Session, 
                           start_date: datetime, end_date: datetime) -> List[AccountSnapshot]:
        """Get snapshots within date range"""
        statement = select(AccountSnapshot).where(
            and_(
                AccountSnapshot.created_at >= start_date,
                AccountSnapshot.created_at <= end_date
            )
        ).order_by(AccountSnapshot.created_at)
        
        return list(session.exec(statement).all())


# Convenience class to access all operations
class DatabaseOperations:
    def __init__(self):
        self.orders = OrderOperations()
        self.fills = FillOperations()
        self.positions = PositionOperations()
        self.signals = SignalOperations()
        self.candles = CandleOperations()
        self.account = AccountOperations()


# Global operations instance
db_ops = DatabaseOperations()