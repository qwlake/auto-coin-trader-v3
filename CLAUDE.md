# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **auto-coin-trader-v3**, a Binance Futures automated trading system that receives price data via WebSocket and executes buy/sell operations automatically. The project is in early development with only a basic structure established.

## Development Environment

- **Python**: 3.12+ required
- **Package Manager**: `uv` for package and environment management
- **Virtual Environment**: `.venv` directory (already set up)
- **Database**: SQLite with SQLModel ORM
- **Monitoring**: Streamlit dashboard for real-time monitoring
- **Alerts**: Slack integration for critical events
- **Security**: 1Password for API key management
- **Deployment**: AWS cloud with RDS auto backup

## Common Commands

```bash
# Activate virtual environment and run
uv run python main.py

# Add dependencies
uv add <package_name>

# Install dependencies
uv sync

# Run Streamlit dashboard
uv run streamlit run dashboard/main.py

# Key dependencies to install
uv add sqlmodel fastapi streamlit slack-sdk binance-sdk-derivatives-trading-usds-futures
```

## Project Architecture

The system is designed with a modular architecture (not yet implemented):

### Planned Directory Structure
- `main.py`: Program entry point, initialization, event loop, module connections
- `strategies/`: Strategy modules - each strategy is an independent file generating signals only
  - `strategies/{strategy_name}/{symbol}.yaml`: Symbol-specific strategy configuration files
- `executor/`: Trade execution module handling order validation, risk management, and fill processing
- `database/`: SQLModel-based database models and migration scripts
- `dashboard/`: Streamlit-based real-time monitoring dashboard
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
- **WebSocket Streams**: Uses binance-sdk-derivatives-trading-usds-futures for 1-minute candle (kline@1m) and mark price (markPrice) streams, User Data Stream with 60-minute keepalive
- **Order Execution**: 5-retry logic with 5-second intervals, market order prioritization for position liquidation

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
BINANCE_API_KEY=...         # Retrieved from 1Password
BINANCE_API_SECRET=...      # Retrieved from 1Password
RECV_WINDOW_MS=5000
WS_MAX_BACKOFF_SEC=60
DB_URL=sqlite:///./database/trader.db
LOG_LEVEL=INFO
POSITION_MODE=HEDGE         # or ONEWAY
SLACK_WEBHOOK_URL=...       # For alert notifications
STREAMLIT_PORT=8501
```

### API Keys & Security
- API keys managed through 1Password integration
- Secure credential rotation and access management
- Requires minimum necessary permissions for Binance Futures trading

### Strategy Configuration
- Each strategy has symbol-specific configuration files
- Format: `strategies/{strategy_name}/{symbol}.yaml`
- Supports per-symbol risk limits, position sizing, and strategy parameters

## Risk Management & Safety

### Order Validation
- **Filter Verification**: LOT_SIZE, PRICE_FILTER, MIN_NOTIONAL checks using cached /exchangeInfo
- **Precision Management**: Uses Decimal for price/quantity with stepSize/tickSize rounding
- **Time Synchronization**: Binance server time correction with recvWindow

### Risk Guards
- Strategy-specific loss limits and daily maximum position quantities
- Symbol-specific maximum exposure limits
- **Account-level protection**: Daily maximum loss limits and drawdown thresholds
- **Order management**: 5-retry logic with 5-second intervals, market order liquidation priority
- Order TTL (cancel long-unfilled orders)
- Auto-halt on consecutive losses
- Trading restrictions around funding time periods

### Recovery & Monitoring
- **State Recovery**: On restart, synchronizes open orders/positions/fills via REST API with local DB
- **Structured Logging**: JSON logging with console + file handlers
- **Health Monitoring**: `/status/heartbeat.json` tracks WebSocket/DB/risk status

## Data Models (SQLModel)

Key database tables with multi-symbol support:
- `orders`: Order requests and status tracking (includes symbol field)
- `fills`: Trade execution records (includes symbol field)
- `positions`: Position state management (includes symbol field)
- `signals`: Strategy signal history (includes symbol and strategy fields)
- `candles_1m`: 1-minute candle data cache (includes symbol field)
- `account_stats`: Account-level performance and risk metrics
- `strategy_performance`: Per-strategy, per-symbol performance tracking

**Data Retention Policy**: All data stored permanently for analysis and compliance

## Multi-Symbol Trading Expansion

The system is planned for expansion to support multiple trading pairs simultaneously:

### Design Considerations
- **Symbol Management**: Each symbol should have independent strategy instances and risk limits
- **WebSocket Scaling**: Handle multiple symbol streams efficiently without blocking
- **Database Schema**: Design tables to support multi-symbol data (symbol field in all trading tables)
- **Risk Allocation**: Distribute capital and risk limits across different symbols
- **Strategy Deployment**: Allow different strategies to run on different symbols concurrently

## Monitoring & Alerts

### Streamlit Dashboard
- Real-time trading performance metrics
- Position and order status monitoring
- Strategy performance analysis and charts
- Risk management status displays
- Mobile-friendly responsive design
- **Access**: No authentication required (internal use)

### Slack Integration
- Critical system alerts (connection failures, risk breaches)
- Trading milestone notifications
- Error and exception reporting
- Daily performance summaries

## Development Notes

- This is an early-stage project - most modules are not yet implemented
- Focus on building the core WebSocket data reception and basic trading execution first
- **Design for scalability**: Target 50+ simultaneous symbol trading from architecture design
- **Strategy modularity**: Each symbol can run different strategies independently
- All trading operations should go through proper risk management and validation layers
- Maintain comprehensive logging for all trading activities
- **AWS deployment ready**: Design with cloud deployment and RDS backup in mind