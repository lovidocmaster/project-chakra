import React, { useState } from 'react';
import { Sun, Moon } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const Dashboard = () => {
  const [isDark, setIsDark] = useState(true);
  const [selectedPair, setSelectedPair] = useState('EUR_USD');

  const pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD', 'USD_CAD', 'XAU_USD', 'GBP_JPY'];
  
  const chartData = [
    { time: '10:00', price: 1.0820 },
    { time: '10:15', price: 1.0835 },
    { time: '10:30', price: 1.0828 },
    { time: '10:45', price: 1.0845 },
    { time: '11:00', price: 1.0852 },
    { time: '11:15', price: 1.0840 },
    { time: '11:30', price: 1.0858 }
  ];

  const bgColor = isDark ? 'bg-gray-900' : 'bg-gray-50';
  const textColor = isDark ? 'text-gray-100' : 'text-gray-900';
  const cardBg = isDark ? 'bg-gray-800' : 'bg-white';

  return (
    <div className={\ \ min-h-screen p-6}>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold text-cyan-400">PROJECT CHAKRA</h1>
          <p className="text-gray-400">Multi-Agent AI Forex Trading System - 37 Agents</p>
        </div>
        <button onClick={() => setIsDark(!isDark)} className={p-2 rounded-lg \}>
          {isDark ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </div>

      <div className="grid grid-cols-6 gap-4 mb-8">
        <div className={\ p-4 rounded-lg}><p className="text-gray-400 text-sm">BALANCE</p><p className="text-2xl font-bold text-green-400\">\</p></div>
        <div className={\ p-4 rounded-lg}><p className="text-gray-400 text-sm">OPEN TRADES</p><p className="text-2xl font-bold text-cyan-400\">2</p></div>
        <div className={\ p-4 rounded-lg}><p className="text-gray-400 text-sm">TOTAL SIGNALS</p><p className="text-2xl font-bold text-yellow-400\">247</p></div>
        <div className={\ p-4 rounded-lg}><p className="text-gray-400 text-sm">WIN RATE</p><p className="text-2xl font-bold text-green-400\">65%</p></div>
        <div className={\ p-4 rounded-lg}><p className="text-gray-400 text-sm">AGENTS</p><p className="text-2xl font-bold text-purple-400\">36</p></div>
        <div className={\ p-4 rounded-lg}><p className="text-gray-400 text-sm">MODE</p><p className="text-2xl font-bold text-red-400\">LIVE</p></div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <div className={\ p-4 rounded-lg mb-6}>
            <p className="text-gray-400 text-sm mb-3">TRADING PAIRS</p>
            <div className="grid grid-cols-7 gap-2">
              {pairs.map(pair => (
                <button key={pair} onClick={() => setSelectedPair(pair)} className={py-2 px-2 rounded text-sm font-bold \}>
                  {pair}
                </button>
              ))}
            </div>
          </div>

          <div className={\ p-6 rounded-lg}>
            <p className="text-gray-400 text-sm mb-4">{selectedPair} - 5MIN</p>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid stroke="#374151" />
                <XAxis stroke="#9ca3af" dataKey="time" />
                <YAxis stroke="#9ca3af" />
                <Tooltip />
                <Line type="monotone" dataKey="price" stroke="#06b6d4" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className={\ p-6 rounded-lg}>
          <p className="text-gray-400 text-sm mb-4">AGENT STATUS</p>
          <div className="space-y-2">
            {['Master Orchestrator', 'Chart Analysis', 'News Monitor', 'Sentiment', 'Risk Manager', 'Learning Agent', 'Market Knowledge', 'Execution'].map(agent => (
              <div key={agent} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-400\"></div>
                  <p>{agent}</p>
                </div>
                <p className="text-purple-400\">94%</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
