import React, { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

function App() {
  const [data, setData] = useState([]);
  const [metrics, setMetrics] = useState({ tps: 0, latency_ms: 0, tx_total: 0, gaming_total: 0 });
  
  const [unlockedPosts, setUnlockedPosts] = useState({});
  const [isPaying, setIsPaying] = useState({});
  const [manualTxCount, setManualTxCount] = useState(0);

  const handleUnlock = async (id) => {
    setIsPaying(prev => ({ ...prev, [id]: true }));
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/pay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'demo_user', action: 'unlock_post' })
      });
      if (res.ok) {
        setUnlockedPosts(prev => ({ ...prev, [id]: true }));
        setManualTxCount(prev => prev + 1);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsPaying(prev => ({ ...prev, [id]: false }));
    }
  };

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
        // 240 seconds = 4 minutes of history on the chart
        if (newData.length > 240) newData.shift();
        return newData;
      });
    };

    return () => ws.close();
  }, []);

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 0 },
    scales: {
      x: { grid: { color: 'rgba(0, 0, 0, 0.05)' }, ticks: { color: '#64748b', maxTicksLimit: 10 } },
      y: { grid: { color: 'rgba(0, 0, 0, 0.05)' }, ticks: { color: '#64748b' }, beginAtZero: true }
    },
    plugins: {
      legend: { display: false },
      tooltip: { 
        backgroundColor: 'rgba(255, 255, 255, 0.95)', 
        titleColor: '#0f172a',
        bodyColor: '#0f172a',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        padding: 12, 
        cornerRadius: 8,
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
      }
    }
  };

  const tpsChartData = {
    labels: data.map(d => d.time),
    datasets: [{
      label: 'Throughput (TPS)',
      data: data.map(d => d.tps),
      borderColor: '#10b981', // emerald-500
      backgroundColor: 'rgba(16, 185, 129, 0.1)',
      borderWidth: 2,
      tension: 0.4,
      fill: true,
      pointRadius: 0,
      pointHoverRadius: 6
    }]
  };

  const latencyChartData = {
    labels: data.map(d => d.time),
    datasets: [{
      label: 'Latency (ms)',
      data: data.map(d => d.latency),
      borderColor: '#3b82f6', // blue-500
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      borderWidth: 2,
      tension: 0.4,
      fill: true,
      pointRadius: 0,
      pointHoverRadius: 6
    }]
  };

  const postsData = [
    {
      id: 1,
      author: "Elena Rossi",
      handle: "@erossi_art",
      avatarInitials: "ER",
      lockedText: "🔒 Exclusive: Download the full 4K resolution files for my latest digital painting set, including the layered source PSDs.",
      unlockedText: "🔓 Thanks for supporting my art! Here is the secure link to the 4K files: bit.ly/rossi-exclusive-4k"
    },
    {
      id: 2,
      author: "Marcus Chen",
      handle: "@marcus_dev",
      avatarInitials: "MC",
      lockedText: "🔒 I finally finished the technical deep-dive on bypassing the new compiler limitations. Unlocking gets you the full 20-page PDF.",
      unlockedText: "🔓 Appreciate the support! The PDF guide is attached below. Make sure to read page 12 for the exact compiler workaround."
    },
    {
      id: 3,
      author: "Sarah Jenkins",
      handle: "@s_jenkins_photo",
      avatarInitials: "SJ",
      lockedText: "🔒 Behind the scenes footage from today's volcano shoot in Iceland. Plus my Lightroom preset pack for these exact colors!",
      unlockedText: "🔓 You rock! The raw video files and Lightroom `.xmp` presets are ready for download below. Enjoy editing!"
    }
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-8 font-sans selection:bg-blue-200">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header Removed as requested */}

        {/* Top Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow duration-300">
            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
              <svg className="w-12 h-12 text-emerald-600" fill="currentColor" viewBox="0 0 24 24"><path d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
            </div>
            <h3 className="text-slate-500 text-xs uppercase tracking-[0.2em] font-bold">Live TPS</h3>
            <p className="text-5xl font-mono font-black text-emerald-600 mt-3">{metrics.tps.toFixed(1)}</p>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow duration-300">
            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity duration-500">
              <svg className="w-12 h-12 text-blue-600" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2v20M17 5l-5-3-5 3v13l5 3 5-3V5z"/></svg>
            </div>
            <h3 className="text-slate-500 text-xs uppercase tracking-[0.2em] font-bold">Avg Latency</h3>
            <p className="text-5xl font-mono font-black text-blue-600 mt-3">{metrics.latency_ms.toFixed(1)} <span className="text-2xl font-sans text-slate-400">ms</span></p>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow duration-300">
            <h3 className="text-slate-500 text-xs uppercase tracking-[0.2em] font-bold">Total Micro-Txs</h3>
            <p className="text-5xl font-mono font-black text-purple-600 mt-3">{metrics.tx_total.toLocaleString()}</p>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm relative overflow-hidden group hover:shadow-md transition-shadow duration-300">
            <h3 className="text-slate-500 text-xs uppercase tracking-[0.2em] font-bold">Gaming Events</h3>
            <p className="text-5xl font-mono font-black text-amber-500 mt-3">{metrics.gaming_total.toLocaleString()}</p>
          </div>
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col">
            <h3 className="text-xl font-bold mb-6 flex items-center space-x-2 text-slate-800">
              <span className="w-3 h-3 rounded-full bg-emerald-500 shadow-sm"></span>
              <span>Throughput (TPS) - Last 4 Minutes</span>
            </h3>
            <div className="flex-grow h-80 relative w-full">
              <Line options={commonOptions} data={tpsChartData} />
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col">
            <h3 className="text-xl font-bold mb-6 flex items-center space-x-2 text-slate-800">
              <span className="w-3 h-3 rounded-full bg-blue-500 shadow-sm"></span>
              <span>Latency (ms) - Last 4 Minutes</span>
            </h3>
            <div className="flex-grow h-80 relative w-full">
              <Line options={commonOptions} data={latencyChartData} />
            </div>
          </div>
        </div>

        {/* Microblogging Demo Section */}
        <div className="mt-8 bg-white rounded-2xl p-8 border border-slate-200 shadow-sm">
          <div className="mb-8 border-b border-slate-100 pb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h3 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center space-x-3">
                <svg className="w-6 h-6 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9.5a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" /></svg>
                <span>Live Microblogging Demo</span>
              </h3>
              <p className="text-slate-500 mt-2 text-lg">Clicking "Unlock" triggers a real-time $0.01 microtransaction via the Hydra API.</p>
            </div>
            <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4 px-6 text-center shadow-inner">
              <p className="text-xs font-bold text-indigo-500 uppercase tracking-widest mb-1">Manual dApp Txs</p>
              <p className="text-4xl font-black text-indigo-700">{manualTxCount}</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {postsData.map((post) => (
              <div key={post.id} className="bg-slate-50 p-6 rounded-2xl border border-slate-200 flex flex-col justify-between hover:shadow-md hover:border-indigo-200 transition-all duration-300">
                <div>
                  <div className="flex items-center space-x-4 mb-5">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white font-bold text-xl shadow-inner">
                      {post.avatarInitials}
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-900">{post.author}</h4>
                      <p className="text-xs text-slate-500 font-mono">{post.handle}</p>
                    </div>
                  </div>
                  <div className={`p-4 rounded-xl border ${unlockedPosts[post.id] ? 'bg-emerald-50 border-emerald-200' : 'bg-white border-slate-200'} mb-6 min-h-[120px] flex items-center shadow-sm`}>
                    <p className={`text-sm leading-relaxed font-medium ${unlockedPosts[post.id] ? 'text-emerald-800' : 'text-slate-600'}`}>
                      {unlockedPosts[post.id] ? post.unlockedText : post.lockedText}
                    </p>
                  </div>
                </div>
                <button 
                  onClick={() => handleUnlock(post.id)}
                  disabled={unlockedPosts[post.id] || isPaying[post.id]}
                  className={`w-full py-3 rounded-xl font-bold tracking-wide transition-all duration-300 shadow-sm ${
                    unlockedPosts[post.id] 
                      ? 'bg-emerald-100 text-emerald-700 border border-emerald-200 cursor-default shadow-none' 
                      : 'bg-indigo-600 hover:bg-indigo-700 text-white transform active:scale-95'
                  }`}
                >
                  {isPaying[post.id] ? (
                    <span className="flex items-center justify-center space-x-2">
                      <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                      <span>Processing...</span>
                    </span>
                  ) : (unlockedPosts[post.id] ? "Unlocked!" : "Unlock for $0.01")}
                </button>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}

export default App;
