from datetime import datetime, timedelta
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_recent_closed_trades(days=7):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    result = supabase.table("trades").select("*").eq("status", "closed").gte("created_at", since).execute()
    return result.data

def run_learning_agent():
    print(f"\n🧬 Learning Agent running...")
    trades = get_recent_closed_trades(days=7)
    print(f"   Analyzing {len(trades)} closed trades...")
    if not trades:
        print("   No closed trades yet to analyze.")
        return {"message": "No closed trades yet", "recommendations": []}
    winners = [t for t in trades if t.get("pnl", 0) > 0]
    win_rate = len(winners) / len(trades) * 100 if trades else 0
    total_pnl = sum(t.get("pnl", 0) for t in trades)
    result = {
        "total_trades": len(trades),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 2),
        "recommendations": []
    }
    supabase.table("system_logs").insert({
        "agent_name": "learning_agent",
        "event_type": "learning_cycle",
        "message": f"Analyzed {len(trades)} trades. Win rate: {win_rate:.1f}%",
        "details": result
    }).execute()
    print(f"✅ Learning Agent complete. Win rate: {win_rate:.1f}%")
    return result