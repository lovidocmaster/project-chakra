from knowledge_agent import run_knowledge_agent
from chart_analysis_agent import run_chart_agent
from news_agent import run_news_agent
from sentiment_agent import run_sentiment_agent
from risk_agent import run_risk_agent
from execution_agent import run_execution_agent
from learning_agent import run_learning_agent
from orchestrator import run_orchestrator

WATCHLIST = ["EUR/USD", "GBP/USD", "USD/JPY"]
TIMEFRAME = "H4"

def run_full_cycle(pair, timeframe):
    print(f"\n{'='*60}\n🚀 STARTING FULL CYCLE: {pair} {timeframe}\n{'='*60}")
    agent_reports = []

    knowledge = run_knowledge_agent(pair=pair, timeframe=timeframe, market_context=f"Analyzing {pair} on {timeframe}")
    agent_reports.append({"agent_name":"knowledge_agent","pair":pair,"timeframe":timeframe,"signal":"strategies_retrieved","confidence":knowledge.get("confidence",0.5),"reasoning":knowledge.get("overall_guidance","")})

    chart = run_chart_agent(pair=pair, timeframe=timeframe)
    agent_reports.append({"agent_name":"chart_analysis_agent","pair":pair,"timeframe":timeframe,"signal":chart.get("signal","NEUTRAL"),"confidence":chart.get("confidence",0),"reasoning":chart.get("reasoning","")})

    news = run_news_agent(pair=pair, timeframe=timeframe)
    agent_reports.append({"agent_name":"news_monitor_agent","pair":pair,"timeframe":timeframe,"signal":news.get("signal","NEUTRAL"),"confidence":news.get("confidence",0),"reasoning":news.get("reasoning","")})

    sentiment = run_sentiment_agent(pair=pair, timeframe=timeframe)
    agent_reports.append({"agent_name":"sentiment_agent","pair":pair,"timeframe":timeframe,"signal":sentiment.get("signal","NEUTRAL"),"confidence":sentiment.get("confidence",0),"reasoning":sentiment.get("reasoning","")})

    risk = run_risk_agent(pair=pair, timeframe=timeframe)
    agent_reports.append({"agent_name":"risk_management_agent","pair":pair,"timeframe":timeframe,"signal":risk.get("signal","REJECT"),"confidence":risk.get("confidence",0),"reasoning":risk.get("reasoning","")})

    decision, cycle_id = run_orchestrator(pair, timeframe, agent_reports)

    if decision.get("decision") in ["BUY","SELL"] and risk.get("approved", False):
        run_execution_agent(pair=pair, direction=decision["decision"], decision=decision, cycle_id=cycle_id)
    else:
        print(f"\n⏸️  NO TRADE - Waiting for better setup")

    return decision

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  🤖 FOREX TRADING SYSTEM - STARTING")
    print("  Mode: PAPER TRADING")
    print("="*60)
    run_full_cycle("EUR/USD", TIMEFRAME)