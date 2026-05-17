'use client';
import React, { useState } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const Dashboard = () => {
  const [isDark, setIsDark] = useState(true);
  const [selectedPair, setSelectedPair] = useState('EUR_USD');

  const pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'XAU_USD', 'GBP_JPY'];
  
  const chartData = [
    { time: '10:00', price: 1.0820, volume: 450 },
    { time: '10:15', price: 1.0835, volume: 520 },
    { time: '10:30', price: 1.0828, volume: 380 },
    { time: '10:45', price: 1.0845, volume: 610 },
    { time: '11:00', price: 1.0852, volume: 490 },
    { time: '11:15', price: 1.0840, volume: 540 },
    { time: '11:30', price: 1.0858, volume: 620 },
    { time: '11:45', price: 1.0865, volume: 580 },
    { time: '12:00', price: 1.0875, volume: 700 },
    { time: '12:15', price: 1.0880, volume: 650 }
  ];

  const bgColor = isDark ? 'bg-gray-900' : 'bg-gray-50';
  const textColor = isDark ? 'text-gray-100' : 'text-gray-900';
  const cardBg = isDark ? 'bg-gray-800' : 'bg-white';

  return (
    <div className={`${bgColor} ${textColor} min-h-screen p-6`}>
      <div className="flex justify-between items-center mb-8 pb-4 border-b border-gray-700">
        <div>
          <h1 className="text-4xl font-bold text-cyan-400">PROJECT CHAKRA</h1>
          <p className="text-gray-400">Multi-Agent AI Forex Trading System - V15 Complete - 37 Agents</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setIsDark(!isDark)} className="px-4 py-2 bg-gray-700 rounded text-sm font-bold">
            {isDark ? '☀️ LIGHT' : '🌙 DARK'}
          </button>
          <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded text-sm font-bold">● LIVE</span>
          <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded text-sm">12:31:31 UTC</span>
          <span className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded text-sm">NY/LONDON</span>
        </div>
      </div>

      <div className="grid grid-cols-6 gap-4 mb-8">
        <div className={`${cardBg} p-4 rounded border border-gray-700`}>
          <p className="text-gray-400 text-xs">BALANCE</p>
          <p className="text-2xl font-bold text-green-400 mt-1">$120,000</p>
        </div>
        <div className={`${cardBg} p-4 rounded border border-gray-700`}>
          <p className="text-gray-400 text-xs">OPEN TRADES</p>
          <p className="text-2xl font-bold text-cyan-400 mt-1">2</p>
        </div>
        <div className={`${cardBg} p-4 rounded border border-gray-700`}>
          <p className="text-gray-400 text-xs">TOTAL SIGNALS</p>
          <p className="text-2xl font-bold text-yellow-400 mt-1">247</p>
        </div>
        <div className={`${cardBg} p-4 rounded border border-gray-700`}>
          <p className="text-gray-400 text-xs">WIN RATE</p>
          <p className="text-2xl font-bold text-green-400 mt-1">65%</p>
        </div>
        <div className={`${cardBg} p-4 rounded border border-gray-700`}>
          <p className="text-gray-400 text-xs">AGENTS ACTIVE</p>
          <p className="text-2xl font-bold text-purple-400 mt-1">36</p>
        </div>
        <div className={`${cardBg} p-4 rounded border border-gray-700`}>
          <p className="text-gray-400 text-xs">MODE</p>
          <p className="text-2xl font-bold text-red-400 mt-1">LIVE</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          {/* Pairs */}
          <div className={`${cardBg} p-4 rounded border border-gray-700`}>
            <p className="text-gray-400 text-xs font-bold mb-3">TRADING PAIRS</p>
            <div className="grid grid-cols-7 gap-2">
              {pairs.map(pair => (
                <button
                  key={pair}
                  onClick={() => setSelectedPair(pair)}
                  className={`py-2 px-1 rounded text-xs font-bold ${
                    selectedPair === pair
                      ? 'bg-cyan-500/40 border border-cyan-400 text-cyan-300'
                      : 'bg-gray-700 text-gray-400 border border-gray-600'
                  }`}
                >
                  {pair}
                </button>
              ))}
            </div>
          </div>

          {/* Price Chart */}
          <div className={`${cardBg} p-4 rounded border border-gray-700`}>
            <p className="text-gray-400 text-xs font-bold mb-3">{selectedPair} - 5MIN CHART</p>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid stroke="#374151" strokeDasharray="3 3" />
                <XAxis dataKey="time" stroke="#9ca3af" height={30} />
                <YAxis stroke="#9ca3af" width={60} domain="dataMin dataMax" />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: isDark ? '#1f2937' : '#fff',
                    border: '1px solid #374151',
                    borderRadius: '4px',
                    padding: '8px'
                  }}
                  formatter={(value) => [value.toFixed(4), 'Price']}
                  labelFormatter={(label) => `${label}`}
                />
                <Line 
                  type="linear" 
                  dataKey="price" 
                  stroke="#06b6d4" 
                  dot={false} 
                  strokeWidth={2.5}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Volume Chart */}
          <div className={`${cardBg} p-4 rounded border border-gray-700`}>
            <p className="text-gray-400 text-xs font-bold mb-3">VOLUME</p>
            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid stroke="#374151" strokeDasharray="3 3" />
                <XAxis dataKey="time" stroke="#9ca3af" height={25} />
                <YAxis stroke="#9ca3af" width={50} />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: isDark ? '#1f2937' : '#fff',
                    border: '1px solid #374151',
                    borderRadius: '4px'
                  }}
                />
                <Bar dataKey="volume" fill="#8b5cf6" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Active Trades */}
          <div className={`${cardBg} p-4 rounded border border-gray-700`}>
            <p className="text-gray-400 text-xs font-bold mb-3">ACTIVE TRADES</p>
            <div className="space-y-2">
              <div className="p-3 rounded border border-gray-600 bg-gray-700/30">
                <p className="font-bold text-sm">EUR_USD <span className="text-green-400">BUY</span></p>
                <p className="text-xs text-gray-400">Entry: 1.0845 | SL: 1.0820 | TP: 1.0895 | 1.5M</p>
              </div>
              <div className="p-3 rounded border border-gray-600 bg-gray-700/30">
                <p className="font-bold text-sm">GBP_USD <span className="text-red-400">SELL</span></p>
                <p className="text-xs text-gray-400">Entry: 1.2680 | SL: 1.2705 | TP: 1.2620 | 2.0M</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Agents */}
          <div className={`${cardBg} p-4 rounded border border-gray-700 max-h-96 overflow-y-auto`}>
            <p className="text-gray-400 text-xs font-bold mb-3 sticky top-0 bg-gray-800 pb-2">AGENT STATUS</p>
            <div className="space-y-1">
              {['Master Orchestrator', 'Claude LLM Reasoning', 'Event-Driven LSTM', 'Blvellid Optimizer', 'RL Agent', 'HIDARTS TF Allocator', 'FinnMem Memory', 'Trend Agent', 'RSI Agent', 'MACD Agent', 'Bollinger Agent', 'SMC Agent'].map(agent => (
                <div key={agent} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-400"></div>
                    <p className="text-gray-300 truncate">{agent}</p>
                  </div>
                  <p className="text-purple-400 font-bold ml-1">94%</p>
                </div>
              ))}
            </div>
          </div>

          {/* System Health */}
          <div className={`${cardBg} p-4 rounded border border-gray-700`}>
            <p className="text-gray-400 text-xs font-bold mb-3">SYSTEM HEALTH</p>
            <div className="space-y-2">
              {[
                { label: 'Confidence', value: 89, color: 'bg-yellow-500' },
                { label: 'Daily Loss', value: 68, color: 'bg-blue-500' },
                { label: 'Drawdown', value: 50, color: 'bg-blue-500' },
                { label: 'GARCH', value: 75, color: 'bg-cyan-500' },
                { label: 'Supabase', value: 100, color: 'bg-green-500' },
              ].map(m => (
                <div key={m.label}>
                  <div className="flex justify-between mb-0.5 text-xs">
                    <span className="text-gray-400">{m.label}</span>
                    <span className="text-gray-400">{m.value}%</span>
                  </div>
                  <div className="w-full h-1 rounded-full bg-gray-700">
                    <div className={`h-full rounded-full ${m.color}`} style={{width: `${m.value}%`}}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Signal Log */}
      <div className={`${cardBg} p-4 rounded border border-gray-700 mt-6`}>
        <p className="text-gray-400 text-xs font-bold mb-2">SIGNAL LOG</p>
        <div className="space-y-1 max-h-24 overflow-y-auto text-xs text-gray-400">
          <p>12:31:31 [BUY] EUR_USD @ 1.0845 - Confidence: 94% - 6 agents</p>
          <p>12:30:15 [SELL] GBP_USD @ 1.2680 - Confidence: 87% - 5 agents</p>
          <p>12:29:08 [HOLD] USD_JPY - Confidence: 65%</p>
          <p>12:28:22 System analyzing 7 pairs...</p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;