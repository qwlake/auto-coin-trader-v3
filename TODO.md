# TODO: Auto Coin Trader v3 Development Roadmap

## 📋 Confirmed Technical Stack
- **Database**: SQLite + SQLModel ORM
- **Binance API**: `binance-sdk-derivatives-trading-usds-futures`
- **WebSocket**: Built-in binance-connector WebSocket streams
- **Dashboard**: Streamlit for monitoring
- **Alerts**: Slack integration
- **Cloud**: AWS deployment with RDS auto backup
- **Security**: 1Password for API key management

## 🏗️ Phase 1: Core Infrastructure Setup

### 1.1 Project Structure Creation
- [ ] Create directory structure (`strategies/`, `executor/`, `database/`, `utils/`, `config/`, `status/`, `tests/`, `logs/`, `dashboard/`)
- [ ] Set up proper Python package structure with `__init__.py` files
- [ ] Add core dependencies to `pyproject.toml` (SQLModel, streamlit, binance-sdk-derivatives-trading-usds-futures, slack-sdk)

### 1.2 Configuration Management
- [ ] Create configuration models using Pydantic
- [ ] Implement environment variable loading (`.env` file support)
- [ ] Create symbol configuration management
- [ ] Set up API key management system

### 1.3 Logging System
- [ ] Implement structured JSON logging
- [ ] Set up console and file handlers
- [ ] Create log rotation and management
- [ ] Add logging utilities for trading activities

## 🔌 Phase 2: WebSocket & Data Infrastructure

### 2.1 Binance WebSocket Client
- [ ] Create WebSocket wrapper with reconnection logic
- [ ] Implement 1-minute candle (kline@1m) stream handler
- [ ] Implement mark price stream handler  
- [ ] Set up User Data Stream with keepalive (60-minute)
- [ ] Add WebSocket connection health monitoring

### 2.2 Data Processing
- [ ] Create data models for candles, prices, and account events
- [ ] Implement precision management with Decimal
- [ ] Add time synchronization with Binance servers
- [ ] Create data validation and filtering

## 💾 Phase 3: Database Layer

### 3.1 Database Models
- [ ] Design and implement `orders` table
- [ ] Design and implement `fills` table
- [ ] Design and implement `positions` table  
- [ ] Design and implement `signals` table
- [ ] Design and implement `candles_1m` table
- [ ] Add multi-symbol support to all tables

### 3.2 Database Operations
- [ ] Create database connection management
- [ ] Implement CRUD operations for all models
- [ ] Add database migration system
- [ ] Implement state recovery functionality

## 🎯 Phase 4: Strategy Engine

### 4.1 Strategy Framework
- [ ] Create base strategy class/interface
- [ ] Implement strategy registration system
- [ ] Add strategy lifecycle management
- [ ] Create signal generation framework

### 4.2 VWAP Strategy Implementation
- [ ] Implement VWAP calculation
- [ ] Add ADX filter (ADX < 20 for sideways markets)
- [ ] Create VWAP bands with standard deviation
- [ ] Implement entry/exit signal logic
- [ ] Add 5-second volatility safety mechanism

## ⚡ Phase 5: Trade Execution Engine

### 5.1 Order Management
- [ ] Create order validation system (LOT_SIZE, PRICE_FILTER, MIN_NOTIONAL)
- [ ] Implement order placement with Binance API
- [ ] Add order status tracking and updates
- [ ] Create order TTL and cancellation logic

### 5.2 Risk Management
- [ ] Implement strategy-specific loss limits
- [ ] Add daily maximum position quantity limits
- [ ] Create symbol-specific maximum exposure limits
- [ ] Add consecutive loss auto-halt mechanism
- [ ] Implement funding time trading restrictions

## 🔄 Phase 6: Event System

### 6.1 Event Bus Implementation
- [ ] Create asyncio Queue-based event system
- [ ] Define event channels (`signal.*`, `order.request`, `order.update`)
- [ ] Implement event routing and handling
- [ ] Add event logging and monitoring

### 6.2 Integration Layer
- [ ] Connect WebSocket events to event bus
- [ ] Integrate strategy signals with executor
- [ ] Add database event recording
- [ ] Create health monitoring events

## 📊 Phase 7: Monitoring & Health

### 7.1 Health Monitoring
- [ ] Create `/status/heartbeat.json` health check
- [ ] Monitor WebSocket connection status
- [ ] Track database connection health
- [ ] Add risk management status monitoring

### 7.2 State Recovery
- [ ] Implement open orders synchronization on startup
- [ ] Add position recovery from Binance API
- [ ] Create fill history synchronization
- [ ] Add graceful shutdown and restart procedures

## 🚀 Phase 8: Multi-Symbol Expansion

### 8.1 Architecture Enhancement  
- [ ] Refactor for multi-symbol support
- [ ] Create symbol management system
- [ ] Implement per-symbol strategy instances
- [ ] Add cross-symbol risk allocation

### 8.2 Scaling Infrastructure
- [ ] Optimize WebSocket handling for multiple symbols
- [ ] Add symbol-specific configuration management
- [ ] Implement concurrent strategy execution
- [ ] Create symbol performance monitoring

## 🧪 Phase 9: Testing & Validation

### 9.1 Testing Framework
- [ ] Set up pytest testing environment
- [ ] Create unit tests for core components
- [ ] Add integration tests for WebSocket and API
- [ ] Create strategy backtesting framework

### 9.2 Safety & Validation
- [ ] Test order validation logic
- [ ] Validate precision management
- [ ] Test risk management limits
- [ ] Add end-to-end system tests

## 📝 Phase 10: Documentation & Deployment

### 10.1 Documentation
- [ ] Create API documentation
- [ ] Document strategy development guidelines
- [ ] Add deployment instructions
- [ ] Create troubleshooting guide

### 10.2 Deployment
- [ ] Create production configuration
- [ ] Set up logging for production
- [ ] Add monitoring and alerting
- [ ] Create backup and recovery procedures

---

## 🎯 Current Priority: Phase 1 & 2

**Next immediate tasks:**
1. Set up project structure and dependencies (including Streamlit, Slack SDK)
2. Implement SQLModel-based database models
3. Create configuration management with strategy-specific symbol configs
4. Set up binance-sdk-derivatives-trading-usds-futures WebSocket client
5. Implement 1Password integration for secure API key management

**Success Criteria for MVP:**
- WebSocket connection to Binance Futures working
- Basic VWAP strategy generating signals with SQLModel database
- Order execution with 5-retry logic and risk limits
- Streamlit dashboard showing real-time trading status
- Slack alerts for critical events
- All data permanently stored (signals, trades, logs)
- Multi-symbol architecture foundation ready

**Scalability Target:**
- Support for 50+ simultaneous symbol trading
- Modular strategy deployment per symbol
- AWS-ready deployment architecture