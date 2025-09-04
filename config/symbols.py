from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from decimal import Decimal
import yaml
from pathlib import Path


class SymbolConfig(BaseModel):
    symbol: str
    enabled: bool = True
    leverage: int = Field(default=10, ge=1, le=125)
    position_size_usd: Decimal = Field(default=Decimal("100"), gt=0)
    max_position_size_usd: Decimal = Field(default=Decimal("500"), gt=0)
    daily_max_loss_usd: Decimal = Field(default=Decimal("50"), gt=0)
    profit_target_pct: Decimal = Field(default=Decimal("0.6"), gt=0)
    stop_loss_pct: Decimal = Field(default=Decimal("0.3"), gt=0)
    max_consecutive_losses: int = Field(default=3, ge=1)
    trading_hours_utc: Optional[List[int]] = None  # [0, 23] for 24/7, [9, 17] for 9am-5pm
    strategy_params: Dict = Field(default_factory=dict)


class SymbolManager:
    def __init__(self, symbols_dir: str = "config/symbols"):
        self.symbols_dir = Path(symbols_dir)
        self.symbols_dir.mkdir(exist_ok=True)
        self._configs: Dict[str, SymbolConfig] = {}
    
    def load_symbol_config(self, symbol: str, strategy: str = "vwap") -> SymbolConfig:
        config_path = self.symbols_dir / strategy / f"{symbol.lower()}.yaml"
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
                return SymbolConfig(**data)
        
        default_config = SymbolConfig(symbol=symbol)
        self.save_symbol_config(default_config, strategy)
        return default_config
    
    def save_symbol_config(self, config: SymbolConfig, strategy: str = "vwap") -> None:
        strategy_dir = self.symbols_dir / strategy
        strategy_dir.mkdir(exist_ok=True)
        
        config_path = strategy_dir / f"{config.symbol.lower()}.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config.model_dump(), f, default_flow_style=False)
    
    def get_enabled_symbols(self, strategy: str = "vwap") -> List[str]:
        strategy_dir = self.symbols_dir / strategy
        if not strategy_dir.exists():
            return []
        
        symbols = []
        for config_file in strategy_dir.glob("*.yaml"):
            config = self.load_symbol_config(config_file.stem.upper(), strategy)
            if config.enabled:
                symbols.append(config.symbol)
        
        return symbols
    
    def get_all_symbols(self, strategy: str = "vwap") -> List[str]:
        strategy_dir = self.symbols_dir / strategy
        if not strategy_dir.exists():
            return []
        
        return [config_file.stem.upper() for config_file in strategy_dir.glob("*.yaml")]