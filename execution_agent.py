from datetime import datetime
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
MODE = "paper"

def run_execution_agent(pair, direction, decision, cycle_id=None):
    print(f"\n⚡ Execution Agent - {direction} {pair}...")
    pip = 0.01 if "JPY" in pair else 0.0001
    entry = 1.10000
    stop_pips = decision.get("stop_loss_pips", 25)
    tp_pips = decision.get("take_profit_pips", 50)
    lot_size = decision.get("lot_size", 0.01)
    if direction == "BUY":
        sl = entry - (stop_pips * pip)
        tp = entry + (tp_pips * pip)
    else:
        sl = entry + (stop_pips * pip)
        tp = entry - (tp_pips * pip)
    trade = {
        "cycle_id": cycle_id,
        "pair": pair,
        "direction": direction,
        "entry_price": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "lot_size": lot_size,
        "status": "open",
        "mode": "paper",
        "reasoning": decision.get("reasoning", "")
    }
    result = supabase.table("trades").insert(trade).execute()
    print(f"✅ Paper trade logged: {direction} {pair} @ {entry:.5f}")
    print(f"   SL: {sl:.5f} | TP: {tp:.5f}")
    return result.data[0]