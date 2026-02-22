import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

function App() {
  const [data, setData] = useState([]);
  const [metrics, setMetrics] = useState({ tps: 0, latency_ms: 0, tx_total: 0, gaming_total: 0 });

  useEffect(() => {
    const ws = new WebSocket('ws://127.0.0.1:8000/api/v1/ws/metrics');

    ws.onmessage = (event) => {
      const parsed = JSON.parse(event.data);
      const newPoint = {
        time: new Date(parsed.timestamp * 1000).toLocaleTimeString([], { hour12: false }),
        tps: parsed.tps,
        latency: parsed.latency_ms
      };

      setMetrics(parsed);
      setData(prev => {
        const newData = [...prev, newPoint];
        if (newData.length > 20) newData.shift();
        return newData;
      });
    };

    return () => ws.close();
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8 font-sans">
      <header className="mb-8 border-b border-slate-700 pb-4">
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
          Hydra Micro-PaaS Dashboard
        </h1>
        <p className="text-slate-400 mt-2">Real-time metrics for Milestone 2: Micropayment & Gaming</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
          <h3 className="text-slate-400 text-sm uppercase tracking-wider">Live TPS</h3>
          <p className="text-4xl font-mono font-bold text-emerald-400 mt-2">{metrics.tps.toFixed(1)}</p>
        </div>
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
          <h3 className="text-slate-400 text-sm uppercase tracking-wider">Avg Latency</h3>
          <p className="text-4xl font-mono font-bold text-blue-400 mt-2">{metrics.latency_ms.toFixed(1)} <span className="text-xl">ms</span></p>
        </div>
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
          <h3 className="text-slate-400 text-sm uppercase tracking-wider">Total Micro-Txs</h3>
          <p className="text-4xl font-mono font-bold text-purple-400 mt-2">{metrics.tx_total}</p>
        </div>
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
          <h3 className="text-slate-400 text-sm uppercase tracking-wider">Gaming Events</h3>
          <p className="text-4xl font-mono font-bold text-amber-400 mt-2">{metrics.gaming_total}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
          <h3 className="text-xl font-semibold mb-6">Throughput (TPS)</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }} />
                <Line type="monotone" dataKey="tps" stroke="#34d399" strokeWidth={3} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
          <h3 className="text-xl font-semibold mb-6">Latency (ms)</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }} />
                <Line type="monotone" dataKey="latency" stroke="#60a5fa" strokeWidth={3} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
