import os
import json
import requests
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, ANTHROPIC_API_KEY

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_all_strategies():
    result = supabase.table("strategies").select("*").eq("is_active", True).execute()
    return result.data

def find_relevant_strategies(pair, timeframe, market_context):
    strategies = get_all_strategies()
    if not strategies:
        return {"error": "No strategies found"}
    
    strategies_text = ""
    for i, s in enumerate(strategies):
        strategies_text += f"""
Strategy {i+1}: {s['name']}
Description: {s['description']}
Setup: {s['setup_conditions']}
Entry: {s['entry_rules']}
Exit: {s['exit_rules']}
Risk: {s['risk_rules']}
---"""

    prompt = f"""You are the Knowledge Agent in a forex trading system.
Current situation: Pair={pair}, Timeframe={timeframe}, Context={market_context}

Available strategies:
{strategies_text}

Return JSON only:
{{
  "relevant_strategies": [
    {{
      "name": "Strategy Name",
      "relevance_score": 0.85,
      "why_relevant": "explanation",
      "key_rules_to_follow": "rules"
    }}
  ],
  "overall_guidance": "trading guidance paragraph",
  "confidence": 0.75
}}"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    
    raw_text = response.json()['content'][0]['text']
    try:
        return json.loads(raw_text)
    except:
        import re
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        return json.loads(match.group()) if match else {"confidence": 0}

def run_knowledge_agent(pair, timeframe, market_context, cycle_id=None):
    print(f"\n🧠 Knowledge Agent running for {pair} on {timeframe}...")
    result = find_relevant_strategies(pair, timeframe, market_context)
    
    supabase.table("agent_signals").insert({
        "agent_name": "knowledge_agent",
        "pair": pair,
        "timeframe": timeframe,
        "signal": "strategies_retrieved",
        "confidence": result.get("confidence", 0),
        "reasoning": result.get("overall_guidance", ""),
        "raw_data": result,
        "cycle_id": cycle_id
    }).execute()
    
    print(f"✅ Knowledge Agent complete. Confidence: {result.get('confidence', 0):.0%}")
    return result

if __name__ == "__main__":
    result = run_knowledge_agent(
        pair="EUR/USD",
        timeframe="H4",
        market_context="Price above 200 EMA, pulling back to 20 EMA, RSI at 48"
    )
    print(json.dumps(result, indent=2))