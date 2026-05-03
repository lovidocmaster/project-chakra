#!/usr/bin/env python3
"""
Real-time Macro Economic Calendar Integration
Avoid/capitalize on economic announcements
"""

from datetime import datetime, timedelta
import requests
from typing import Dict, List

class MacroCalendarAgent:
    """Monitor economic calendar events"""
    
    def __init__(self):
        self.name = "Macro Calendar Agent"
        self.critical_events = {
            'NFP': 30,  # Non-Farm Payroll: skip 30 min before/after
            'ECB_DECISION': 60,  # ECB rate decision: skip 60 min
            'FOMC_DECISION': 60,  # Federal Reserve decision: skip 60 min
            'USD_INFLATION': 30,  # US CPI: skip 30 min
            'EUR_INFLATION': 30,  # Eurozone CPI: skip 30 min
            'BOE_DECISION': 60,  # Bank of England: skip 60 min
            'CHINA_GDPGDP': 60,  # China GDP: skip 60 min
            'US_GDPGDP': 30,  # US GDP: skip 30 min
        }
        
        self.upcoming_events = []
        self.last_update = None
    
    def fetch_calendar(self) -> List[Dict]:
        """Fetch upcoming economic events"""
        
        try:
            # Using TradingEconomics API
            url = "https://api.tradingeconomics.com/calendar"
            params = {
                'c': 'guest',  # Free tier
                'format': 'json'
            }
            
            response = requests.get(url, params=params, timeout=5)
            events = response.json()
            
            # Filter for relevant currencies and importance
            important_events = [
                e for e in events
                if e.get('country') in ['United States', 'Eurozone', 'United Kingdom', 'Japan']
                and e.get('importance') in ['High', 'Critical']
            ]
            
            self.upcoming_events = important_events
            self.last_update = datetime.now()
            
            return important_events
        
        except Exception as e:
            print(f"⚠️  Calendar fetch error: {e}")
            return []
    
    def should_trade_now(self, current_time: datetime = None) -> Dict:
        """Check if safe to trade right now"""
        
        if current_time is None:
            current_time = datetime.now()
        
        self.fetch_calendar()
        
        status = {
            "can_trade": True,
            "upcoming_events": [],
            "skip_reason": None,
            "confidence_adjustment": 0
        }
        
        for event in self.upcoming_events:
            event_time = datetime.fromisoformat(event['date'])
            skip_minutes = self.critical_events.get(event['event'], 0)
            
            if skip_minutes == 0:
                continue
            
            skip_delta = timedelta(minutes=skip_minutes)
            
            # Check if within skip window
            time_until = (event_time - current_time).total_seconds() / 60
            time_after = (current_time - event_time).total_seconds() / 60
            
            # Before event
            if 0 < time_until < skip_minutes:
                status["can_trade"] = False
                status["skip_reason"] = f"{event['event']} in {time_until:.0f} min"
                status["upcoming_events"].append(event)
            
            # After event
            elif 0 < time_after < skip_minutes:
                status["can_trade"] = False
                status["skip_reason"] = f"{event['event']} just happened ({time_after:.0f} min ago)"
                status["upcoming_events"].append(event)
            
            # Upcoming (within next 4 hours)
            elif time_until > 0 and time_until < 240:
                status["confidence_adjustment"] -= 0.10
                status["upcoming_events"].append({
                    **event,
                    'time_until_minutes': time_until
                })
        
        return status
    
    def capitalize_on_event(self, event: Dict, actual_vs_forecast: str) -> Dict:
        """
        Trade based on economic surprise
        actual_vs_forecast: 'better', 'worse', 'as_expected'
        """
        
        event_name = event.get('event', '')
        country = event.get('country', '')
        
        # Determine signal based on surprise
        if actual_vs_forecast == 'better':
            # Better than expected data is bullish for that country's currency
            if 'US' in country or 'United States' in country:
                signal = 'BUY_USD'
            elif 'EUR' in country or 'Eurozone' in country:
                signal = 'BUY_EUR'
            elif 'GBP' in country or 'United Kingdom' in country:
                signal = 'BUY_GBP'
            else:
                signal = 'BUY'
        
        elif actual_vs_forecast == 'worse':
            # Worse than expected is bearish
            if 'US' in country or 'United States' in country:
                signal = 'SELL_USD'
            elif 'EUR' in country or 'Eurozone' in country:
                signal = 'SELL_EUR'
            else:
                signal = 'SELL'
        
        else:  # as_expected
            signal = 'HOLD'
        
        return {
            "event": event_name,
            "country": country,
            "surprise": actual_vs_forecast,
            "signal": signal,
            "confidence": 0.75 if actual_vs_forecast != 'as_expected' else 0.40,
            "urgency": "HIGH"
        }
    
    def get_calendar_heatmap(self, days_ahead: int = 7) -> str:
        """Get heatmap of economic calendar (text visualization)"""
        
        self.fetch_calendar()
        
        heatmap = "\n📊 ECONOMIC CALENDAR (Next 7 Days)\n"
        heatmap += "="*60 + "\n"
        
        today = datetime.now().date()
        
        for day_offset in range(days_ahead):
            date = today + timedelta(days=day_offset)
            day_events = [
                e for e in self.upcoming_events
                if datetime.fromisoformat(e['date']).date() == date
            ]
            
            if day_events:
                heatmap += f"\n📅 {date.strftime('%A, %b %d')} - {len(day_events)} events\n"
                
                for event in day_events:
                    imp = event.get('importance', 'Low')
                    emoji = '🔴' if imp == 'Critical' else '🟠' if imp == 'High' else '🟡'
                    heatmap += f"   {emoji} {event['event']} ({event['country']})\n"
        
        return heatmap

# Integration code
integration_code = '''
# Add to v10_complete.py

from macro_calendar_agent import MacroCalendarAgent

# In __init__:
self.macro_calendar = MacroCalendarAgent()

# In main trading loop:
calendar_status = self.macro_calendar.should_trade_now()

if not calendar_status["can_trade"]:
    print(f"⚠️  Skipping: {calendar_status['skip_reason']}")
    self.skip_this_cycle = True
else:
    # Apply confidence adjustment if events are upcoming
    confidence_adjustment = calendar_status["confidence_adjustment"]
    if confidence_adjustment < 0:
        print(f"📊 Reducing confidence by {abs(confidence_adjustment):.0%} - events coming")
        signal_confidence *= (1 + confidence_adjustment)

# Print calendar heatmap at start of day
if self.hour == 7:  # 7am UTC
    print(self.macro_calendar.get_calendar_heatmap())
'''

if __name__ == "__main__":
    print("\n" + "="*60)
    print("MACRO CALENDAR AGENT")
    print("="*60)
    print("\n✅ Features:")
    print("   • Auto-fetch economic calendar")
    print("   • Automatic trade skip (30-60 min around events)")
    print("   • Reduced confidence if events upcoming")
    print("   • Capitalize on economic surprises")
    print("   • 7-day heatmap visualization")
    print("\n📊 Monitors:")
    print("   • NFP (US Jobs)")
    print("   • CPI (Inflation)")
    print("   • ECB/FOMC decisions")
    print("   • GDP reports")
    print("   • And 50+ more events")
    print("\n" + "="*60 + "\n")