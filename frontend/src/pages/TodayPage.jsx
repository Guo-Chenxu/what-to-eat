import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { setFinalChoice, startSelection } from '../api.js'

function TodayPage({ coords }) {
  const [status, setStatus] = useState('idle')
  const [streamText, setStreamText] = useState('')
  const [recommendations, setRecommendations] = useState(null)
  const [chosenFood, setChosenFood] = useState('')
  const [preference, setPreference] = useState('')
  const [error, setError] = useState('')
  const cancelRef = useRef(null)

  useEffect(() => {
    return () => {
      cancelRef.current?.()
    }
  }, [])

  const handleStart = () => {
    cancelRef.current?.()
    setStatus('loading')
    setStreamText('')
    setRecommendations(null)
    setChosenFood('')
    setError('')

    cancelRef.current = startSelection(
      (chunk) => setStreamText((prev) => prev + chunk),
      (done) => {
        setRecommendations({ id: done.id, food_1: done.food_1, food_2: done.food_2 })
        setStatus('done')
        cancelRef.current = null
      },
      (err) => {
        setError(err.message || '推荐失败，请稍后再试')
        setStatus('error')
        cancelRef.current = null
      },
      coords,
      preference,
    )
  }

  const handleChoose = async (food) => {
    if (!recommendations?.id || chosenFood) return
    const previous = chosenFood
    setChosenFood(food)
    try {
      await setFinalChoice(recommendations.id, food)
    } catch (err) {
      setChosenFood(previous)
      setError(err.response?.data?.detail || '确认选择失败')
    }
  }

  const loadingWithoutText = status === 'loading' && !streamText
  const hasStream = Boolean(streamText)

  return (
    <section className="today-page page-card">
      <div className="hero-copy">
        <p className="eyebrow">AI meal recommendation</p>
        <h2>让 AI 结合天气、时间和你的习惯来选</h2>
        <p>维护你的美食库，点击按钮后获得两项候选，再确认最终吃了什么。</p>
      </div>

      <div className="selection-panel">
        <input
          className="preference-input"
          maxLength={100}
          disabled={status === 'loading'}
          value={preference}
          placeholder="今日偏好（选填）：想吃清淡的？辣的？不想动脑点外卖？"
          onChange={(event) => setPreference(event.target.value)}
        />
        <button className="big-orange-button" type="button" disabled={status === 'loading'} onClick={handleStart}>
          {status === 'loading' ? '🤔 思考中...' : '🎲 今天吃什么？'}
        </button>
      </div>

      {loadingWithoutText && (
        <div className="thinking-box">
          <span className="box-label">AI 正在思考</span>
          <div className="dots" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        </div>
      )}

      {hasStream && (
        <div className={status === 'loading' ? 'stream-box streaming' : 'stream-box'}>
          <span className="box-label">✦ {status === 'loading' ? 'AI 分析中' : 'AI 分析'}</span>
          <ReactMarkdown>{streamText}</ReactMarkdown>
          {status === 'loading' && <span className="cursor" aria-hidden="true" />}
        </div>
      )}

      {status === 'done' && recommendations && (
        <div className="recommendation-section">
          <h2>{chosenFood ? '✅ 今天吃这个' : '今天推荐吃'}</h2>
          <div className="recommendation-grid">
            {[recommendations.food_1, recommendations.food_2].map((food, index) => {
              const selected = chosenFood === food
              const dimmed = chosenFood && !selected
              return (
                <article
                  className={`recommendation-card ${selected ? 'selected' : ''} ${dimmed ? 'dimmed' : ''}`}
                  key={`${food}-${index}`}
                  style={{ animationDelay: `${index * 0.15}s` }}
                >
                  <div className="food-icon">{selected ? '✅' : index === 0 ? '🥢' : '🍴'}</div>
                  <h3>{food}</h3>
                  {selected && <span className="confirmed-tag">已确认</span>}
                  {!chosenFood && (
                    <button type="button" className="choose-button" onClick={() => handleChoose(food)}>
                      选这个
                    </button>
                  )}
                </article>
              )
            })}
          </div>
          {!chosenFood && <p className="hint-text">点击确认你最终的选择，下次推荐将参考此记录</p>}
        </div>
      )}

      {status === 'error' && <div className="error-box">{error}</div>}
    </section>
  )
}

export default TodayPage
