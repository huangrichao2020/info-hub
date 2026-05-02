import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Radar, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
} from 'chart.js';
import { Target, AlertTriangle, TrendingUp, TrendingDown, Minus, RefreshCw } from 'lucide-react';

ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement
);

interface Perspective {
  name: string;
  verdict: string;
  confidence: number;
  reasoning: string;
  signals: string[];
  risks: string[];
}

interface CrossValidationResult {
  timestamp: string;
  consensus: string;
  consensus_strength: number;
  final_verdict: string;
  action_plan: string;
  disagreements: any[];
  perspectives: Perspective[];
}

const verdictColors: Record<string, string> = {
  '看多': '#10b981',
  '看空': '#ef4444',
  '中性': '#6b7280',
  '结构性机会': '#f59e0b',
};

const verdictIcons: Record<string, React.ReactNode> = {
  '看多': <TrendingUp className="w-5 h-5 text-emerald-500" />,
  '看空': <TrendingDown className="w-5 h-5 text-red-500" />,
  '中性': <Minus className="w-5 h-5 text-gray-500" />,
  '结构性机会': <Target className="w-5 h-5 text-amber-500" />,
};

export default function CrossValidationPanel() {
  const [data, setData] = useState<CrossValidationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/stock/cross-validation');
      if (!res.ok) throw new Error('获取数据失败');
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : '未知错误');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const radarData = {
    labels: data?.perspectives.map(p => p.name) || [],
    datasets: [
      {
        label: '置信度',
        data: data?.perspectives.map(p => p.confidence * 100) || [],
        backgroundColor: 'rgba(99, 102, 241, 0.2)',
        borderColor: 'rgba(99, 102, 241, 1)',
        borderWidth: 2,
        pointBackgroundColor: data?.perspectives.map(p => verdictColors[p.verdict]) || [],
      },
    ],
  };

  const barData = {
    labels: data?.perspectives.map(p => p.name) || [],
    datasets: [
      {
        label: '看多',
        data: data?.perspectives.map(p => p.verdict === '看多' ? p.confidence * 100 : 0) || [],
        backgroundColor: '#10b981',
      },
      {
        label: '看空',
        data: data?.perspectives.map(p => p.verdict === '看空' ? p.confidence * 100 : 0) || [],
        backgroundColor: '#ef4444',
      },
      {
        label: '中性',
        data: data?.perspectives.map(p => p.verdict === '中性' ? p.confidence * 100 : 0) || [],
        backgroundColor: '#6b7280',
      },
      {
        label: '结构性机会',
        data: data?.perspectives.map(p => p.verdict === '结构性机会' ? p.confidence * 100 : 0) || [],
        backgroundColor: '#f59e0b',
      },
    ],
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
        <p className="text-red-600">{error}</p>
        <button onClick={fetchData} className="mt-2 text-indigo-600 hover:underline">
          重试
        </button>
      </div>
    );
  }

  if (!data) return null;

  const strengthPercent = Math.round(data.consensus_strength * 100);
  const strengthColor = strengthPercent >= 80 ? 'emerald' : strengthPercent >= 60 ? 'amber' : 'red';

  return (
    <div className="space-y-6">
      {/* 顶部摘要卡片 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl p-6 text-white"
      >
        <div className="flex justify-between items-start">
          <div>
            <p className="text-indigo-100 text-sm">最终结论</p>
            <h2 className="text-2xl font-bold mt-1">{data.final_verdict}</h2>
            <p className="text-indigo-100 mt-2">{data.action_plan}</p>
          </div>
          <button
            onClick={fetchData}
            className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
        <div className="mt-4 flex gap-4 text-sm">
          <div>
            <span className="text-indigo-200">共识强度</span>
            <p className="text-xl font-bold">{strengthPercent}%</p>
          </div>
          <div>
            <span className="text-indigo-200">更新时间</span>
            <p className="text-xl font-bold">{data.timestamp}</p>
          </div>
        </div>
      </motion.div>

      {/* 图表区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 雷达图 */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-gray-100"
        >
          <h3 className="text-lg font-semibold mb-4">五视角置信度雷达</h3>
          <Radar
            data={radarData}
            options={{
              scales: {
                r: {
                  beginAtZero: true,
                  max: 100,
                  ticks: { stepSize: 20 },
                },
              },
              plugins: {
                legend: { display: false },
              },
            }}
          />
        </motion.div>

        {/* 柱状图 */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-xl p-6 shadow-sm border border-gray-100"
        >
          <h3 className="text-lg font-semibold mb-4">视角分布</h3>
          <Bar
            data={barData}
            options={{
              scales: {
                x: { stacked: true },
                y: { stacked: true, beginAtZero: true, max: 100 },
              },
              plugins: {
                legend: { position: 'bottom' },
              },
            }}
          />
        </motion.div>
      </div>

      {/* 各视角详情 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.perspectives.map((p, i) => (
          <motion.div
            key={p.name}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * i }}
            className="bg-white rounded-xl p-5 shadow-sm border border-gray-100"
          >
            <div className="flex items-center gap-2 mb-3">
              {verdictIcons[p.verdict]}
              <h4 className="font-semibold">{p.name}</h4>
              <span
                className="ml-auto px-2 py-0.5 rounded text-xs font-medium"
                style={{
                  backgroundColor: `${verdictColors[p.verdict]}20`,
                  color: verdictColors[p.verdict],
                }}
              >
                {p.verdict}
              </span>
            </div>
            <p className="text-sm text-gray-600 mb-3">{p.reasoning}</p>
            {p.signals.length > 0 && (
              <div className="mb-2">
                <p className="text-xs text-emerald-600 font-medium">✅ 信号</p>
                <ul className="text-xs text-gray-500 mt-1 space-y-1">
                  {p.signals.map((s, j) => <li key={j}>• {s}</li>)}
                </ul>
              </div>
            )}
            {p.risks.length > 0 && (
              <div>
                <p className="text-xs text-red-600 font-medium flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> 风险
                </p>
                <ul className="text-xs text-gray-500 mt-1 space-y-1">
                  {p.risks.map((r, j) => <li key={j}>• {r}</li>)}
                </ul>
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* 分歧点 */}
      {data.disagreements.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-amber-50 border border-amber-200 rounded-xl p-5"
        >
          <h4 className="font-semibold text-amber-800 mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            分歧点 ({data.disagreements.length})
          </h4>
          <ul className="space-y-2">
            {data.disagreements.map((d, i) => (
              <li key={i} className="text-sm text-amber-700">
                <span className="font-medium">{d.perspective}</span>：
                {d.reasoning}
              </li>
            ))}
          </ul>
        </motion.div>
      )}
    </div>
  );
}
