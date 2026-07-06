import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getChoiceStats, getPriceStats } from '../api.js'

const COLORS = ['#eb6834', '#2a78d6', '#1baf7a', '#eda100', '#008300', '#4a3aa7', '#e34948', '#e87ba4']
const rankMedal = ['🥇', '🥈', '🥉']

function percentLabel({ percent }) {
  if (percent < 0.04) return ''
  return `${Math.round(percent * 100)}%`
}

function StatsPage() {
  const [choiceStats, setChoiceStats] = useState([])
  const [priceStats, setPriceStats] = useState({ avg_price: 0, distribution: [] })
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([getChoiceStats(), getPriceStats()])
      .then(([choices, prices]) => {
        setChoiceStats(choices)
        setPriceStats(prices)
      })
      .catch((err) => setError(err.response?.data?.detail || '加载统计失败'))
  }, [])

  const totalChoices = useMemo(() => choiceStats.reduce((sum, item) => sum + item.count, 0), [choiceStats])

  return (
    <section className="page-card stats-page viz-root">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Analytics</p>
          <h2>统计</h2>
          <p>看看最近都吃了什么，以及大概花了多少钱。</p>
        </div>
        <div className="avg-price-card">
          <span>平均消费</span>
          <strong>¥{priceStats.avg_price || 0}</strong>
        </div>
      </div>

      {error && <div className="error-box compact">{error}</div>}

      <div className="stats-grid">
        <article className="chart-card">
          <div className="chart-heading">
            <h3>选择次数分布</h3>
            <span>{totalChoices} 次确认</span>
          </div>
          {choiceStats.length ? (
            <ResponsiveContainer width="100%" height={320}>
              <PieChart>
                <Pie
                  data={choiceStats}
                  dataKey="count"
                  nameKey="name"
                  innerRadius={68}
                  outerRadius={120}
                  paddingAngle={2}
                  label={percentLabel}
                  labelLine={false}
                >
                  {choiceStats.map((entry, index) => (
                    <Cell key={entry.name} fill={COLORS[index % COLORS.length]} stroke="#fffaf7" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [`${value} 次`, name]} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">确认选择后会显示分布。</div>
          )}
        </article>

        <article className="chart-card">
          <div className="chart-heading">
            <h3>价格区间分布</h3>
            <span>按最终选择聚合</span>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={priceStats.distribution} margin={{ top: 16, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid vertical={false} stroke="#f1dfd5" />
              <XAxis dataKey="range" tickLine={false} axisLine={false} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
              <Tooltip formatter={(value) => [`${value} 次`, '数量']} />
              <Bar dataKey="count" name="数量" fill="#eb6834" radius={[8, 8, 0, 0]} maxBarSize={52} />
            </BarChart>
          </ResponsiveContainer>
        </article>
      </div>

      <article className="ranking-card">
        <div className="chart-heading">
          <h3>排行榜</h3>
          <span>食物名 · 次数 · 占比</span>
        </div>
        {choiceStats.length ? (
          <div className="ranking-table">
            {choiceStats.map((item, index) => {
              const percentage = totalChoices ? Math.round((item.count / totalChoices) * 100) : 0
              return (
                <div className="ranking-row" key={item.name}>
                  <span className="rank-index">{rankMedal[index] || index + 1}</span>
                  <span className="series-dot" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                  <strong>{item.name}</strong>
                  <span>{item.count} 次</span>
                  <div className="progress-track" aria-label={`${item.name} 占比 ${percentage}%`}>
                    <div className="progress-fill" style={{ width: `${percentage}%` }} />
                  </div>
                  <span className="percent-text">{percentage}%</span>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="empty-state">暂无排行数据。</div>
        )}
      </article>
    </section>
  )
}

export default StatsPage
