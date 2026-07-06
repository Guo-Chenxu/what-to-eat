import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import TodayPage from './pages/TodayPage.jsx'
import { getWeather } from './api.js'

const FoodManager = lazy(() => import('./pages/FoodManager.jsx'))
const HistoryPage = lazy(() => import('./pages/HistoryPage.jsx'))
const StatsPage = lazy(() => import('./pages/StatsPage.jsx'))

const TABS = [
  { key: 'today', label: '今天吃什么', icon: '🎲' },
  { key: 'foods', label: '美食库', icon: '🍱' },
  { key: 'history', label: '历史', icon: '📜' },
  { key: 'stats', label: '统计', icon: '📊' },
]

const normalizeHash = () => {
  const key = window.location.hash.replace('#', '') || 'today'
  return TABS.some((tab) => tab.key === key) ? key : 'today'
}

function App() {
  const [activeTab, setActiveTab] = useState(normalizeHash)
  const [coords, setCoords] = useState(null)
  const [weather, setWeather] = useState(null)

  useEffect(() => {
    const syncHash = () => setActiveTab(normalizeHash())
    window.addEventListener('hashchange', syncHash)
    window.addEventListener('popstate', syncHash)
    if (!window.location.hash) window.location.hash = '#today'
    return () => {
      window.removeEventListener('hashchange', syncHash)
      window.removeEventListener('popstate', syncHash)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const loadWeather = async (nextCoords) => {
      try {
        const data = await getWeather(nextCoords)
        if (!cancelled) setWeather(data)
      } catch {
        if (!cancelled) {
          setWeather({ location: '未知位置', description: '无法获取天气', temp: '--' })
        }
      }
    }

    if (!navigator.geolocation) {
      loadWeather(null)
      return () => {
        cancelled = true
      }
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const nextCoords = {
          lat: position.coords.latitude,
          lon: position.coords.longitude,
        }
        if (!cancelled) setCoords(nextCoords)
        loadWeather(nextCoords)
      },
      () => loadWeather(null),
      { enableHighAccuracy: false, timeout: 5000, maximumAge: 10 * 60 * 1000 },
    )

    return () => {
      cancelled = true
    }
  }, [])

  const content = useMemo(() => {
    if (activeTab === 'today') return <TodayPage coords={coords} />
    if (activeTab === 'foods') return <FoodManager />
    if (activeTab === 'history') return <HistoryPage />
    return <StatsPage />
  }, [activeTab, coords])

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-row">
          <div>
            <p className="eyebrow">Personal meal picker</p>
            <h1>今天吃什么</h1>
          </div>
          <div className="weather-pill" title="天气信息">
            <span>📍 {weather?.location || '定位中'}</span>
            <span>·</span>
            <span>{weather?.description || '天气加载中'}</span>
            <span>·</span>
            <strong>{weather?.temp || '--'}</strong>
          </div>
        </div>
        <nav className="tabs" aria-label="主导航">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              className={activeTab === tab.key ? 'tab active' : 'tab'}
              type="button"
              onClick={() => {
                window.location.hash = `#${tab.key}`
                setActiveTab(tab.key)
              }}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="app-main">
        <Suspense fallback={<div className="loading-page">加载中...</div>}>{content}</Suspense>
      </main>
    </div>
  )
}

export default App
