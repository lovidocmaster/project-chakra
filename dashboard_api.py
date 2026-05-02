from flask import Flask, jsonify, request
from flask_cors import CORS
from supabase import create_client, Client
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)

# Supabase connection
SUPABASE_URL = "https://jvnaphbygmqjeyawkmnz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp2bmFwaGJ5Z21xamV5YXdrbW56Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTA3NzMyMDAsImV4cCI6MTk4MjM0OTIwMH0.qJ_N5ZZ5vZ5vZ5vZ5vZ5vZ5vZ5vZ5vZ5vZ5vZ5vZ5vZ5"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Helper function to safely get data
def safe_query(table, filters=None):
    try:
        query = supabase.table(table).select("*")
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        return query.execute().data
    except Exception as e:
        print(f"Error querying {table}: {str(e)}")
        return []

# DASHBOARD ENDPOINTS

@app.route('/api/agents-status', methods=['GET'])
def agents_status():
    """Get status of all 8 agents"""
    try:
        logs = safe_query('system_logs', {'type': 'agent_status'})
        
        agents = {
            'Knowledge': {'status': 'idle', 'last_run': None, 'tasks_completed': 0},
            'Chart': {'status': 'idle', 'last_run': None, 'tasks_completed': 0},
            'News': {'status': 'idle', 'last_run': None, 'tasks_completed': 0},
            'Sentiment': {'status': 'idle', 'last_run': None, 'tasks_completed': 0},
            'Risk': {'status': 'idle', 'last_run': None, 'tasks_completed': 0},
            'Execution': {'status': 'idle', 'last_run': None, 'tasks_completed': 0},
            'Learning': {'status': 'idle', 'last_run': None, 'tasks_completed': 0},
            'Orchestrator': {'status': 'idle', 'last_run': None, 'tasks_completed': 0},
        }
        
        for log in logs:
            agent_name = log.get('agent_name')
            if agent_name in agents:
                agents[agent_name]['status'] = log.get('status', 'idle')
                agents[agent_name]['last_run'] = log.get('timestamp')
                agents[agent_name]['tasks_completed'] = log.get('task_count', 0)
        
        return jsonify({
            'success': True,
            'agents': agents,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/live-trades', methods=['GET'])
def live_trades():
    """Get all open trades"""
    try:
        trades = safe_query('trades', {'status': 'open'})
        
        formatted_trades = []
        for trade in trades:
            formatted_trades.append({
                'id': trade.get('id'),
                'pair': trade.get('pair'),
                'type': trade.get('type'),
                'entry_price': float(trade.get('entry_price', 0)),
                'current_price': float(trade.get('current_price', 0)),
                'size': float(trade.get('size', 0)),
                'pnl': float(trade.get('pnl', 0)),
                'pnl_percent': float(trade.get('pnl_percent', 0)),
                'entry_time': trade.get('entry_time'),
                'stop_loss': float(trade.get('stop_loss', 0)) if trade.get('stop_loss') else None,
                'take_profit': float(trade.get('take_profit', 0)) if trade.get('take_profit') else None,
            })
        
        return jsonify({
            'success': True,
            'trades': formatted_trades,
            'total_open': len(formatted_trades),
            'total_pnl': sum(t['pnl'] for t in formatted_trades),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/performance', methods=['GET'])
def performance():
    """Get performance statistics"""
    try:
        trades = safe_query('trades')
        closed_trades = [t for t in trades if t.get('status') == 'closed']
        
        if not closed_trades:
            return jsonify({
                'success': True,
                'win_rate': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'total_pnl': 0
            })
        
        wins = [t for t in closed_trades if float(t.get('pnl', 0)) > 0]
        losses = [t for t in closed_trades if float(t.get('pnl', 0)) < 0]
        
        win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0
        total_pnl = sum(float(t.get('pnl', 0)) for t in closed_trades)
        avg_win = sum(float(t.get('pnl', 0)) for t in wins) / len(wins) if wins else 0
        avg_loss = abs(sum(float(t.get('pnl', 0)) for t in losses) / len(losses)) if losses else 0
        profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
        
        return jsonify({
            'success': True,
            'win_rate': round(win_rate, 2),
            'total_trades': len(closed_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'total_pnl': round(total_pnl, 2),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/equity-curve', methods=['GET'])
def equity_curve():
    """Get equity curve data"""
    try:
        performance_data = safe_query('performance')
        
        equity_points = []
        for data in sorted(performance_data, key=lambda x: x.get('timestamp', '')):
            equity_points.append({
                'timestamp': data.get('timestamp'),
                'equity': float(data.get('equity', 0)),
                'daily_pnl': float(data.get('daily_pnl', 0))
            })
        
        return jsonify({
            'success': True,
            'equity_curve': equity_points,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/signals', methods=['GET'])
def signals():
    """Get recent agent signals"""
    try:
        signals_data = safe_query('agent_signals')
        
        formatted_signals = []
        for signal in signals_data[-50:]:  # Last 50 signals
            formatted_signals.append({
                'id': signal.get('id'),
                'agent': signal.get('agent_name'),
                'pair': signal.get('pair'),
                'signal': signal.get('signal_type'),
                'confidence': float(signal.get('confidence', 0)),
                'timestamp': signal.get('timestamp'),
                'details': signal.get('details')
            })
        
        return jsonify({
            'success': True,
            'signals': formatted_signals,
            'total': len(formatted_signals),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system-logs', methods=['GET'])
def system_logs():
    """Get recent system logs"""
    try:
        logs = safe_query('system_logs')
        
        formatted_logs = []
        for log in logs[-100:]:  # Last 100 logs
            formatted_logs.append({
                'timestamp': log.get('timestamp'),
                'level': log.get('level'),
                'message': log.get('message'),
                'agent_name': log.get('agent_name'),
                'type': log.get('type')
            })
        
        return jsonify({
            'success': True,
            'logs': formatted_logs,
            'total': len(formatted_logs),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/trading-cycles', methods=['GET'])
def trading_cycles():
    """Get trading cycles"""
    try:
        cycles = safe_query('trading_cycles')
        
        formatted_cycles = []
        for cycle in cycles[-20:]:  # Last 20 cycles
            formatted_cycles.append({
                'id': cycle.get('id'),
                'cycle_number': cycle.get('cycle_number'),
                'start_time': cycle.get('start_time'),
                'end_time': cycle.get('end_time'),
                'trades_executed': cycle.get('trades_executed', 0),
                'cycle_pnl': float(cycle.get('cycle_pnl', 0)),
                'status': cycle.get('status')
            })
        
        return jsonify({
            'success': True,
            'cycles': formatted_cycles,
            'total': len(formatted_cycles),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard-summary', methods=['GET'])
def dashboard_summary():
    """Get all dashboard data in one call"""
    try:
        trades = safe_query('trades')
        open_trades = [t for t in trades if t.get('status') == 'open']
        closed_trades = [t for t in trades if t.get('status') == 'closed']
        
        total_pnl = sum(float(t.get('pnl', 0)) for t in closed_trades)
        open_pnl = sum(float(t.get('pnl', 0)) for t in open_trades)
        
        wins = [t for t in closed_trades if float(t.get('pnl', 0)) > 0]
        win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0
        
        logs = safe_query('system_logs', {'type': 'agent_status'})
        agents_count = {}
        for log in logs:
            agent = log.get('agent_name')
            agents_count[agent] = agents_count.get(agent, 0) + 1
        
        return jsonify({
            'success': True,
            'summary': {
                'open_trades': len(open_trades),
                'closed_trades': len(closed_trades),
                'total_pnl': round(total_pnl, 2),
                'open_pnl': round(open_pnl, 2),
                'win_rate': round(win_rate, 2),
                'active_agents': len(agents_count),
                'total_agents': 8,
                'system_status': 'RUNNING',
                'last_update': datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})

if __name__ == '__main__':
    print("🚀 Dashboard API Starting on http://localhost:5000")
    print("📊 Open dashboard at http://localhost:3000")
    app.run(debug=False, host='0.0.0.0', port=5000)