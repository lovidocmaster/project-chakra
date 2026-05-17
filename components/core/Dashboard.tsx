'use client';
import React, { useState } from 'react';

export default function Dashboard() {
  const [isDark, setIsDark] = useState(true);
  const [selectedPair, setSelectedPair] = useState('EUR_USD');

  const pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'XAU_USD', 'GBP_JPY'];
  
  const agents = ['Master Orchestrator', 'Chart Analysis', 'News Monitor', 'Sentiment', 'Risk Manager', 'Learning Agent', 'Market Knowledge', 'Execution'];

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
          <button onClick={() => setIsDark(!isDark)} className="px-4 py-2 bg-gray-700 rounded text-sm">
            {isDark ? '☀️ Light' : '🌙 Dark'}
          </button>
          <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded text-sm">● LIVE</span>
          <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded text-sm">11:59:23 UTC</span>
          <span className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded text-sm">LONDON OPEN</span>
        </div>
      </div>

      <div className="grid grid-cols-6 gap-4 mb-8">
        <div className={`${cardBg} p-4 rounded-lg border border-gray-700`}>
          <p className="text-gray-400 text-sm">BALANCE</p>
          <p className="text-2xl font-bold text-green-400">$120,000</p>
        </div>
        <div className={`${cardBg} p-4 rounded-lg border border-gray-700`}>
          <p className="text-gray-400 text-sm">OPEN TRADES</p>
          <p className="text-2xl font-bold text-cyan-400">2</p>
        </div>
        <div className={`${cardBg} p-4 rounded-lg border border-gray-700`}>
          <p className="text-gray-400 text-sm">TOTAL SIGNALS</p>
          <p className="text-2xl font-bold text-yellow-400">247</p>
        </div>
        <div className={`${cardBg} p-4 rounded-lg border border-gray-700`}>
          <p className="text-gray-400 text-sm">WIN RATE</p>
          <p className="text-2xl font-bold text-green-400">65%</p>
        </div>
        <div className={`${cardBg} p-4 rounded-lg border border-gray-700`}>
          <p className="text-gray-400 text-sm">AGENTS ACTIVE</p>
          <p className="text-2xl font-bold text-purple-400">36</p>
        </div>
        <div className={`${cardBg} p-4 rounded-lg border border-gray-700`}>
          <p className="text-gray-400 text-sm">MODE</p>
          <p className="text-2xl font-bold text-red-400">LIVE</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <div className={`${cardBg} p-4 rounded-lg border border-gray-700`}>
            <p className="text-gray-400 text-sm mb-3">TRADING PAIRS</p>
            <div className="grid grid-cols-7 gap-2">
              {pairs.map(pair => (
                <button
                  key={pair}
                  onClick={() => setSelectedPair(pair)}
                  className={`py-2 px-2 rounded text-sm font-bold transition-all ${
                    selectedPair === pair
                      ? 'bg-cyan-500/30 border border-cyan-400 text-cyan-400'
                      : `bg-gray-700 text-gray-300 border border-gray-600`
                  }`}
                >
                  {pair}
                </button>
              ))}
            </div>
          </div>

          <div className={`${cardBg} p-6 rounded-lg border border-gray-700`}>
            <p className="text-gray-400 text-sm mb-4">{selectedPair} - 5MIN CANDLESTICKS</p>
            <div className="h-80 bg-gray-700/30 rounded flex items-center justify-center">
              <div className="text-center">
                <p className="text-4xl font-bold text-cyan-400">1.0845</p>
                <p className="text-gray-400 mt-2">Live price for {selectedPair}</p>
              </div>
            </div>
          </div>

          <div className={`${cardBg} p-6 rounded-lg border border-gray-700`}>
            <p className="text-gray-400 text-sm mb-4">ACTIVE TRADES</p>
            <div className="space-y-3">
              <div className="p-3 rounded border border-gray-600">
                <p className="font-bold">EUR_USD <span className="text-green-400">BUY</span></p>
                <p className="text-sm text-gray-400">Entry: 1.0845 | SL: 1.0820 | TP: 1.0895 | Size: 1.5M</p>
              </div>
              <div className="p-3 rounded border border-gray-600">
                <p className="font-bold">GBP_USD <span className="text-red-400">SELL</span></p>
                <p className="text-sm text-gray-400">Entry: 1.2680 | SL: 1.2705 | TP: 1.2620 | Size: 2.0M</p>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className={`${cardBg} p-6 rounded-lg border border-gray-700`}>
            <p className="text-gray-400 text-sm mb-4">AGENT STATUS - 36 ACTIVE</p>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {agents.map(agent => (
                <div key={agent} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-400"></div>
                    <p className="text-gray-300">{agent}</p>
                  </div>
                  <p className="text-purple-400 font-bold">94%</p>
                </div>
              ))}
            </div>
          </div>

          <div className={`${cardBg} p-6 rounded-lg border border-gray-700`}>
            <p className="text-gray-400 text-sm mb-4">SYSTEM HEALTH</p>
            <div className="space-y-3">
              {[
                { label: 'Confidence', value: 89, color: 'bg-yellow-500' },
                { label: 'Daily Loss', value: 68, color: 'bg-blue-500' },
                { label: 'Drawdown', value: 50, color: 'bg-blue-500' },
                { label: 'GARCH', value: 75, color: 'bg-cyan-500' },
                { label: 'Supabase', value: 100, color: 'bg-purple-500' }
              ].map(metric => (
                <div key={metric.label}>
                  <div className="flex justify-between mb-1 text-xs">
                    <span className="text-gray-400">{metric.label}</span>
                    <span className="text-gray-400">{metric.value}%</span>
                  </div>
                  <div className="w-full h-1 rounded-full bg-gray-700">
                    <div className={`h-full rounded-full ${metric.color}`} style={{width: `${metric.value}%`}}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className={`${cardBg} p-6 rounded-lg border border-gray-700 mt-6`}>
        <p className="text-gray-400 text-sm mb-4">SIGNAL LOG</p>
        <div className="space-y-2 max-h-32 overflow-y-auto text-xs text-gray-400">
          <p>11:59:23 [BUY] EUR_USD @ 1.0845 - Confidence: 94% - 6 agents agree</p>
          <p>11:58:45 [SELL] GBP_USD @ 1.2680 - Confidence: 87% - 5 agents agree</p>
          <p>11:57:22 [HOLD] USD_JPY - Confidence: 65% - Waiting for consensus</p>
          <p>11:56:10 System analyzing 7 pairs across 15-minute timeframes...</p>
          <p>11:55:33 Agents voting on next entry point...</p>
        </div>
      </div>
    </div>
  );
}// Cache bust: 20260517174834
