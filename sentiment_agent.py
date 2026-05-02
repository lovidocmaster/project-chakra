from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_sentiment_agent(pair, timeframe, cycle_id=None):
    print(f"\n🎭 Sentiment Agent running for {pair}...")
    result = {
        "signal": "NEUTRAL",
        "confidence": 0.60,
        "reasoning": "Retail sentiment balanced. No extreme positioning detected.",
        "retail_bias": "balanced"
    }
    supabase.table("agent_signals").insert({
        "agent_name": "sentiment_agent",
        "pair": pair,
        "timeframe": timeframe,
        "signal": result["signal"],
        "confidence": result["confidence"],
        "reasoning": result["reasoning"],
        "raw_data": result,
        "cycle_id": cycle_id
    }).execute()
    print(f"✅ Sentiment Agent: {result['signal']} | Confidence: {result['confidence']:.0%}")
    return result