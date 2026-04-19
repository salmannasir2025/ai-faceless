#!/usr/bin/env python3
"""
FINANCIAL SCOUT
Scans SEC EDGAR, CourtListener, Google Trends, and news for documentary topics.
Optimized for closed cases with public court documentation.
"""

import re
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import feedparser
import time
from core.security_utils import mask_sensitive_data

class FinancialScout:
    """
    Intelligence gatherer for The Ledger.
    Never scrapes illegal content. Only public filings and reported journalism.
    """
    
    def __init__(self, api_manager):
        self.api = api_manager
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "TheLedgerBot/1.0 (Documentary Research; contact@yourdomain.com)"
        })
        
        # SECURITY: Enable SSL verification (default, but explicit for clarity)
        self.session.verify = True
        
        # Rate limiting: Track last request times per domain
        self._last_request_time = {}
        self._min_request_interval = 1.0  # Minimum 1 second between requests to same domain
        
        # Source endpoints
        self.SEC_RSS = "https://www.sec.gov/cgi/browse-edgar?action=getcurrent&owner=include&start=0&count=40&output=atom"
        self.COURTLISTENER_BASE = "https://www.courtlistener.com/api/rest/v3"
        self.TRENDS_API = None  # Would need SERP API or manual scrape; using RSS fallback
    
    def _rate_limited_request(self, method, url, **kwargs):
        """
        Make a rate-limited request to prevent hammering APIs.
        
        Args:
            method: 'get', 'post', etc.
            url: Request URL
            **kwargs: Additional request arguments
            
        Returns:
            Response object
        """
        # Extract domain for rate limiting
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        # Check if we need to wait
        if domain in self._last_request_time:
            elapsed = time.time() - self._last_request_time[domain]
            if elapsed < self._min_request_interval:
                sleep_time = self._min_request_interval - elapsed
                time.sleep(sleep_time)
        
        # Make the request
        request_func = getattr(self.session, method.lower())
        
        # SECURITY: Ensure verify=True and reasonable timeout
        kwargs.setdefault('verify', True)
        kwargs.setdefault('timeout', 15)
        
        try:
            resp = request_func(url, **kwargs)
            self._last_request_time[domain] = time.time()
            return resp
        except requests.exceptions.RequestException as e:
            # SECURITY: Mask sensitive data in error
            safe_error = mask_sensitive_data(str(e))
            raise requests.exceptions.RequestException(f"Request failed: {safe_error}")
    
    def research(self, topic: str, depth: str = "deep") -> Dict:
        """
        Main entry: Returns structured research packet.
        depth: "deep" (long-form documentary) or "shallow" (trading Shorts)
        """
        print(f"  🔍 Researching: {topic}")
        
        packet = {
            "topic": topic,
            "timestamp": datetime.utcnow().isoformat(),
            "depth": depth,
            "sources": [],
            "court_docs": [],
            "quotes": [],
            "timeline": [],
            "entities": [],
            "financial_data": {}
        }
        
        # 1. SEC EDGAR Search (enforcement actions)
        sec_results = self._search_sec(topic)
        packet["sources"].extend(sec_results)
        packet["court_docs"].extend([s for s in sec_results if s["type"] == "sec_filing"])
        
        # 2. CourtListener Docket Search
        court_results = self._search_courtlistener(topic)
        packet["sources"].extend(court_results)
        packet["court_docs"].extend([s for s in court_results if s["type"] == "court_doc"])
        
        # 3. News Aggregation (Reuters/Bloomberg via RSS or NewsAPI)
        news_results = self._search_news(topic)
        packet["sources"].extend(news_results)
        
        # 4. Extract primary quotes from court docs
        packet["quotes"] = self._extract_quotes(packet["court_docs"])
        
        # 5. Build timeline from sources
        packet["timeline"] = self._build_timeline(packet["sources"])
        
        # 6. Extract entities (people, companies, amounts)
        packet["entities"] = self._extract_entities(packet["sources"])
        
        # 7. Financial data (if available via FRED or AlphaVantage)
        if depth == "deep":
            packet["financial_data"] = self._get_market_context(topic)
        print(f"  ✅ Found {len(packet['sources'])} sources, {len(packet['quotes'])} quotable excerpts")
        return packet
    
    # ─── SEC EDGAR ───
    
    def _search_sec(self, topic: str, max_results: int = 5) -> List[Dict]:
        """Search SEC EDGAR for enforcement releases and filings."""
        results = []
        
        try:
            # Get current enforcement RSS
            resp = self._rate_limited_request('get', self.SEC_RSS)
            if resp.status_code != 200:
                return results
            
            feed = feedparser.parse(resp.text)
            
            for entry in feed.entries[:20]:
                title_lower = entry.title.lower()
                summary_lower = getattr(entry, 'summary', '').lower()
                
                # Match topic keywords
                topic_keywords = topic.lower().split()
                if any(kw in title_lower or kw in summary_lower for kw in topic_keywords):
                    results.append({
                        "type": "sec_filing",
                        "title": entry.title,
                        "url": entry.link,
                        "date": getattr(entry, 'published', 'unknown'),
                        "source": "SEC EDGAR",
                        "summary": getattr(entry, 'summary', '')[:500],
                        "confidence": "high"
                    })
                    
                    if len(results) >= max_results:
                        break
                        
        except Exception as e:
            print(f"  ⚠️ SEC search error: {e}")
        
        return results
    
    # ─── COURTLISTENER ───
    
    def _search_courtlistener(self, topic: str, max_results: int = 5) -> List[Dict]:
        """Search CourtListener API for criminal/civil dockets."""
        results = []
        
        try:
            # Search dockets
            params = {
                "type": 5,  # Criminal
                "description__contains": topic.split()[0],  # First keyword
                "ordering": "-date_created"
            }
            resp = self._rate_limited_request(
                'get',
                f"{self.COURTLISTENER_BASE}/dockets/",
                params=params
            )
            
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", [])[:max_results]:
                    results.append({
                        "type": "court_doc",
                        "title": item.get("case_name", "Unknown"),
                        "url": f"https://www.courtlistener.com{item.get('absolute_url', '')}",
                        "date": item.get("date_created", "unknown"),
                        "source": f"CourtListener ({item.get('court', 'Unknown Court')})",
                        "docket_number": item.get("docket_number", "N/A"),
                        "confidence": "high"
                    })
            
            # Also search opinions for written decisions
            opinion_params = {
                "q": topic,
                "type": "o",
                "ordering": "-dateFiled"
            }
            resp_op = self._rate_limited_request(
                'get',
                f"{self.COURTLISTENER_BASE}/search/",
                params=opinion_params
            )
            if resp_op.status_code == 200:
                data_op = resp_op.json()
                for item in data_op.get("results", [])[:3]:
                    results.append({
                        "type": "court_opinion",
                        "title": item.get("caseName", "Unknown"),
                        "url": item.get("absolute_url", ""),
                        "date": item.get("dateFiled", "unknown"),
                        "source": f"CourtListener Opinion ({item.get('court', 'Unknown')})",
                        "judge": item.get("judge", "Unknown"),
                        "confidence": "high"
                    })
                    
        except Exception as e:
            print(f"  ⚠️ CourtListener error: {e}")
        
        return results
    
    # ─── NEWS AGGREGATION ───
    
    def _search_news(self, topic: str, max_results: int = 5) -> List[Dict]:
        """Search reputable financial news via RSS or NewsAPI."""
        results = []
        
        # Reputable finance RSS feeds
        feeds = [
            "https://www.reutersagency.com/feed/?taxonomy=markets&post_type=reuters-best",
            "https://feeds.bbci.co.uk/news/business/rss.xml",
            "https://feeds.bloomberg.com/business/news.rss"
        ]
        
        for feed_url in feeds:
            try:
                resp = self._rate_limited_request('get', feed_url)
                feed = feedparser.parse(resp.text)
                
                for entry in feed.entries[:10]:
                    title = getattr(entry, 'title', '')
                    if any(kw in title.lower() for kw in topic.lower().split()):
                        results.append({
                            "type": "news",
                            "title": title,
                            "url": entry.link,
                            "date": getattr(entry, 'published', 'unknown'),
                            "source": feed_url.split('/')[2],
                            "summary": getattr(entry, 'summary', '')[:300],
                            "confidence": "medium"
                        })
                        
            except Exception as e:
                continue
                
            if len(results) >= max_results:
                break
        
        return results[:max_results]
    
    # ─── EXTRACTION ───
    
    def _extract_quotes(self, court_docs: List[Dict]) -> List[Dict]:
        """Pull quotable excerpts from court documents."""
        quotes = []
        
        for doc in court_docs[:3]:  # Top 3 docs
            try:
                # Fetch the actual document text if possible
                url = doc["url"]
                resp = self._rate_limited_request('get', url)
                
                if resp.status_code == 200:
                    text = resp.text
                    
                    # Extract sentences with $ amounts or shocking admissions
                    pattern = r'([^.]*?\$[\d,]+(?:\.\d{2})?[^.]*\.)'
                    matches = re.findall(pattern, text)
                    
                    for match in matches[:2]:  # Top 2 per doc
                        quotes.append({
                            "text": match.strip(),
                            "source": doc["title"],
                            "page": "N/A",  # Would need PDF parser for real page nums
                            "url": url,
                            "script_timestamp": None  # Set by Scribe later
                        })
                        
            except Exception as e:
                continue
        
        return quotes
    
    def _build_timeline(self, sources: List[Dict]) -> List[Dict]:
        """Chronological events from all sources."""
        events = []
        for src in sources:
            if "date" in src and src["date"] != "unknown":
                events.append({
                    "date": src["date"],
                    "event": src["title"],
                    "source": src["source"],
                    "type": src["type"]
                })
        
        # Sort by date (best effort parsing)
        def parse_date(d):
            try:
                return datetime.strptime(d[:10], "%Y-%m-%d")
            except:
                return datetime.min
        
        events.sort(key=lambda x: parse_date(x["date"]), reverse=True)
        return events
    
    def _extract_entities(self, sources: List[Dict]) -> Dict:
        """Named entities and dollar amounts."""
        all_text = " ".join([s.get("title", "") + " " + s.get("summary", "") for s in sources])
        
        # Dollar amounts
        amounts = re.findall(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(billion|million|thousand)?', all_text)
        
        # Simple company/person extraction (would use NER in production)
        companies = re.findall(r'([A-Z][a-zA-Z&\s]+(?:Inc\.|LLC|Ltd\.|Corp\.|Bank|Exchange))', all_text)
        
        return {
            "dollar_amounts": list(set([f"${a[0]} {a[1]}" for a in amounts])),
            "companies_mentioned": list(set(companies)),
            "people_mentioned": []  # Would need spaCy NER
        }
    
    def _get_market_context(self, topic: str) -> Dict:
        """Get relevant market data for documentary context."""
        context = {}
        
        # If topic involves crypto, get BTC/ETH price context
        if any(kw in topic.lower() for kw in ["crypto", "bitcoin", "ftx", "exchange"]):
            try:
                resp = self._rate_limited_request(
                    'get',
                    "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
                )
                if resp.status_code == 200:
                    context["crypto_prices"] = resp.json()
            except:
                pass
        
        return context