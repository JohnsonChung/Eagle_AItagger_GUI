from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod

@dataclass
class CheckResult:
    """環境檢查結果"""
    name: str
    status: str  # 'pass' | 'fail' | 'warn'
    message: str
    fix_url: Optional[str] = None

class BaseCheck(ABC):
    """環境檢查基底類別"""
    @abstractmethod
    def run(self) -> CheckResult:
        """執行檢查並回傳結果"""
        pass
