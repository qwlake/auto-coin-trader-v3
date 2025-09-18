# auto-coin-trader-v3

## 프로젝트 구조

- main.py: 프로그램 진입점. 초기화, 이벤트 루프, 모듈 간 연결.
- .env: 환경 변수 파일 (운영 모드, DB URL, 로깅 레벨 등).
- strategies/: 전략 모듈 디렉토리. 각 전략은 독립 파일로 존재.
  - strategies/{전략명}/{심볼}.yaml: 심볼별 전략 설정 파일
- executor/: 거래 실행 모듈. 주문 검증, 리스크 관리, 체결 처리 담당.
- database/: SQLModel 기반 데이터베이스 모델 및 마이그레이션 스크립트.
- utils/: 공통 모듈 (시간 동기화, 정밀도/필터 검증, 로깅, 웹소켓 래퍼).
- config/: 설정 파일 디렉토리 (심볼 리스트, 레버리지, Pydantic 설정).
- dashboard/: Streamlit 기반 실시간 모니터링 대시보드.
- status/: 프로그램 상태 및 헬스체크 파일 저장(heartbeat 등).
- tests/: 단위/통합 테스트 코드.
- logs/: 로그 파일 디렉토리 (gitignore).
- docs/: 프로젝트 문서 디렉토리. 전략 설계 및 거래 규칙 정리.
- Dockerfile: 도커 이미지 빌드 설정 (uv 기반)
- docker-compose.prod.yml: 운영 환경용 도커 컴포즈
- entrypoint.sh: 도커 컨테이너 시작 스크립트

## Docker
- 로컬 개발 환경은 bash 에서 `uv run` 사용
- 서버 운영 환경에서만 Docker 사용
- Docker 운용시 main.py 와 dashboard 둘 다 구성해야함

## 기술 스택
- **Python**: 3.12+
- **패키지 관리**: uv
- **데이터베이스**: SQLite + SQLModel ORM
- **Binance API**: binance-sdk-derivatives-trading-usds-futures
- **모니터링**: Streamlit 대시보드
- **알림**: Slack 통합
- **보안**: 1Password를 통한 API 키 관리
- **클라우드**: AWS 배포 (RDS 자동 백업)
- **로깅**: 구조화 JSON 로깅 (콘솔 + 파일)

## 프로젝트 개요
- Binance Futures 가격을 웹소켓으로 수신하여 자동으로 매수/매도 수행.
- 1분봉 캔들(kline@1m) 및 마크프라이스(markPrice) 스트림을 사용.
- User Data Stream(listenKey)으로 체결/계정 이벤트 수신 (60분마다 keepalive).
- 전략은 독립 모듈 형태로 추가/삭제 가능. 각 전략은 시그널만 생성.
- 거래 실행은 Executor 모듈이 전담. 시그널 수신 후 리스크 체크 + 필터 검증을 거쳐 주문 실행.
- 모든 거래, 시그널, 포지션은 데이터베이스에 기록. 프로그램 재기동 시 동기화(오픈오더, 포지션, 체결내역 복구).
- 향후 비트코인뿐만 아니라 다른 심볼에 대해서도 동시에 거래 가능하도록 확장 계획. (50개 이상 심볼 동시 거래 목표)

## 안전/체계 보강 포인트
- 주문 전 필터 검증: LOT_SIZE, PRICE_FILTER, MIN_NOTIONAL 필수 확인. /exchangeInfo에서 캐시 후 적용.
- 정밀도 관리: Decimal 사용, 가격/수량은 stepSize·tickSize 규칙에 맞게 반올림.
- 시간 동기화: Binance 서버 시간과 로컬 시간 보정. recvWindow 활용.
- 리스크 가드:
  - 전략별 손실 한도, 일일 최대 포지션 수량, 심볼별 최대 노출 금액 제한.
  - 계정 레벨 일일 최대 손실액 및 드로우다운 한도 설정.
  - 주문 실패 시 5회 재시도 (5초 간격), 포지션 청산은 시장가 우선.
  - 주문 TTL(장시간 미체결 → 취소), 연속 손실 시 자동 중단.
  - 펀딩 시각 전후 위험 구간 거래 제한.
- 복구 시나리오: 재시작 시 오픈오더/포지션/체결내역 REST 재조회 → 로컬 DB와 동기화.
- 이벤트 버스: asyncio Queue 기반 신호 전달. signal.*, order.request, order.update 등 이벤트 채널 구분.
- 로깅/가시성: 구조화(JSON) 로깅 + /status/heartbeat.json에 WS/DB/리스크 상태 기록.
- 모니터링/알림: Streamlit 대시보드를 통한 실시간 모니터링, Slack을 통한 중요 이벤트 알림.

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
