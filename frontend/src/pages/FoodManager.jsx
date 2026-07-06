import { useEffect, useState } from 'react'
import { createFood, deleteFood, getFoods, updateFood } from '../api.js'

const SERVICE_TYPES = ['外卖', '到店<100m', '到店<500m', '到店<1km', '到店<2km']
const PAGE_SIZE = 15
const emptyForm = { name: '', type: '', characteristics: '', service_type: '到店<500m', avg_price: 30 }

const errorDetail = (error, fallback) => error.response?.data?.detail || fallback

function FoodForm({ value, onChange, onSubmit, onCancel, submitText }) {
  const update = (field, nextValue) => onChange({ ...value, [field]: nextValue })
  return (
    <div className="food-form-grid">
      <input value={value.name} placeholder="名称" onChange={(event) => update('name', event.target.value)} />
      <input value={value.type} placeholder="类型" onChange={(event) => update('type', event.target.value)} />
      <input
        value={value.characteristics}
        placeholder="特点"
        onChange={(event) => update('characteristics', event.target.value)}
      />
      <select value={value.service_type} onChange={(event) => update('service_type', event.target.value)}>
        {SERVICE_TYPES.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
      <label className="price-input">
        <span>¥</span>
        <input
          type="number"
          min="1"
          value={value.avg_price}
          onChange={(event) => update('avg_price', Number(event.target.value || 1))}
        />
      </label>
      <div className="form-actions">
        <button type="button" className="primary-small" onClick={onSubmit}>
          {submitText}
        </button>
        <button type="button" className="ghost-small" onClick={onCancel}>
          取消
        </button>
      </div>
    </div>
  )
}

function FoodManager() {
  const [foods, setFoods] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [adding, setAdding] = useState(false)
  const [newFood, setNewFood] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [editFood, setEditFood] = useState(emptyForm)

  const loadFoods = async (targetPage = page) => {
    setLoading(true)
    setError('')
    try {
      const data = await getFoods(targetPage, PAGE_SIZE)
      if (data.items.length === 0 && targetPage > 1 && data.total > 0) {
        const lastPage = Math.ceil(data.total / PAGE_SIZE)
        setPage(lastPage)
        return
      }
      setFoods(data.items)
      setTotalPages(data.total_pages)
      setTotal(data.total)
    } catch (err) {
      setError(errorDetail(err, '加载失败'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadFoods(page)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  const submitNew = async () => {
    try {
      await createFood(newFood)
      setNewFood(emptyForm)
      setAdding(false)
      setPage(1)
      await loadFoods(1)
    } catch (err) {
      setError(errorDetail(err, '添加失败'))
    }
  }

  const startEdit = (food) => {
    setEditingId(food.id)
    setEditFood({
      name: food.name,
      type: food.type,
      characteristics: food.characteristics,
      service_type: food.service_type,
      avg_price: food.avg_price,
    })
  }

  const submitEdit = async (id) => {
    try {
      await updateFood(id, editFood)
      setEditingId(null)
      await loadFoods(page)
    } catch (err) {
      setError(errorDetail(err, '保存失败'))
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('确定删除这个食物吗？')) return
    try {
      await deleteFood(id)
      await loadFoods(page)
    } catch (err) {
      setError(errorDetail(err, '删除失败'))
    }
  }

  return (
    <section className="page-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Food library</p>
          <h2>美食库</h2>
          <p>共 {total} 个可选食物，AI 只会从这里挑选。</p>
        </div>
        <button type="button" className="primary-small" onClick={() => setAdding(true)}>
          + 添加食物
        </button>
      </div>

      {error && <div className="error-box compact">{error}</div>}
      {adding && (
        <div className="inline-editor top-editor">
          <FoodForm
            value={newFood}
            onChange={setNewFood}
            onSubmit={submitNew}
            onCancel={() => setAdding(false)}
            submitText="添加"
          />
        </div>
      )}

      <div className="table-wrap">
        <table className="food-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>类型</th>
              <th>特点</th>
              <th>获取方式</th>
              <th>人均</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {foods.map((food) => (
              <tr key={food.id}>
                {editingId === food.id ? (
                  <td colSpan="6">
                    <FoodForm
                      value={editFood}
                      onChange={setEditFood}
                      onSubmit={() => submitEdit(food.id)}
                      onCancel={() => setEditingId(null)}
                      submitText="保存"
                    />
                  </td>
                ) : (
                  <>
                    <td className="strong-cell">{food.name}</td>
                    <td>{food.type}</td>
                    <td className="muted-cell">{food.characteristics}</td>
                    <td>
                      <span className="service-badge">{food.service_type}</span>
                    </td>
                    <td>¥{food.avg_price}</td>
                    <td>
                      <div className="row-actions">
                        <button type="button" className="ghost-small" onClick={() => startEdit(food)}>
                          编辑
                        </button>
                        <button type="button" className="danger-small" onClick={() => handleDelete(food.id)}>
                          删除
                        </button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
            {!foods.length && !loading && (
              <tr>
                <td colSpan="6" className="empty-cell">
                  还没有食物，先添加几个常吃的吧。
                </td>
              </tr>
            )}
          </tbody>
        </table>
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

export default FoodManager
