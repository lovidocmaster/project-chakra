from datetime import date
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

RISK_RULES = {
    "max_open_trades": 3,
    "max_daily_loss_pct": 3.0,
    "min_risk_reward": 1.5,
    "max_risk_per_trade_pct": 1.0
}

def get_open_trades_count():
    result = supabase.table("trades").select("id").eq("status", "open").execute()
    return len(result.data)

def get_todays_pnl():
    today = date.today().isoformat()
    result = supabase.table("trades").select("pnl").gte("created_at", today).eq("status", "closed").execute()
    return sum(t["pnl"] for t in result.data if t["pnl"] is not None)

def run_risk_agent(pair, timeframe, proposed_trade=None, cycle_id=None):
    print(f"\n🛡️  Risk Agent running for {pair}...")
    open_trades = get_open_trades_count()
    todays_pnl = get_todays_pnl()
    approved = open_trades < RISK_RULES["max_open_trades"]
    result = {
        "signal": "APPROVE" if approved else "REJECT",
        "confidence": 0.90,
        "approved": approved,
        "rejection_reason": None if approved else f"Too many open trades: {open_trades}",
        "recommended_lot_size": 0.01,
        "reasoning": f"Open trades: {open_trades}/{RISK_RULES['max_open_trades']}. Today PnL: {todays_pnl:.2f}"
    }
    supabase.table("agent_signals").insert({
        "agent_name": "risk_management_agent",
        "pair": pair,
        "timeframe": timeframe,
        "signal": result["signal"],
        "confidence": result["confidence"],
        "reasoning": result["reasoning"],
        "raw_data": result,
        "cycle_id": cycle_id
    }).execute()
    status = "✅ APPROVED" if approved else "❌ REJECTED"
    print(f"{status} | Confidence: {result['confidence']:.0%}")
    return result