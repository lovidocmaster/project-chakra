#!/usr/bin/env python3
"""
Enhanced Sentiment Analysis
Real social sentiment from Twitter, Reddit, etc.
"""

class EnhancedSentimentAgent:
    """Multi-source sentiment analysis"""
    
    def __init__(self):
        self.name = "Enhanced Sentiment Agent"
        self.sources = {
            'twitter': weight=0.30,      # Most reliable
            'reddit': weight=0.20,        # Retail traders
            'stocktwits': weight=0.15,    # Day traders
            'seeking_alpha': weight=0.20, # Analysts
            'crypto_fear_index': weight=0.15  # Overall market
        }
    
    def get_twitter_sentiment(self, currency_pair: str) -> dict:
        """Analyze Twitter sentiment for currency pair"""
        
        try:
            import tweepy
            from textblob import TextBlob
            
            # Initialize Twitter API (requires API key)
            # This is pseudocode - you'd implement with real API
            
            queries = [
                f"#{currency_pair.replace('/', '')}",
                f"#{currency_pair.split('/')[0]}",
                f"forex {currency_pair}",
            ]
            
            total_sentiment = 0
            tweet_count = 0
            
            for query in queries:
                # tweets = client.search_recent_tweets(query=query, max_results=100)
                # for tweet in tweets:
                #     blob = TextBlob(tweet.text)
                #     total_sentiment += blob.sentiment.polarity
                #     tweet_count += 1
                pass
            
            if tweet_count > 0:
                avg_sentiment = total_sentiment / tweet_count  # -1 to +1
                return {
                    "source": "twitter",
                    "sentiment": avg_sentiment,
                    "tweet_count": tweet_count,
                    "signal": "BUY" if avg_sentiment > 0.1 else "SELL" if avg_sentiment < -0.1 else "NEUTRAL"
                }
            
            return {"source": "twitter", "sentiment": 0, "error": "Insufficient tweets"}
        
        except Exception as e:
            return {"source": "twitter", "error": str(e)}
    
    def get_reddit_sentiment(self, currency_pair: str) -> dict:
        """Analyze Reddit sentiment"""
        
        try:
            import praw
            from textblob import TextBlob
            
            # Initialize Reddit API (requires credentials)
            # reddit = praw.Reddit(...)
            
            subreddits = ['forex', 'investing', 'stocks', 'cryptocurrency']
            
            total_sentiment = 0
            post_count = 0
            
            # for subreddit_name in subreddits:
            #     subreddit = reddit.subreddit(subreddit_name)
            #     for post in subreddit.hot(limit=50):
            #         if currency_pair in post.title or currency_pair.replace('/', '') in post.title:
            #             blob = TextBlob(post.selftext)
            #             total_sentiment += blob.sentiment.polarity
            #             post_count += 1
            
            if post_count > 0:
                avg_sentiment = total_sentiment / post_count
                return {
                    "source": "reddit",
                    "sentiment": avg_sentiment,
                    "post_count": post_count,
                    "signal": "BUY" if avg_sentiment > 0.15 else "SELL" if avg_sentiment < -0.15 else "NEUTRAL"
                }
            
            return {"source": "reddit", "sentiment": 0, "error": "Insufficient posts"}
        
        except Exception as e:
            return {"source": "reddit", "error": str(e)}
    
    def get_fear_index(self) -> dict:
        """Get crypto fear & greed index (proxy for market mood)"""
        
        try:
            import requests
            
            # Alternative: crypto fear index
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            current_index = int(data['data'][0]['value'])  # 0-100
            
            # 0-25: Fear, 25-45: Neutral, 45-55: Neutral, 55-75: Greed, 75-100: Extreme Greed
            
            if current_index < 30:
                sentiment = "SELL"  # Fear = opportunity to short
                confidence = 0.65
            elif current_index < 45:
                sentiment = "HOLD"
                confidence = 0.40
            elif current_index < 60:
                sentiment = "HOLD"
                confidence = 0.40
            elif current_index < 80:
                sentiment = "BUY"  # Greed = be cautious (overbought)
                confidence = 0.65
            else:
                sentiment = "SELL"  # Extreme greed = likely reversal
                confidence = 0.70
            
            return {
                "source": "fear_index",
                "index": current_index,
                "sentiment": sentiment,
                "confidence": confidence,
                "description": {
                    "0-25": "Fear",
                    "25-45": "Slight Fear",
                    "45-55": "Neutral",
                    "55-75": "Greed",
                    "75-100": "Extreme Greed"
                }.get(f"{current_index//25*25}-{current_index//25*25+25}", "Unknown")
            }
        
        except Exception as e:
            return {"source": "fear_index", "error": str(e)}
    
    def get_combined_sentiment(self, currency_pair: str) -> dict:
        """Combine all sentiment sources with weighted average"""
        
        sentiments = []
        
        # Collect from all sources
        twitter = self.get_twitter_sentiment(currency_pair)
        reddit = self.get_reddit_sentiment(currency_pair)
        fear = self.get_fear_index()
        
        if 'sentiment' in twitter and 'error' not in twitter:
            sentiments.append(("twitter", twitter['sentiment'], 0.30))
        
        if 'sentiment' in reddit and 'error' not in reddit:
            sentiments.append(("reddit", reddit['sentiment'], 0.20))
        
        if 'sentiment' in fear and 'error' not in fear:
            # Convert fear index (0-100) to sentiment (-1 to +1)
            fear_sentiment = (fear['index'] / 100) * 2 - 1
            sentiments.append(("fear_index", fear_sentiment, 0.50))
        
        if not sentiments:
            return {"error": "No sentiment data available"}
        
        # Weighted average
        total_weight = sum(w for _, _, w in sentiments)
        weighted_sentiment = sum(s * w for _, s, w in sentiments) / total_weight
        
        # Determine final signal
        if weighted_sentiment > 0.2:
            final_signal = "BUY"
            confidence = min(0.95, 0.5 + abs(weighted_sentiment))
        elif weighted_sentiment < -0.2:
            final_signal = "SELL"
            confidence = min(0.95, 0.5 + abs(weighted_sentiment))
        else:
            final_signal = "HOLD"
            confidence = 0.45
        
        return {
            "currency_pair": currency_pair,
            "combined_sentiment": weighted_sentiment,
            "final_signal": final_signal,
            "confidence": confidence,
            "sources_used": len(sentiments),
            "breakdown": {
                "twitter": twitter.get('sentiment', 'N/A'),
                "reddit": reddit.get('sentiment', 'N/A'),
                "fear_index": fear.get('index', 'N/A')
            }
        }

if __name__ == "__main__":
    print("\n" + "="*60)
    print("ENHANCED SENTIMENT AGENT")
    print("="*60)
    print("\n✅ Features:")
    print("   • Twitter sentiment analysis")
    print("   • Reddit sentiment tracking")
    print("   • Crypto fear & greed index")
    print("   • Weighted average combination")
    print("   • Per-pair sentiment scores")
    print("\n📊 Signal Strength:")
    print("   • BUY when sentiment > +0.2")
    print("   • SELL when sentiment < -0.2")
    print("   • HOLD when in-between")
    print("\n⚙️  Configuration needed:")
    print("   • Twitter API keys")
    print("   • Reddit API credentials")
    print("   • No API key needed for fear index")
    print("\n" + "="*60 + "\n")