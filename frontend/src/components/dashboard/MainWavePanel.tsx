import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, ArrowUpRight, ArrowDownRight, BarChart3, RefreshCw } from 'lucide-react'
import apiClient from '../../api/client'

interface ScanResult {
  symbol: string
  close_change_pct?: number
  volume_ratio?: number
  ma25?: number
  signal?: string
}

export default function MainWavePanel() {
  const [volumeUp, setVolumeUp] = useState<ScanResult[]>([])
  const [ma25Up, setMa25Up] = useState<ScanResult[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [volRes, maRes] = await Promise.all([
        apiClient.get('/stock/scan/volume-up'),
        apiClient.get('/stock/scan/ma25-up'),
      ])
      setVolumeUp((volRes.data.stocks || []).slice(0, 20))
      setMa25Up((maRes.data.stocks || []).slice(0, 20))
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  // 找出同时出现在两个列表中的（放量+趋势共振）
  const maSymbols = new Set(ma25Up.map(s => s.symbol))
  const resonant = volumeUp.filter(s => maSymbols.has(s.symbol))

  return (
    <div className="space-y-6">
      {/* 顶部摘要 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-r from-emerald-600 to-teal-600 rounded-xl p-6 text-white"
      >
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <TrendingUp className="w-6 h-6" />
              主升浪机会
            </h2>
            <p className="text-emerald-100 mt-1">放量上涨 + MA25 趋势向上的共振标的</p>
          </div>
          <button onClick={fetchData} className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition">
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
        <div className="mt-4 flex gap-6 text-sm">
          <div>
            <span className="text-emerald-200">放量上涨</span>
            <p className="text-2xl font-bold">{volumeUp.length} <span className="text-base font-normal">只</span></p>
          </div>
          <div>
            <span className="text-emerald-200">趋势向上</span>
            <p className="text-2xl font-bold">{ma25Up.length} <span className="text-base font-normal">只</span></p>
          </div>
          <div>
            <span className="text-emerald-200">量价共振</span>
            <p className="text-2xl font-bold">{resonant.length} <span className="text-base font-normal">只</span></p>
          </div>
        </div>
      </motion.div>

      {/* 共振机会（优先展示） */}
      {resonant.length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-white rounded-xl shadow-sm border border-emerald-100">
          <div className="px-5 py-3 border-b border-emerald-100 bg-emerald-50 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-emerald-600" />
            <h3 className="font-semibold text-emerald-800">量价共振（放量上涨 + 趋势向上）— 优先关注</h3>
          </div>
          <div className="divide-y">
            {resonant.map((s, i) => (
              <div key={i} className="px-5 py-3 flex items-center justify-between hover:bg-gray-50">
                <div className="flex items-center gap-3">
                  <span className="font-mono font-semibold text-sm bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded">{s.symbol}</span>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <span className="flex items-center gap-1 text-red-600">
                    <ArrowUpRight className="w-3 h-3" /> {s.close_change_pct?.toFixed(2)}%
                  </span>
                  <span className="text-emerald-600">量比 {s.volume_ratio?.toFixed(2)}x</span>
                  <span className="px-2 py-0.5 rounded text-xs bg-emerald-100 text-emerald-700 font-medium">共振</span>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* 放量上涨列表 */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
          <ArrowUpRight className="w-4 h-4 text-orange-500" />
          <h3 className="font-semibold">放量上涨（量比 ≥ 1.5）</h3>
        </div>
        {volumeUp.length === 0 ? (
          <div className="px-5 py-8 text-center text-gray-400 text-sm">{loading ? '加载中...' : '暂无数据'}</div>
        ) : (
          <div className="divide-y">
            {volumeUp.slice(0, 10).map((s, i) => (
              <div key={i} className="px-5 py-3 flex items-center justify-between hover:bg-gray-50">
                <span className="font-mono font-semibold text-sm">{s.symbol}</span>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-red-600">{s.close_change_pct?.toFixed(2)}%</span>
                  <span className="text-gray-500">量比 {s.volume_ratio?.toFixed(2)}x</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </motion.div>

      {/* 趋势向上列表 */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-blue-500" />
          <h3 className="font-semibold">趋势向上（MA25 拐头）</h3>
        </div>
        {ma25Up.length === 0 ? (
          <div className="px-5 py-8 text-center text-gray-400 text-sm">{loading ? '加载中...' : '暂无数据'}</div>
        ) : (
          <div className="divide-y">
            {ma25Up.slice(0, 10).map((s, i) => (
              <div key={i} className="px-5 py-3 flex items-center justify-between hover:bg-gray-50">
                <span className="font-mono font-semibold text-sm">{s.symbol}</span>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-gray-500">MA25 {s.ma25}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </motion.div>

      {/* 操作提示 */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800"
      >
        <strong>操作提醒：</strong>共振标的优先观察，但需结合板块逻辑和大盘状态。
        试仓 20%，确认趋势后再加码。量价共振是必要条件，不是充分条件。
      </motion.div>
    </div>
  )
}
