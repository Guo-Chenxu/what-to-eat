import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { deleteHistory, getHistory, setFinalChoice } from '../api.js'

const PAGE_SIZE = 10
const slotIcon = { 午餐: '☀️', 晚餐: '🌅', 夜宵: '🌙' }

function HistoryPage() {
  const [items, setItems] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState({})
  const [localChoices, setLocalChoices] = useState({})
  const [selecting, setSelecting] = useState(false)
  const [selectedIds, setSelectedIds] = useState([])
  const [deleting, setDeleting] = useState(false)
  const listTopRef = useRef(null)

  const loadHistory = async (targetPage = page) => {
    setLoading(true)
    setError('')
    try {
      const data = await getHistory(targetPage, PAGE_SIZE)
      if (data.items.length === 0 && targetPage > 1 && data.total > 0) {
        setPage(Math.ceil(data.total / PAGE_SIZE))
        return
      }
      setItems(data.items)
      setTotalPages(data.total_pages)
    } catch (err) {
      setError(err.response?.data?.detail || '加载历史失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setExpanded({})
    setLocalChoices({})
    setSelectedIds([])
    setSelecting(false)
    listTopRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    loadHistory(page)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  const choiceOf = (item) => localChoices[item.id] ?? item.final_choice

  const chooseFood = async (item, food) => {
    const previous = localChoices[item.id]
    setLocalChoices((prev) => ({ ...prev, [item.id]: food }))
    try {
      await setFinalChoice(item.id, food)
    } catch (err) {
      setLocalChoices((prev) => {
        const next = { ...prev }
        if (previous === undefined) delete next[item.id]
        else next[item.id] = previous
        return next
      })
      setError(err.response?.data?.detail || '确认选择失败')
    }
  }

  const removeItem = async (id) => {
    if (!window.confirm('确定删除这条历史吗？')) return
    const previousItems = items
    setItems((prev) => prev.filter((item) => item.id !== id))
    try {
      await deleteHistory(id)
      await loadHistory(page)
    } catch (err) {
      setItems(previousItems)
      setError(err.response?.data?.detail || '删除失败')
    }
  }

  const batchDelete = async () => {
    if (!selectedIds.length || !window.confirm(`确定删除选中的 ${selectedIds.length} 条历史吗？`)) return
    const ids = [...selectedIds]
    setDeleting(true)
    setItems((prev) => prev.filter((item) => !ids.includes(item.id)))
    setSelectedIds([])
    let failed = 0
    for (const id of ids) {
      try {
        await deleteHistory(id)
      } catch {
        failed += 1
      }
    }
    setDeleting(false)
    setSelecting(false)
    if (failed) window.alert(`有 ${failed} 条删除失败，请刷新页面查看未成功删除的记录。`)
    await loadHistory(page)
  }

  const toggleSelected = (id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]))
  }

  return (
    <section className="page-card history-page" ref={listTopRef}>
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Meal history</p>
          <h2>历史记录</h2>
          <p>确认后的选择会进入统计，也会影响之后的推荐。</p>
        </div>
        <div className="history-toolbar">
          {selecting && (
            <button type="button" className="danger-small" disabled={!selectedIds.length || deleting} onClick={batchDelete}>
              删除选中（{selectedIds.length}）
            </button>
          )}
          <button type="button" className="ghost-small" disabled={deleting} onClick={() => setSelecting((prev) => !prev)}>
            {selecting ? '取消选择' : '选择'}
          </button>
        </div>
      </div>

      {error && <div className="error-box compact">{error}</div>}
      {loading && <div className="loading-page">加载中...</div>}

      <div className="timeline">
        {items.map((item) => {
          const chosen = choiceOf(item)
          const foods = [item.food_1, item.food_2]
          return (
            <article className="timeline-item" key={item.id}>
              <div className="timeline-dot" />
              {selecting && (
                <input
                  className="timeline-checkbox"
                  type="checkbox"
                  checked={selectedIds.includes(item.id)}
                  onChange={() => toggleSelected(item.id)}
                />
              )}
              <button
                type="button"
                className="history-delete"
                disabled={deleting}
                title="删除"
                onClick={() => removeItem(item.id)}
              >
                🗑
              </button>
              <div className="history-meta">
                <strong>{item.date}</strong>
                <span>
                  {slotIcon[item.slot_name] || '🍽'} {item.slot_name}
                </span>
                {item.location && <span>📍{item.location}</span>}
                {item.weather && <span>🌤{item.weather}</span>}
              </div>
              <div className="food-chips">
                {foods.map((food) => {
                  const isChosen = chosen === food
                  const isDim = chosen && !isChosen
                  return (
                    <span className={`food-chip ${isChosen ? 'chosen' : ''} ${isDim ? 'dim' : ''}`} key={food}>
                      {isChosen && '✅ '}
                      {food}
                      {!chosen && (
                        <button type="button" onClick={() => chooseFood(item, food)} aria-label={`选择 ${food}`}>
                          ✓
                        </button>
                      )}
                    </span>
                  )
                })}
              </div>
              {item.today_preference && <p className="preference-note">偏好：{item.today_preference}</p>}
              <button
                type="button"
                className="analysis-toggle"
                onClick={() => setExpanded((prev) => ({ ...prev, [item.id]: !prev[item.id] }))}
              >
                {expanded[item.id] ? '▲ 收起AI分析' : '▼ 查看AI分析'}
              </button>
              {expanded[item.id] && (
                <div className="history-reasoning">
                  <ReactMarkdown>{item.reasoning || '暂无分析内容'}</ReactMarkdown>
                </div>
              )}
            </article>
          )
        })}
        {!items.length && !loading && <div className="empty-state">暂无历史记录。</div>}
      </div>

      <div className="pagination">
        <button type="button" disabled={page <= 1} onClick={() => setPage((prev) => Math.max(prev - 1, 1))}>
          上一页
        </button>
        <span>
          第 {page} / {totalPages || 1} 页
        </span>
        <button
          type="button"
          disabled={!totalPages || page >= totalPages}
          onClick={() => setPage((prev) => prev + 1)}
        >
          下一页
        </button>
      </div>
    </section>
  )
}

export default HistoryPage
