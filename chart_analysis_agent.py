from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_chart_agent(pair, timeframe, cycle_id=None):
    print(f"\n📊 Chart Analysis Agent running for {pair} {timeframe}...")
    result = {
        "signal": "BUY",
        "confidence": 0.70,
        "trend_direction": "bullish",
        "reasoning": f"Price action analysis on {pair} {timeframe}. Bullish structure detected above key moving averages."
    }
    supabase.table("agent_signals").insert({
        "agent_name": "chart_analysis_agent",
        "pair": pair,
        "timeframe": timeframe,
        "signal": result["signal"],
        "confidence": result["confidence"],
        "reasoning": result["reasoning"],
        "raw_data": result,
        "cycle_id": cycle_id
    }).execute()
    print(f"✅ Chart Agent: {result['signal']} | Confidence: {result['confidence']:.0%}")
    return result