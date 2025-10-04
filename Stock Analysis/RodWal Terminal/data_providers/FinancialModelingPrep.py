# rodwal_terminal/data_providers/FinancialModelingPrep.py

import requests
from .base import BaseProvider

class FinancialModelingPrep(BaseProvider):
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get(self, endpoint: str, params: dict = None):
        if params is None:
            params = {}
        params['apikey'] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"[FMP] Error fetching {endpoint}: {e}")
            return None

    def get_quote(self, symbol: str):
        """Fetch latest quote for a symbol"""
        return self._get(f"quote/{symbol}")

    def get_profile(self, symbol: str):
        """Fetch company profile and fundamentals"""
        return self._get(f"profile/{symbol}")

    def get_historical_prices(self, symbol: str, timespan: str = "1mo"):
        """Fetch historical prices (daily)"""
        return self._get(f"historical-price-full/{symbol}", {"serietype": "line"})

    def get_key_metrics(self, symbol: str):
        """Fetch key financial metrics"""
        return self._get(f"key-metrics/{symbol}")

    def get_income_statement(self, symbol: str):
        """Fetch income statement"""
        return self._get(f"income-statement/{symbol}")

    def get_balance_sheet(self, symbol: str):
        """Fetch balance sheet"""
        return self._get(f"balance-sheet-statement/{symbol}")
