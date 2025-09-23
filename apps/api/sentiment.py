from __future__ import annotations

import feedparser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import List
from supabase_client import get_client


RSS_SOURCES = [
  'https://news.google.com/rss/search?q=NSE%20India&hl=en-IN&gl=IN&ceid=IN:en',
]


def fetch_and_store_sentiment(tickers: List[str] | None = None) -> int:
  analyzer = SentimentIntensityAnalyzer()
  sb = get_client()
  count = 0
  for url in RSS_SOURCES:
    feed = feedparser.parse(url)
    for entry in feed.entries[:50]:
      title = entry.title
      link = entry.link
      score = analyzer.polarity_scores(title)['compound']
      # If tickers list given, only store for matched symbols by name substring
      if tickers:
        for t in tickers:
          # naive match
          if t.upper() in title.upper():
            sym = sb.table('symbols').select('id').eq('ticker', t.upper()).limit(1).execute().data
            if not sym:
              continue
            sb.table('sentiment').insert({ 'symbol_id': sym[0]['id'], 'source': 'google_rss', 'title': title, 'url': link, 'score': score }).execute()
            count += 1
      else:
        # global entries without mapping
        pass
  return count


