/**
 * API Client for Project Chakra Dashboard
 * Connects to Railway-deployed Flask backend
 */

const API_BASE_URL = "https://project-chakra-production.up.railway.app";

// Types
export interface AccountMetrics {
  capital: number;
  balance: number;
  equity: number;
  used_margin: number;
  available_margin: number;
  currency: string;
  timestamp: string;
}

export interface PerformanceMetrics {
  win_rate: number;
  sharpe_ratio: number;
  max_drawdown: number;
  monthly_return: number;
  trades_total: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  timestamp: string;
}

export interface Trade {
  id: string;
  pair: string;
  direction: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  size: number;
  opened_at: string;
  closed_at?: string;
  exit_price?: number;
  p_l?: number;
  status: string;
}

export interface SystemStatus {
  status: string;
  timestamp: string;
  backend_version: string;
  agents_active: number;
  uptime_seconds: number;
  database: string;
}

export interface Agent {
  name: string;
  status: string;
  uptime: number;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  agent: string;
}

// API Functions
export const apiClient = {
  // Health & Status
  async getSystemStatus(): Promise<SystemStatus> {
    const response = await fetch(`${API_BASE_URL}/api/system/status`);
    if (!response.ok) throw new Error("Failed to fetch system status");
    return response.json();
  },

  async getSystemHealth() {
    const response = await fetch(`${API_BASE_URL}/api/system/health`);
    if (!response.ok) throw new Error("Failed to fetch system health");
    return response.json();
  },

  // Account
  async getAccountMetrics(): Promise<AccountMetrics> {
    const response = await fetch(`${API_BASE_URL}/api/account/metrics`);
    if (!response.ok) throw new Error("Failed to fetch account metrics");
    return response.json();
  },

  async getPerformanceMetrics(): Promise<PerformanceMetrics> {
    const response = await fetch(`${API_BASE_URL}/api/account/performance`);
    if (!response.ok) throw new Error("Failed to fetch performance metrics");
    return response.json();
  },

  // Trades
  async getOpenTrades(): Promise<Trade[]> {
    const response = await fetch(`${API_BASE_URL}/api/trades/open`);
    if (!response.ok) throw new Error("Failed to fetch open trades");
    const data = await response.json();
    return data.trades;
  },

  async getClosedTrades(limit = 20): Promise<Trade[]> {
    const response = await fetch(`${API_BASE_URL}/api/trades/closed?limit=${limit}`);
    if (!response.ok) throw new Error("Failed to fetch closed trades");
    const data = await response.json();
    return data.trades;
  },

  async createTrade(trade: Partial<Trade>) {
    const response = await fetch(`${API_BASE_URL}/api/trades/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(trade),
    });
    if (!response.ok) throw new Error("Failed to create trade");
    return response.json();
  },

  async closeTrade(tradeId: string, exitPrice: number, pL: number) {
    const response = await fetch(`${API_BASE_URL}/api/trades/close/${tradeId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ exit_price: exitPrice, p_l: pL }),
    });
    if (!response.ok) throw new Error("Failed to close trade");
    return response.json();
  },

  // Agents
  async getAgentsStatus(): Promise<Agent[]> {
    const response = await fetch(`${API_BASE_URL}/api/agents/status`);
    if (!response.ok) throw new Error("Failed to fetch agents status");
    const data = await response.json();
    return data.agents;
  },

  // Logs
  async getSystemLogs(limit = 50): Promise<LogEntry[]> {
    const response = await fetch(`${API_BASE_URL}/api/logs/system?limit=${limit}`);
    if (!response.ok) throw new Error("Failed to fetch system logs");
    const data = await response.json();
    return data.logs;
  },

  async addLog(level: string, message: string, agent: string = "system") {
    const response = await fetch(`${API_BASE_URL}/api/logs/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level, message, agent }),
    });
    if (!response.ok) throw new Error("Failed to add log");
    return response.json();
  },

  // Configuration
  async getInstruments(): Promise<string[]> {
    const response = await fetch(`${API_BASE_URL}/api/config/instruments`);
    if (!response.ok) throw new Error("Failed to fetch instruments");
    const data = await response.json();
    return data.instruments;
  },

  async getRiskConfig() {
    const response = await fetch(`${API_BASE_URL}/api/config/risk`);
    if (!response.ok) throw new Error("Failed to fetch risk config");
    return response.json();
  },
};

export default apiClient;
