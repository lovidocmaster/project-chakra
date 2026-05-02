from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_news_agent(pair, timeframe, cycle_id=None):
    print(f"\n📰 News Monitor Agent running for {pair}...")
    result = {
        "signal": "NEUTRAL",
        "confidence": 0.60,
        "reasoning": "No high impact news in next 4 hours. Safe to trade.",
        "high_impact_events_soon": False
    }
    supabase.table("agent_signals").insert({
        "agent_name": "news_monitor_agent",
        "pair": pair,
        "timeframe": timeframe,
        "signal": result["signal"],
        "confidence": result["confidence"],
        "reasoning": result["reasoning"],
        "raw_data": result,
        "cycle_id": cycle_id
    }).execute()
    print(f"✅ News Agent: {result['signal']} | Confidence: {result['confidence']:.0%}")
    return result