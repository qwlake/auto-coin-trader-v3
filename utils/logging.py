import logging
import logging.handlers
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, 'extra_data'):
            log_obj.update(record.extra_data)
        
        return json.dumps(log_obj, ensure_ascii=False)


class TradingLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        extra_data = kwargs.pop('extra_data', {})
        if self.extra:
            extra_data.update(self.extra)
        
        kwargs['extra'] = {'extra_data': extra_data}
        return msg, kwargs


def setup_logging(
    log_level: str = "INFO",
    console_enabled: bool = True,
    file_enabled: bool = True,
    json_format: bool = True,
    logs_dir: str = "logs"
) -> logging.Logger:
    logs_path = Path(logs_dir)
    logs_path.mkdir(exist_ok=True)
    
    logger = logging.getLogger("auto-coin-trader")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    logger.handlers.clear()
    
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
    
    if console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    if file_enabled:
        file_handler = logging.handlers.RotatingFileHandler(
            logs_path / "trader.log",
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        error_handler = logging.handlers.RotatingFileHandler(
            logs_path / "error.log",
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str, extra_context: Optional[Dict[str, Any]] = None) -> TradingLoggerAdapter:
    base_logger = logging.getLogger("auto-coin-trader").getChild(name)
    return TradingLoggerAdapter(base_logger, extra_context or {})


def log_trade_activity(
    logger: TradingLoggerAdapter,
    activity_type: str,
    symbol: str,
    data: Dict[str, Any],
    level: str = "INFO"
) -> None:
    extra_data = {
        "activity_type": activity_type,
        "symbol": symbol,
        "trade_data": data
    }
    
    message = f"[{activity_type.upper()}] {symbol}: {data.get('action', 'N/A')}"
    
    log_method = getattr(logger, level.lower())
    log_method(message, extra_data=extra_data)