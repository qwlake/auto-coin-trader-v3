# auto-coin-trader-v3

## 프로젝트 구조

- main.py: 프로그램 진입점. 초기화, 이벤트 루프, 모듈 간 연결.
- .env: 환경 변수 파일 (운영 모드, DB URL, 로깅 레벨 등).
- .apikey: API 키 파일 (권한 최소화, gitignore 필수).
- docs/: 프로젝트 문서 디렉토리. 전략 설계 및 거래 규칙 정리.
- strategies/: 전략 모듈 디렉토리. 각 전략은 독립 파일로 존재.
- executor/: 거래 실행 모듈. 주문 검증, 리스크 관리, 체결 처리 담당.
- status/: 프로그램 상태 및 헬스체크 파일 저장(heartbeat 등).
- database/: 데이터베이스 모델 및 마이그레이션 스크립트.
- utils/: 공통 모듈 (시간 동기화, 정밀도/필터 검증, 로깅, 웹소켓 래퍼).
- config/: 설정 파일 디렉토리 (심볼 리스트, 레버리지, Pydantic 설정).
- tests/: 단위/통합 테스트 코드.
- logs/: 로그 파일 디렉토리 (gitignore).

## 프로젝트 설정
- Python 3.12
- uv (패키지/환경 관리)
- logging (구조화 로깅: 콘솔 + 파일 핸들러)
- binance-connector-python

## 프로젝트 개요
- Binance Futures 가격을 웹소켓으로 수신하여 자동으로 매수/매도 수행.
- 1분봉 캔들(kline@1m) 및 마크프라이스(markPrice) 스트림을 사용.
- User Data Stream(listenKey)으로 체결/계정 이벤트 수신 (60분마다 keepalive).
- 전략은 독립 모듈 형태로 추가/삭제 가능. 각 전략은 시그널만 생성.
- 거래 실행은 Executor 모듈이 전담. 시그널 수신 후 리스크 체크 + 필터 검증을 거쳐 주문 실행.
- 모든 거래, 시그널, 포지션은 데이터베이스에 기록. 프로그램 재기동 시 동기화(오픈오더, 포지션, 체결내역 복구).
- 향후 비트코인뿐만 아니라 다른 심볼에 대해서도 동시에 거래 가능하도록 확장 계획.

## 안전/체계 보강 포인트
- 주문 전 필터 검증: LOT_SIZE, PRICE_FILTER, MIN_NOTIONAL 필수 확인. /exchangeInfo에서 캐시 후 적용.
- 정밀도 관리: Decimal 사용, 가격/수량은 stepSize·tickSize 규칙에 맞게 반올림.
- 시간 동기화: Binance 서버 시간과 로컬 시간 보정. recvWindow 활용.
- 리스크 가드:
  - 전략별 손실 한도, 일일 최대 포지션 수량, 심볼별 최대 노출 금액 제한.
  - 주문 TTL(장시간 미체결 → 취소), 연속 손실 시 자동 중단.
  - 펀딩 시각 전후 위험 구간 거래 제한.
- 복구 시나리오: 재시작 시 오픈오더/포지션/체결내역 REST 재조회 → 로컬 DB와 동기화.
- 이벤트 버스: asyncio Queue 기반 신호 전달. signal.*, order.request, order.update 등 이벤트 채널 구분.
- 로깅/가시성: 구조화(JSON) 로깅 + /status/heartbeat.json에 WS/DB/리스크 상태 기록.

## 데이터 모델 (예시)
- orders: 주문 요청 및 상태 (clientOrderId, symbol, qty, price, side, status 등)
- fills: 체결 내역 (tradeId, orderId, price, qty, fee 등)
- positions: 포지션 상태 (symbol, size, entry_price, leverage 등)
- signals: 전략 시그널 기록 (strategy, symbol, side, strength, reason 등)
- candles_1m: 1분봉 데이터 캐시

## 환경 변수 예시 (.env)
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
