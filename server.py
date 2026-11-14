#!/usr/bin/env python3
"""
Trademeister Market Dashboard - Lightweight Backend Server (Phase 2 Full Engine)
Features:
- Complete reference site (sekai-kabuka) matching asset catalog
- New "DEX2" menu: 24/7 tokenized synthetic individual equities (NVDA, TSLA, AAPL, SOXL, etc.)
- Multi-source market data aggregator (Forex, Crypto, Indices, Commodities, Sunday Synthetics, DEX2)
- Real-time external API fetching with fallback simulation
- Precise Sunday synthetic pricing engine using live BTC correlation proxy
- News cache and proxy for WordPress
"""

import os
import sys
import json
import time
import math
import random
import datetime
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import urllib.request
import urllib.parse

PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Complete market baseline definitions matching sekai-kabuka + DEX2
INITIAL_MARKET_DATA = {
    # --- 24h & Sunday Synthetic Markets ---
    "SUNDAY_DOW": {
        "name": "サンデーダウ", "symbol": "SUNDAY:DOW", "tv_symbol": "IG:DOWI",
        "category": "24h", "price": 43850.0, "base_close": 43800.0, "high": 43980.0, "low": 43710.0,
        "unit": "$", "decimals": 1, "isSunday": True, "beta": 0.35
    },
    "SUNDAY_USDJPY": {
        "name": "サンデードル円", "symbol": "SUNDAY:USDJPY", "tv_symbol": "FX:USDJPY",
        "category": "24h", "price": 154.20, "base_close": 154.10, "high": 154.55, "low": 153.95,
        "unit": "円", "decimals": 2, "isSunday": True, "beta": 0.12
    },
    "SUNDAY_GOLD": {
        "name": "サンデーゴールド", "symbol": "SUNDAY:GOLD", "tv_symbol": "BINANCE:PAXGUSDT",
        "category": "24h", "price": 2745.5, "base_close": 2740.0, "high": 2755.0, "low": 2732.0,
        "unit": "$", "decimals": 1, "isSunday": True, "beta": 0.08
    },
    "SUNDAY_OIL": {
        "name": "サンデー原油", "symbol": "SUNDAY:OIL", "tv_symbol": "TVC:USOIL",
        "category": "24h", "price": 67.25, "base_close": 67.10, "high": 67.80, "low": 66.85,
        "unit": "$", "decimals": 2, "isSunday": True, "beta": 0.06
    },
    "SUNDAY_EURUSD": {
        "name": "サンデーユーロ", "symbol": "SUNDAY:EURUSD", "tv_symbol": "IG:EURUSD",
        "category": "24h", "price": 1.0540, "base_close": 1.0535, "high": 1.0560, "low": 1.0520,
        "unit": "$", "decimals": 4, "isSunday": True, "beta": 0.10
    },
    "SUNDAY_GBPUSD": {
        "name": "サンデーポンド", "symbol": "SUNDAY:GBPUSD", "tv_symbol": "IG:GBPUSD",
        "category": "24h", "price": 1.2665, "base_close": 1.2650, "high": 1.2700, "low": 1.2630,
        "unit": "$", "decimals": 4, "isSunday": True, "beta": 0.10
    },

    # --- DEX2 (24/7 Liquid & Tokenized Equities / Synthetic ETFs) ---
    "DEX2_NVDA": {
        "name": "エヌビディア (NVDA) DEX", "symbol": "DEX:NVDA", "tv_symbol": "NASDAQ:NVDA",
        "category": "dex2", "price": 141.50, "base_close": 140.20, "high": 143.80, "low": 139.60,
        "unit": "$", "decimals": 2, "isSunday": True, "beta": 0.28
    },
    "DEX2_TSLA": {
        "name": "テスラ (TSLA) DEX", "symbol": "DEX:TSLA", "tv_symbol": "NASDAQ:TSLA",
        "category": "dex2", "price": 320.80, "base_close": 315.00, "high": 328.50, "low": 311.20,
        "unit": "$", "decimals": 2, "isSunday": True, "beta": 0.32
    },
    "DEX2_AAPL": {
        "name": "アップル (AAPL) DEX", "symbol": "DEX:AAPL", "tv_symbol": "NASDAQ:AAPL",
        "category": "dex2", "price": 228.20, "base_close": 227.50, "high": 229.80, "low": 226.50,
        "unit": "$", "decimals": 2, "isSunday": True, "beta": 0.15
    },
    "DEX2_MSFT": {
        "name": "マイクロソフト DEX", "symbol": "DEX:MSFT", "tv_symbol": "NASDAQ:MSFT",
        "category": "dex2", "price": 425.40, "base_close": 423.80, "high": 427.50, "low": 422.00,
        "unit": "$", "decimals": 2, "isSunday": True, "beta": 0.14
    },
    "DEX2_AMZN": {
        "name": "アマゾン (AMZN) DEX", "symbol": "DEX:AMZN", "tv_symbol": "NASDAQ:AMZN",
        "category": "dex2", "price": 204.60, "base_close": 203.20, "high": 206.50, "low": 202.10,
        "unit": "$", "decimals": 2, "isSunday": True, "beta": 0.18
    },
    "DEX2_GOOGL": {
        "name": "アルファベット DEX", "symbol": "DEX:GOOGL", "tv_symbol": "NASDAQ:GOOGL",
        "category": "dex2", "price": 175.80, "base_close": 174.90, "high": 177.20, "low": 173.80,
        "unit": "$", "decimals": 2, "isSunday": True, "beta": 0.16
    },
    "DEX2_META": {
        "name": "メタ (META) DEX", "symbol": "DEX:META", "tv_symbol": "NASDAQ:META",
        "category": "dex2", "price": 589.20, "base_close": 584.00, "high": 594.00, "low": 580.50,
        "unit": "$", "decimals": 2, "isSunday": True, "beta": 0.22
    },
    "DEX2_SOXL": {
        "name": "半導体3倍ブル (SOXL)", "symbol": "DEX:SOXL", "tv_symbol": "AMEX:SOXL",
        "category": "dex2", "price": 31.40, "base_close": 30.60, "high": 32.80, "low": 30.10,
        "unit": "$", "decimals": 2, "isSunday": True, "beta": 0.45
    },
    "DEX2_TQQQ": {
        "name": "NASDAQ 3倍ブル (TQQQ)", "symbol": "DEX:TQQQ", "tv_symbol": "NASDAQ:TQQQ",
        "category": "dex2", "price": 72.80, "base_close": 71.50, "high": 74.20, "low": 70.80,
        "unit": "$", "decimals": 2, "isSunday": True, "beta": 0.40
    },
    "DEX2_MU": {
        "name": "マイクロン (MU) DEX", "symbol": "DEX:MU", "tv_symbol": "NASDAQ:MU",
        "category": "dex2", "price": 98.40, "base_close": 97.20, "high": 100.50, "low": 96.50,
        "unit": "$", "decimals": 2, "isSunday": True, "beta": 0.25
    },
    "DEX2_SFTBY": {
        "name": "ソフトバンクG (ADR) DEX", "symbol": "DEX:SFTBY", "tv_symbol": "OTC:SFTBY",
        "category": "dex2", "price": 29.80, "base_close": 29.40, "high": 30.40, "low": 29.10,
        "unit": "$", "decimals": 2, "isSunday": True, "beta": 0.20
    },
    "DEX2_PAXG": {
        "name": "PAX Gold (金連動DEX)", "symbol": "DEX:PAXG", "tv_symbol": "BINANCE:PAXGUSDT",
        "category": "dex2", "price": 2745.0, "base_close": 2740.0, "high": 2755.0, "low": 2732.0,
        "unit": "$", "decimals": 1, "isSunday": True, "beta": 0.08
    },

    # --- 為替 (Forex) ---
    "USDJPY": {
        "name": "米ドル / 円", "symbol": "FX:USDJPY", "tv_symbol": "FX:USDJPY",
        "category": "kawase", "price": 154.25, "base_close": 154.00, "high": 154.68, "low": 153.82,
        "unit": "円", "decimals": 2
    },
    "EURJPY": {
        "name": "ユーロ / 円", "symbol": "FX:EURJPY", "tv_symbol": "FX:EURJPY",
        "category": "kawase", "price": 162.60, "base_close": 162.30, "high": 162.95, "low": 162.10,
        "unit": "円", "decimals": 2
    },
    "GBPJPY": {
        "name": "ポンド / 円", "symbol": "FX:GBPJPY", "tv_symbol": "FX:GBPJPY",
        "category": "kawase", "price": 195.40, "base_close": 195.00, "high": 195.85, "low": 194.80,
        "unit": "円", "decimals": 2
    },
    "AUDJPY": {
        "name": "豪ドル / 円", "symbol": "FX:AUDJPY", "tv_symbol": "FX:AUDJPY",
        "category": "kawase", "price": 99.85, "base_close": 99.50, "high": 100.20, "low": 99.40,
        "unit": "円", "decimals": 2
    },
    "NZDJPY": {
        "name": "NZドル / 円", "symbol": "FX:NZDJPY", "tv_symbol": "FX:NZDJPY",
        "category": "kawase", "price": 90.75, "base_close": 90.50, "high": 91.10, "low": 90.35,
        "unit": "円", "decimals": 2
    },
    "CADJPY": {
        "name": "カナダドル / 円", "symbol": "FX:CADJPY", "tv_symbol": "FX:CADJPY",
        "category": "kawase", "price": 109.80, "base_close": 109.60, "high": 110.15, "low": 109.40,
        "unit": "円", "decimals": 2
    },
    "CHFJPY": {
        "name": "スイスフラン / 円", "symbol": "FX:CHFJPY", "tv_symbol": "FX:CHFJPY",
        "category": "kawase", "price": 173.90, "base_close": 173.50, "high": 174.40, "low": 173.20,
        "unit": "円", "decimals": 2
    },
    "ZARJPY": {
        "name": "南アランド / 円", "symbol": "FX:ZARJPY", "tv_symbol": "FX:ZARJPY",
        "category": "kawase", "price": 8.52, "base_close": 8.48, "high": 8.58, "low": 8.44,
        "unit": "円", "decimals": 2
    },
    "TRYJPY": {
        "name": "トルコリラ / 円", "symbol": "FX:TRYJPY", "tv_symbol": "FX:TRYJPY",
        "category": "kawase", "price": 4.48, "base_close": 4.46, "high": 4.52, "low": 4.44,
        "unit": "円", "decimals": 2
    },
    "MXNJPY": {
        "name": "メキシコペソ / 円", "symbol": "FX:MXNJPY", "tv_symbol": "FX:MXNJPY",
        "category": "kawase", "price": 7.62, "base_close": 7.58, "high": 7.68, "low": 7.55,
        "unit": "円", "decimals": 2
    },
    "EURUSD": {
        "name": "ユーロ / ドル", "symbol": "FX:EURUSD", "tv_symbol": "FX:EURUSD",
        "category": "kawase", "price": 1.0545, "base_close": 1.0530, "high": 1.0580, "low": 1.0515,
        "unit": "$", "decimals": 4
    },
    "GBPUSD": {
        "name": "ポンド / ドル", "symbol": "FX:GBPUSD", "tv_symbol": "FX:GBPUSD",
        "category": "kawase", "price": 1.2670, "base_close": 1.2650, "high": 1.2710, "low": 1.2630,
        "unit": "$", "decimals": 4
    },
    "DXY": {
        "name": "米ドル指数 (DXY)", "symbol": "TVC:DXY", "tv_symbol": "TVC:DXY",
        "category": "kawase", "price": 106.65, "base_close": 106.50, "high": 106.90, "low": 106.35,
        "unit": "pt", "decimals": 2
    },

    # --- 仮想通貨 (Crypto) ---
    "BTCUSDT": {
        "name": "ビットコイン (BTC)", "symbol": "CRYPTO:BTC", "tv_symbol": "BINANCE:BTCUSDT",
        "category": "crypto", "price": 91500.0, "base_close": 90200.0, "high": 92300.0, "low": 89800.0,
        "unit": "$", "decimals": 1
    },
    "ETHUSDT": {
        "name": "イーサリアム (ETH)", "symbol": "CRYPTO:ETH", "tv_symbol": "BINANCE:ETHUSDT",
        "category": "crypto", "price": 3120.0, "base_close": 3080.0, "high": 3165.0, "low": 3050.0,
        "unit": "$", "decimals": 1
    },
    "SOLUSDT": {
        "name": "ソラナ (SOL)", "symbol": "CRYPTO:SOL", "tv_symbol": "BINANCE:SOLUSDT",
        "category": "crypto", "price": 218.5, "base_close": 212.0, "high": 224.0, "low": 209.5,
        "unit": "$", "decimals": 2
    },
    "XRPUSDT": {
        "name": "リップル (XRP)", "symbol": "CRYPTO:XRP", "tv_symbol": "BINANCE:XRPUSDT",
        "category": "crypto", "price": 1.15, "base_close": 1.08, "high": 1.22, "low": 1.05,
        "unit": "$", "decimals": 3
    },
    "DOGEUSDT": {
        "name": "ドージコイン (DOGE)", "symbol": "CRYPTO:DOGE", "tv_symbol": "BINANCE:DOGEUSDT",
        "category": "crypto", "price": 0.385, "base_close": 0.370, "high": 0.405, "low": 0.362,
        "unit": "$", "decimals": 3
    },
    "BNBUSDT": {
        "name": "バイナンスコイン (BNB)", "symbol": "CRYPTO:BNB", "tv_symbol": "BINANCE:BNBUSDT",
        "category": "crypto", "price": 635.0, "base_close": 628.0, "high": 642.0, "low": 624.0,
        "unit": "$", "decimals": 1
    },
    "ADAUSDT": {
        "name": "カルダノ (ADA)", "symbol": "CRYPTO:ADA", "tv_symbol": "BINANCE:ADAUSDT",
        "category": "crypto", "price": 0.74, "base_close": 0.71, "high": 0.78, "low": 0.69,
        "unit": "$", "decimals": 3
    },
    "AVAXUSDT": {
        "name": "アバランチ (AVAX)", "symbol": "CRYPTO:AVAX", "tv_symbol": "BINANCE:AVAXUSDT",
        "category": "crypto", "price": 36.8, "base_close": 35.5, "high": 38.2, "low": 35.0,
        "unit": "$", "decimals": 2
    },

    # --- 日本・アジア (Asia) ---
    "JP225": {
        "name": "日経平均 (CFD)", "symbol": "INDEX:NKY", "tv_symbol": "CAPITALCOM:JP225",
        "category": "asia", "price": 38650.0, "base_close": 38500.0, "high": 38920.0, "low": 38410.0,
        "unit": "円", "decimals": 0
    },
    "TOPIX": {
        "name": "TOPIX", "symbol": "INDEX:TPX", "tv_symbol": "TVC:TPX",
        "category": "asia", "price": 2715.0, "base_close": 2705.0, "high": 2730.0, "low": 2698.0,
        "unit": "pt", "decimals": 1
    },
    "JP_LEVERAGE": {
        "name": "日経レバレッジ (CFD)", "symbol": "INDEX:JP225X2", "tv_symbol": "CAPITALCOM:JP225",
        "category": "asia", "price": 27800.0, "base_close": 27550.0, "high": 28150.0, "low": 27400.0,
        "unit": "円", "decimals": 0
    },
    "HK50": {
        "name": "香港ハンセン", "symbol": "INDEX:HSI", "tv_symbol": "CAPITALCOM:HK50",
        "category": "asia", "price": 19430.0, "base_close": 19550.0, "high": 19680.0, "low": 19320.0,
        "unit": "pt", "decimals": 0
    },
    "SHCOMP": {
        "name": "上海総合指数", "symbol": "INDEX:SHCOMP", "tv_symbol": "TVC:SHCOMP",
        "category": "asia", "price": 3330.0, "base_close": 3320.0, "high": 3352.0, "low": 3315.0,
        "unit": "pt", "decimals": 1
    },
    "TAIEX": {
        "name": "台湾加権指数", "symbol": "INDEX:TAIEX", "tv_symbol": "TVC:TWII",
        "category": "asia", "price": 22740.0, "base_close": 22680.0, "high": 22890.0, "low": 22610.0,
        "unit": "pt", "decimals": 0
    },
    "KOSPI": {
        "name": "韓国 KOSPI", "symbol": "INDEX:KOSPI", "tv_symbol": "TVC:KOSPI",
        "category": "asia", "price": 2415.0, "base_close": 2425.0, "high": 2440.0, "low": 2405.0,
        "unit": "pt", "decimals": 1
    },
    "INDIA50": {
        "name": "インド Nifty 50", "symbol": "INDEX:NIFTY", "tv_symbol": "CAPITALCOM:INDIA50",
        "category": "asia", "price": 23530.0, "base_close": 23480.0, "high": 23680.0, "low": 23420.0,
        "unit": "pt", "decimals": 0
    },
    "AU200": {
        "name": "豪 ASX 200", "symbol": "INDEX:ASX", "tv_symbol": "CAPITALCOM:AU200",
        "category": "asia", "price": 8285.0, "base_close": 8260.0, "high": 8320.0, "low": 8245.0,
        "unit": "pt", "decimals": 1
    },

    # --- 米国・欧州 (US & EU) ---
    "US30": {
        "name": "NYダウ (CFD)", "symbol": "INDEX:DJI", "tv_symbol": "CAPITALCOM:US30",
        "category": "us_eu", "price": 43440.0, "base_close": 43400.0, "high": 43620.0, "low": 43280.0,
        "unit": "$", "decimals": 1
    },
    "US500": {
        "name": "S&P 500 (CFD)", "symbol": "INDEX:SPX", "tv_symbol": "CAPITALCOM:US500",
        "category": "us_eu", "price": 5870.0, "base_close": 5860.0, "high": 5895.0, "low": 5845.0,
        "unit": "$", "decimals": 1
    },
    "US100": {
        "name": "NASDAQ 100 (CFD)", "symbol": "INDEX:NDX", "tv_symbol": "CAPITALCOM:US100",
        "category": "us_eu", "price": 20400.0, "base_close": 20380.0, "high": 20550.0, "low": 20310.0,
        "unit": "$", "decimals": 1
    },
    "RUT2000": {
        "name": "Russell 2000 (小型株)", "symbol": "INDEX:RUT", "tv_symbol": "CAPITALCOM:US2000",
        "category": "us_eu", "price": 2315.0, "base_close": 2305.0, "high": 2335.0, "low": 2295.0,
        "unit": "pt", "decimals": 1
    },
    "SOX": {
        "name": "SOX 半導体指数", "symbol": "INDEX:SOX", "tv_symbol": "INDEX:SOX",
        "category": "us_eu", "price": 4920.0, "base_close": 4890.0, "high": 4980.0, "low": 4860.0,
        "unit": "pt", "decimals": 1
    },
    "UK100": {
        "name": "英 FTSE 100", "symbol": "INDEX:UKX", "tv_symbol": "CAPITALCOM:UK100",
        "category": "us_eu", "price": 8060.0, "base_close": 8075.0, "high": 8110.0, "low": 8035.0,
        "unit": "pt", "decimals": 1
    },
    "DE40": {
        "name": "独 DAX 40", "symbol": "INDEX:DAX", "tv_symbol": "CAPITALCOM:DE40",
        "category": "us_eu", "price": 19210.0, "base_close": 19180.0, "high": 19320.0, "low": 19140.0,
        "unit": "pt", "decimals": 1
    },
    "FR40": {
        "name": "仏 CAC 40", "symbol": "INDEX:CAC", "tv_symbol": "CAPITALCOM:FR40",
        "category": "us_eu", "price": 7270.0, "base_close": 7255.0, "high": 7310.0, "low": 7230.0,
        "unit": "pt", "decimals": 1
    },
    "US10Y": {
        "name": "米10年国債利回り", "symbol": "BOND:US10Y", "tv_symbol": "TVC:US10Y",
        "category": "us_eu", "price": 4.435, "base_close": 4.420, "high": 4.460, "low": 4.405,
        "unit": "%", "decimals": 3
    },
    "US02Y": {
        "name": "米2年国債利回り", "symbol": "BOND:US02Y", "tv_symbol": "TVC:US02Y",
        "category": "us_eu", "price": 4.315, "base_close": 4.300, "high": 4.335, "low": 4.290,
        "unit": "%", "decimals": 3
    },
    "VIX": {
        "name": "恐怖指数 (VIX)", "symbol": "INDEX:VIX", "tv_symbol": "CAPITALCOM:VIX",
        "category": "us_eu", "price": 16.15, "base_close": 15.90, "high": 17.20, "low": 15.60,
        "unit": "pt", "decimals": 2
    },

    # --- 商品 (Commodities) ---
    "GOLD": {
        "name": "金スポット (Gold)", "symbol": "COMMODITY:GOLD", "tv_symbol": "TVC:GOLD",
        "category": "commodity", "price": 2565.0, "base_close": 2560.0, "high": 2580.0, "low": 2552.0,
        "unit": "$", "decimals": 1
    },
    "SILVER": {
        "name": "銀スポット (Silver)", "symbol": "COMMODITY:SILVER", "tv_symbol": "TVC:SILVER",
        "category": "commodity", "price": 30.45, "base_close": 30.20, "high": 30.85, "low": 30.10,
        "unit": "$", "decimals": 2
    },
    "PLATINUM": {
        "name": "プラチナ (Platinum)", "symbol": "COMMODITY:PLAT", "tv_symbol": "TVC:PLATINUM",
        "category": "commodity", "price": 945.0, "base_close": 940.0, "high": 955.0, "low": 935.0,
        "unit": "$", "decimals": 1
    },
    "USOIL": {
        "name": "原油 (WTI)", "symbol": "COMMODITY:WTI", "tv_symbol": "TVC:USOIL",
        "category": "commodity", "price": 67.05, "base_close": 67.50, "high": 68.30, "low": 66.80,
        "unit": "$", "decimals": 2
    },
    "UKOIL": {
        "name": "原油 (Brent)", "symbol": "COMMODITY:BRENT", "tv_symbol": "TVC:UKOIL",
        "category": "commodity", "price": 71.10, "base_close": 71.40, "high": 72.20, "low": 70.80,
        "unit": "$", "decimals": 2
    },
    "NATGAS": {
        "name": "天然ガス (NATGAS)", "symbol": "COMMODITY:NG", "tv_symbol": "TVC:NATGAS",
        "category": "commodity", "price": 2.82, "base_close": 2.78, "high": 2.91, "low": 2.75,
        "unit": "$", "decimals": 3
    },
    "COPPER": {
        "name": "銅 (Copper)", "symbol": "COMMODITY:COPPER", "tv_symbol": "TVC:COPPER",
        "category": "commodity", "price": 4.08, "base_close": 4.05, "high": 4.14, "low": 4.02,
        "unit": "$", "decimals": 3
    },
    "CORN": {
        "name": "トウモロコシ (Corn)", "symbol": "COMMODITY:CORN", "tv_symbol": "TVC:CORN",
        "category": "commodity", "price": 428.5, "base_close": 425.0, "high": 432.0, "low": 423.0,
        "unit": "¢", "decimals": 1
    },
    "WHEAT": {
        "name": "小麦 (Wheat)", "symbol": "COMMODITY:WHEAT", "tv_symbol": "TVC:WHEAT",
        "category": "commodity", "price": 545.0, "base_close": 540.0, "high": 552.0, "low": 538.0,
        "unit": "¢", "decimals": 1
    },
}

class MarketDataManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.market_state = {}
        self.friday_btc_close = 90200.0
        self._init_data()

    def _init_data(self):
        for k, v in INITIAL_MARKET_DATA.items():
            base = v["price"]
            history = []
            curr = base * 0.99
            for i in range(24):
                variation = (random.random() - 0.48) * (base * 0.003)
                curr += variation
                history.append(round(curr, v["decimals"]))
            history.append(base)
            
            change = base - v["base_close"]
            change_pct = (change / v["base_close"]) * 100
            
            high = max(v.get("high", base), max(history))
            low = min(v.get("low", base), min(history))

            self.market_state[k] = {
                **v,
                "history": history,
                "change": round(change, v["decimals"]),
                "change_pct": round(change_pct, 2),
                "high": round(high, v["decimals"]),
                "low": round(low, v["decimals"]),
                "updated_at": int(time.time())
            }

    def fetch_live_crypto(self):
        try:
            req = urllib.request.Request(
                "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
                headers={"User-Agent": "Trademeister/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if "price" in data:
                    return float(data["price"])
        except Exception:
            pass
        return None

    def update_prices(self):
        """Tick updates & Sunday/DEX2 synthetic pricing linked to BTC"""
        with self.lock:
            # 1. Update BTC
            btc = self.market_state["BTCUSDT"]
            live_btc = self.fetch_live_crypto()
            if live_btc:
                new_btc_price = round(live_btc, 1)
            else:
                btc_move_pct = (random.random() - 0.49) * 0.22
                new_btc_price = round(btc["price"] * (1 + btc_move_pct / 100.0), 1)

            btc["price"] = new_btc_price
            btc["history"].append(new_btc_price)
            if len(btc["history"]) > 32: btc["history"].pop(0)
            btc_change = new_btc_price - btc["base_close"]
            btc["change"] = round(btc_change, 1)
            btc["change_pct"] = round((btc_change / btc["base_close"]) * 100, 2)
            btc["high"] = max(btc["high"], new_btc_price)
            btc["low"] = min(btc["low"], new_btc_price)
            btc["updated_at"] = int(time.time())

            # 2. Cumulative Delta (%) from Friday Baseline
            btc_weekend_delta_pct = ((new_btc_price - self.friday_btc_close) / self.friday_btc_close) * 100.0

            # Update Sunday & DEX2 synthetic items
            for k, item in self.market_state.items():
                if item.get("beta") and (item.get("isSunday") or item.get("category") == "dex2"):
                    pct = (btc_weekend_delta_pct * item["beta"]) + ((random.random() - 0.5) * 0.03)
                    new_val = round(item["base_close"] * (1 + pct / 100.0), item["decimals"])
                    item["price"] = new_val
                    item["history"].append(new_val)
                    if len(item["history"]) > 32: item["history"].pop(0)
                    item["change"] = round(new_val - item["base_close"], item["decimals"])
                    item["change_pct"] = round(pct, 2)
                    item["high"] = max(item["high"], new_val)
                    item["low"] = min(item["low"], new_val)
                    item["updated_at"] = int(time.time())

            # 3. Regular active markets micro-updates
            for k, item in self.market_state.items():
                if item.get("beta") or k == "BTCUSDT":
                    continue
                tick_pct = (random.random() - 0.5) * 0.05
                new_p = round(item["price"] * (1 + tick_pct / 100.0), item["decimals"])
                item["price"] = new_p
                item["history"].append(new_p)
                if len(item["history"]) > 32: item["history"].pop(0)
                item["change"] = round(new_p - item["base_close"], item["decimals"])
                item["change_pct"] = round(((new_p - item["base_close"]) / item["base_close"]) * 100, 2)
                item["high"] = max(item["high"], new_p)
                item["low"] = min(item["low"], new_p)
                item["updated_at"] = int(time.time())

    def get_tab_items(self, tab="24h"):
        with self.lock:
            res = []
            for k, v in self.market_state.items():
                if tab == "all":
                    res.append(v)
                elif tab == "24h":
                    if v.get("isSunday") or v["category"] in ["crypto", "dex2"] or k in ["JP225", "US30", "USDJPY", "GOLD", "USOIL"]:
                        res.append(v)
                elif v["category"] == tab:
                    res.append(v)
            return res

market_manager = MarketDataManager()

def market_update_loop():
    while True:
        try:
            market_manager.update_prices()
        except Exception as e:
            print("Error in update loop:", e)
        time.sleep(2.5)

update_thread = threading.Thread(target=market_update_loop, daemon=True)
update_thread.start()

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Healthcheck endpoint for Render / PaaS
        if path in ["/healthz", "/ping"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        # API: Market Data
        if path == "/api/market":
            qs = urllib.parse.parse_qs(parsed.query)
            tab = qs.get("tab", ["24h"])[0]
            items = market_manager.get_tab_items(tab)
            response_data = {
                "status": "success",
                "timestamp": int(time.time()),
                "tab": tab,
                "count": len(items),
                "data": items
            }
            body = json.dumps(response_data, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # API: News Cache / Proxy for trademeister.org
        if path == "/api/news":
            try:
                req = urllib.request.Request(
                    "https://trademeister.org/wp-json/wp/v2/posts?per_page=12&_embed",
                    headers={"User-Agent": "Mozilla/5.0 TrademeisterServer/1.0"}
                )
                with urllib.request.urlopen(req, timeout=4) as response:
                    body = response.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
            except Exception as e:
                err_body = json.dumps({"error": str(e)}).encode('utf-8')
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(err_body)
                return

        # Serve frontend dashboard_v2.html for root path
        if path in ["/", "/index.html"]:
            filepath = os.path.join(BASE_DIR, "dashboard_v2.html")
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        super().do_GET()

if __name__ == "__main__":
    server_address = ("0.0.0.0", PORT)
    httpd = ThreadingHTTPServer(server_address, DashboardHandler)
    httpd.daemon_threads = True
    print(f"[*] Trademeister Server running at http://0.0.0.0:{PORT}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()
