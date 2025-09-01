# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **auto-coin-trader-v3**, a Binance Futures automated trading system that receives price data via WebSocket and executes buy/sell operations automatically. The project is in early development with only a basic structure established.

## Development Environment

- **Python**: 3.12+ required
- **Package Manager**: `uv` for package and environment management
- **Virtual Environment**: `.venv` directory (already set up)

## Common Commands

```bash
# Activate virtual environment and run
uv run python main.py

# Add dependencies
uv add <package_name>

# Install dependencies
uv sync
```

## Project Architecture

The system is designed with a modular architecture (not yet implemented):

### Planned Directory Structure
- `main.py`: Program entry point, initialization, event loop, module connections
- `strategies/`: Strategy modules - each strategy is an independent file generating signals only
- `executor/`: Trade execution module handling order validation, risk management, and fill processing
- `database/`: Database models and migration scripts
- `utils/`: Common modules (time sync, precision/filter validation, logging, WebSocket wrappers)
- `config/`: Configuration files (symbol lists, leverage, Pydantic settings)
- `status/`: Program status and health check files (heartbeat, etc.)
- `tests/`: Unit and integration test code
- `logs/`: Log file directory

### Core Architecture Principles
- **Event-driven**: Uses asyncio Queue-based signal passing with channels like `signal.*`, `order.request`, `order.update`
- **Strategy Independence**: Strategies only generate signals; execution is handled separately by the Executor module
- **Multi-Symbol Support**: Designed for expansion beyond Bitcoin to support simultaneous trading across multiple symbols
- **Database Synchronization**: All trades, signals, and positions are recorded in database with recovery on restart
- **WebSocket Streams**: 1-minute candle (kline@1m) and mark price (markPrice) streams, User Data Stream with 60-minute keepalive

### Trading Strategy
Currently focuses on **VWAP-based mean reversion strategy**:
- Uses ADX filtering (ADX < 20 for sideways markets)
- VWAP bands with standard deviation coefficients
- Target: +0.6% profit, -0.3% stop loss
- Safety mechanism: 5-second volatility check with 10-minute trading halt

## Configuration

### Environment Variables (.env)
```
MODE=testnet                # sim | testnet | mainnet
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
RECV_WINDOW_MS=5000
WS_MAX_BACKOFF_SEC=60
DB_URL=sqlite:///./database/trader.db
LOG_LEVEL=INFO
POSITION_MODE=HEDGE         # or ONEWAY
```

### API Keys
- Stored in `.apikey` file (excluded from git)
- Requires minimum necessary permissions

## Risk Management & Safety

### Order Validation
- **Filter Verification**: LOT_SIZE, PRICE_FILTER, MIN_NOTIONAL checks using cached /exchangeInfo
- **Precision Management**: Uses Decimal for price/quantity with stepSize/tickSize rounding
- **Time Synchronization**: Binance server time correction with recvWindow

### Risk Guards
- Strategy-specific loss limits and daily maximum position quantities
- Symbol-specific maximum exposure limits  
- Order TTL (cancel long-unfilled orders)
- Auto-halt on consecutive losses
- Trading restrictions around funding time periods

### Recovery & Monitoring
- **State Recovery**: On restart, synchronizes open orders/positions/fills via REST API with local DB
- **Structured Logging**: JSON logging with console + file handlers
- **Health Monitoring**: `/status/heartbeat.json` tracks WebSocket/DB/risk status

## Data Models

Key database tables (planned):
- `orders`: Order requests and status tracking
- `fills`: Trade execution records  
- `positions`: Position state management
- `signals`: Strategy signal history
- `candles_1m`: 1-minute candle data cache

## Multi-Symbol Trading Expansion

The system is planned for expansion to support multiple trading pairs simultaneously:

### Design Considerations
- **Symbol Management**: Each symbol should have independent strategy instances and risk limits
- **WebSocket Scaling**: Handle multiple symbol streams efficiently without blocking
- **Database Schema**: Design tables to support multi-symbol data (symbol field in all trading tables)
- **Risk Allocation**: Distribute capital and risk limits across different symbols
- **Strategy Deployment**: Allow different strategies to run on different symbols concurrently

## Development Notes

- This is an early-stage project - most modules are not yet implemented
- Focus on building the core WebSocket data reception and basic trading execution first
- **Design for scalability**: Consider multi-symbol architecture from the beginning to avoid major refactoring later
- All trading operations should go through proper risk management and validation layers
- Maintain comprehensive logging for all trading activities