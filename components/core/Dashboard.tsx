'use client';
import React, { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

export default function Dashboard() {
  const [isDark, setIsDark] = useState(true);
  const [selectedPair, setSelectedPair] = useState('EUR_USD');

  const pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'XAU_USD', 'GBP_JPY'];
  
  const agents = ['Master Orchestrator', 'Chart Analysis', 'News Monitor', 'Sentiment', 'Risk Manager', 'Learning Agent', 'Market Knowledge', 'Execution'];

  const chartData = [
    { time: '10:00', price: 1.0820, high: 1.0835, low: 1.0810, volume: 450 },
    { time: '10:15', price: 1.0835, high: 1.0845, low: 1.0825, volume: 520 },
    { time: '10:30', price: 1.0828, high: 1.0840, low: 1.0820, volume: 380 },
    { time: '10:45', price: 1.0845, high: 1.0860, low: 1.0830, volume: 610 },
    { time: '11:00', price: 1.0852, high: 1.0865, low: 1.0840, volume: 490 },
    { time: '11:15', price: 1.0840, high: 1.0858, low: 1.0835, volume: 540 },
    { time: '11:30', price: 1.0858, high: 1.0870, low: 1.0845, volume: 620 },
    { time: '11:45', price: 1.0865, high: 1.0875, low: 1.0855, volume: 580 },
    { time: '12:00', price: 1.0875, high: 1.0885, low: 1.0860, volume: 700 },
    { time: '12:15', price: 1.0880, high: 1.0890, low: 1.0870, volume: 650 }
  ];

  const bgColor = isDark ? 'bg-gray-900' : 'bg-gray-50';
  const textColor = isDark ? 'text-gray-100' : 'text-gray-900';
  const cardBg = isDark ? 'bg-gray-800' : 'bg-white';

  return (
    <div className={\ \ min-h-screen p-6}>
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
          <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded text-sm">12:24:40 UTC</span>
          <span className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded text-sm">NY/LONDON</span>
        </div>
      </div>

      <div className="grid grid-cols-6 gap-4 mb-8">
        <div className={\ p-4 rounded-lg border border-gray-700}><p className="text-gray-400 text-sm">BALANCE</p><p className="text-2xl font-bold text-green-400\">\,000</p></div>
        <div className={\ p-4 rounded-lg border border-gray-700}><p className="text-gray-400 text-sm">OPEN TRADES</p><p className="text-2xl font-bold text-cyan-400\">2</p></div>
        <div className={\ p-4 rounded-lg border border-gray-700}><p className="text-gray-400 text-sm">TOTAL SIGNALS</p><p className="text-2xl font-bold text-yellow-400\">247</p></div>
        <div className={\ p-4 rounded-lg border border-gray-700}><p className="text-gray-400 text-sm">WIN RATE</p><p className="text-2xl font-bold text-green-400\">65%</p></div>
        <div className={\ p-4 rounded-lg border border-gray-700}><p className="text-gray-400 text-sm">AGENTS ACTIVE</p><p className="text-2xl font-bold text-purple-400\">36</p></div>
        <div className={\ p-4 rounded-lg border border-gray-700}><p className="text-gray-400 text-sm">MODE</p><p className="text-2xl font-bold text-red-400\">LIVE</p></div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <div className={\ p-4 rounded-lg border border-gray-700}><p className="text-gray-400 text-sm mb-3">TRADING PAIRS</p><div className="grid grid-cols-7 gap-2">{pairs.map(pair => (<button key={pair} onClick={() => setSelectedPair(pair)} className={py-2 px-2 rounded text-sm font-bold \}>{pair}</button>))}</div></div>

          <div className={\ p-6 rounded-lg border border-gray-700}>
            <p className="text-gray-400 text-sm mb-4">{selectedPair} - 5MIN CANDLESTICKS</p>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid stroke={isDark ? '#374151' : '#e5e7eb'} />
                <XAxis stroke={isDark ? '#9ca3af' : '#6b7280'} dataKey="time" />
                <YAxis stroke={isDark ? '#9ca3af' : '#6b7280'} domain={['dataMin - 0.001', 'dataMax + 0.001']} />
                <Tooltip contentStyle={{backgroundColor: isDark ? '#1f2937' : '#fff', border: 1px solid \}} formatter={(value) => value.toFixed(4)} />
                <Line type="monotone" dataKey="price" stroke="#06b6d4" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className={\ p-6 rounded-lg border border-gray-700}>
            <p className="text-gray-400 text-sm mb-4">VOLUME ANALYSIS</p>
            <ResponsiveContainer width="100%" height={150}>
              <BarChart data={chartData}>
                <CartesianGrid stroke={isDark ? '#374151' : '#e5e7eb'} />
                <XAxis stroke={isDark ? '#9ca3af' : '#6b7280'} dataKey="time" />
                <YAxis stroke={isDark ? '#9ca3af' : '#6b7280'} />
                <Tooltip contentStyle={{backgroundColor: isDark ? '#1f2937' : '#fff'}} />
                <Bar dataKey="volume" fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className={\ p-6 rounded-lg border border-gray-700}><p className="text-gray-400 text-sm mb-4">ACTIVE TRADES</p><div className="space-y-3"><div className="p-3 rounded border border-gray-600"><p className="font-bold">EUR_USD <span className="text-green-400\">BUY</span></p><p className="text-sm text-gray-400\">Entry: 1.0845 | SL: 1.0820 | TP: 1.0895 | Size: 1.5M</p></div><div className="p-3 rounded border border-gray-600"><p className="font-bold">GBP_USD <span className="text-red-400\">SELL</span></p><p className="text-sm text-gray-400\">Entry: 1.2680 | SL: 1.2705 | TP: 1.2620 | Size: 2.0M</p></div></div></div>
        </div>

        <div className="space-y-6">
          <div className={\ p-6 rounded-lg border border-gray-700}><p className="text-gray-400 text-sm mb-4">AGENT STATUS</p><div className="space-y-2 max-h-80 overflow-y-auto">{agents.map(agent => (<div key={agent} className="flex items-center justify-between text-sm"><div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-green-400\"></div><p className="text-gray-300\">{agent}</p></div><p className="text-purple-400 font-bold\">94%</p></div>))}</div></div>

          <div className={\ p-6 rounded-lg border border-gray-700}><p className="text-gray-400 text-sm mb-4">SYSTEM HEALTH</p><div className="space-y-3">{[{label: 'Confidence', value: 89, color: 'bg-yellow-500'}, {label: 'Daily Loss', value: 68, color: 'bg-blue-500'}, {label: 'Drawdown', value: 50, color: 'bg-blue-500'}, {label: 'GARCH', value: 75, color: 'bg-cyan-500'}, {label: 'Supabase', value: 100, color: 'bg-purple-500'}].map(metric => (<div key={metric.label}><div className="flex justify-between mb-1 text-xs\"><span className="text-gray-400\">{metric.label}</span><span className="text-gray-400\">{metric.value}%</span></div><div className="w-full h-1 rounded-full bg-gray-700\"><div className={h-full rounded-full \} style={{width: \%}}></div></div></div>))}</div></div>
        </div>
      </div>

      <div className={\ p-6 rounded-lg border border-gray-700 mt-6}><p className="text-gray-400 text-sm mb-4">SIGNAL LOG</p><div className="space-y-2 max-h-32 overflow-y-auto text-xs text-gray-400\"><p>12:24:40 [BUY] EUR_USD @ 1.0845 - Confidence: 94%</p><p>12:23:15 [SELL] GBP_USD @ 1.2680 - Confidence: 87%</p><p>12:22:08 [HOLD] USD_JPY - Confidence: 65%</p><p>12:21:22 System analyzing 7 pairs...</p></div></div>
    </div>
  );
}
