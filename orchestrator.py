import json
import requests
from datetime import datetime
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY, ANTHROPIC_API_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def orchestrate_decision(pair, timeframe, agent_reports):
    reports_text = ""
    for r in agent_reports:
        reports_text += f"\nAgent: {r['agent_name'].upper()}\nSignal: {r.get('signal','N/A')}\nConfidence: {r.get('confidence',0)}\nReasoning: {r.get('reasoning','N/A')}\n---"

    prompt = f"""You are the Master Orchestrator of a forex trading system.
Pair: {pair}, Timeframe: {timeframe}
Agent Reports:
{reports_text}
Rules: Only trade if 2+ agents agree. Average confidence must be above 0.65. Risk agent has VETO power.
Return JSON only:
{{"decision":"BUY or SELL or NO_TRADE","confidence":0.75,"pair":"{pair}","reasoning":"explanation","stop_loss_pips":25,"take_profit_pips":50,"lot_size":0.01}}"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    raw = response.json()["content"][0]["text"]
    try:
        return json.loads(raw)
    except:
        import re
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        return json.loads(m.group()) if m else {"decision": "NO_TRADE", "confidence": 0}

def run_orchestrator(pair, timeframe, agent_reports):
    print(f"\n{'='*50}\n🎯 MASTER ORCHESTRATOR - {pair} {timeframe}\n{'='*50}")
    cycle = supabase.table("trading_cycles").insert({
        "pair": pair,
        "timeframe": timeframe,
        "status": "running"
    }).execute()
    cycle_id = cycle.data[0]["id"]
    print(f"\n🤔 Synthesizing {len(agent_reports)} agent reports...")
    decision = orchestrate_decision(pair, timeframe, agent_reports)
    print(f"\n📊 FINAL DECISION: {decision['decision']}")
    print(f"   Confidence: {decision.get('confidence',0):.0%}")
    supabase.table("trading_cycles").update({
        "status": "completed",
        "completed_at": datetime.now().isoformat(),
        "final_decision": decision["decision"],
        "final_reasoning": decision.get("reasoning", ""),
        "trade_placed": False
    }).eq("id", cycle_id).execute()
    return decision, cycle_id