import axios from 'axios'

export const api = axios.create({ baseURL: '/' })

const withCoords = (path, coords) => {
  const params = new URLSearchParams()
  if (coords?.lat != null && coords?.lon != null) {
    params.set('lat', coords.lat)
    params.set('lon', coords.lon)
  }
  const query = params.toString()
  return query ? `${path}?${query}` : path
}

export const getWeather = (coords) => api.get(withCoords('/api/weather', coords)).then((res) => res.data)
export const getFoods = (page = 1, pageSize = 15) =>
  api.get('/api/food', { params: { page, page_size: pageSize } }).then((res) => res.data)
export const createFood = (payload) => api.post('/api/food', payload).then((res) => res.data)
export const updateFood = (id, payload) => api.put(`/api/food/${id}`, payload).then((res) => res.data)
export const deleteFood = (id) => api.delete(`/api/food/${id}`).then((res) => res.data)
export const getHistory = (page = 1, pageSize = 10) =>
  api.get('/api/history', { params: { page, page_size: pageSize } }).then((res) => res.data)
export const setFinalChoice = (id, finalChoice) =>
  api.patch(`/api/history/${id}/choice`, { final_choice: finalChoice }).then((res) => res.data)
export const deleteHistory = (id) => api.delete(`/api/history/${id}`).then((res) => res.data)
export const getChoiceStats = () => api.get('/api/stats/choices').then((res) => res.data)
export const getPriceStats = () => api.get('/api/stats/price').then((res) => res.data)

export function startSelection(onChunk, onDone, onError, coords, preference) {
  const controller = new AbortController()
  const body = {}
  const trimmed = preference?.trim()
  if (trimmed) body.today_preference = trimmed

  ;(async () => {
    try {
      const response = await fetch(withCoords('/api/select', coords), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      if (!response.ok || !response.body) {
        throw new Error(`请求失败：${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          const trimmedLine = line.trim()
          if (!trimmedLine.startsWith('data:')) continue
          const raw = trimmedLine.slice(5).trim()
          if (!raw) continue
          const data = JSON.parse(raw)
          if (data.type === 'done') {
            onDone?.(data)
          } else if (data.type === 'error') {
            onError?.(new Error(data.message || '推荐失败'))
          } else if (data.content) {
            onChunk?.(data.content)
          }
        }
      }
    } catch (error) {
      if (error.name !== 'AbortError') onError?.(error)
    }
  })()

  return () => controller.abort()
}
