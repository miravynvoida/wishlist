import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, ArrowUpRight, Check, ChevronRight, CirclePlus, Gift, Layers3, List, LockKeyhole, Plus, Search, Settings2, Trash2, X, Sun, Moon } from 'lucide-react'

declare global { interface Window { Telegram?: { WebApp?: { initData: string; initDataUnsafe?: { user?: { id: number; first_name?: string } }; ready: () => void; expand: () => void; colorScheme?: string } } } }

type Owner = { id: number; display_name: string; item_count: number }
type Category = { id: number; owner_id: number; name: string; emoji: string; item_count: number }
type Item = { id: number; owner_id: number; category_id: number | null; title: string; description: string; url: string; price: string; image_url: string; category_name?: string; category_emoji?: string; is_reserved: number; can_cancel_reservation?: number }
const API = import.meta.env.VITE_API_BASE ?? ''
const OWNER_IDS = [8580512680, 1973334354]
const tg = window.Telegram?.WebApp

async function api(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (tg?.initData) headers.set('X-Telegram-Init-Data', tg.initData)
  const response = await fetch(`${API}${path}`, { ...init, headers })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || 'Что-то пошло не так')
  return body
}
function App() {
  const params = new URLSearchParams(window.location.search)
  const requestedOwner = Number(params.get('owner') || params.get('start'))
  const hasValidLink = OWNER_IDS.includes(requestedOwner)
  const [owners, setOwners] = useState<Owner[]>([])
  const [ownerId, setOwnerId] = useState(requestedOwner)
  const [categories, setCategories] = useState<Category[]>([])
  const [items, setItems] = useState<Item[]>([])
  const [mode, setMode] = useState<'all'|'category'>((params.get('mode') as 'all'|'category') || 'all')
  const [categoryId, setCategoryId] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [theme, setTheme] = useState<'light' | 'dark'>(() => (localStorage.getItem('wishlist-theme') as 'light' | 'dark') || 'light')
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem('wishlist-theme', theme) }, [theme])
  const [editor, setEditor] = useState<Item | null | 'new'>(null)
  const [selectedItem, setSelectedItem] = useState<Item | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [newCat, setNewCat] = useState('')
  const [newEmoji, setNewEmoji] = useState('🎁')
  const [ownerName, setOwnerName] = useState('')
  const [form, setForm] = useState({ title:'', category_id:'', price:'', url:'', description:'', image_url:'' })
  const viewerId = tg?.initDataUnsafe?.user?.id
  const isOwner = viewerId === ownerId && OWNER_IDS.includes(viewerId || 0)
  const activeOwner = owners.find(o => o.id === ownerId)
  const filtered = useMemo(() => items.filter(i => `${i.title} ${i.description} ${i.category_name || ''}`.toLowerCase().includes(query.toLowerCase())).sort((a,b) => (a.category_name || 'Без категории').localeCompare(b.category_name || 'Без категории', 'ru') || a.title.localeCompare(b.title, 'ru')), [items, query])

  async function refresh() {
    if (!hasValidLink) return
    try {
      const [o, c, w] = await Promise.all([
        api('/api/owners'), api(`/api/categories/${ownerId}`), api(`/api/wishlist/${ownerId}${categoryId ? `?category_id=${categoryId}` : ''}`)
      ])
      setOwners(o); setOwnerName(o.find((x: Owner) => x.id === ownerId)?.display_name || ''); setCategories(c); setItems(w.items)
    } catch (e) { setNotice(e instanceof Error ? e.message : 'Ошибка загрузки') }
  }
  useEffect(() => { tg?.ready(); tg?.expand(); }, [])
  useEffect(() => { setCategoryId(null); setQuery(''); }, [ownerId])
  useEffect(() => { refresh() }, [ownerId, categoryId])
  function openEditor(item: Item | null) {
    setForm(item ? { title:item.title, category_id:item.category_id ? String(item.category_id) : '', price:item.price || '', url:item.url || '', description:item.description || '', image_url:item.image_url || '' } : { title:'', category_id: categories[0] ? String(categories[0].id) : '', price:'', url:'', description:'', image_url:'' })
    setEditor(item || 'new')
  }
  async function saveItem() {
    if (!form.title.trim()) return setNotice('Укажите название записи')
    setBusy(true)
    try {
      const payload = { owner_id: ownerId, title: form.title.trim(), category_id: form.category_id ? Number(form.category_id) : null, price:form.price, url:form.url, description:form.description, image_url:form.image_url }
      await api(editor === 'new' ? '/api/items' : `/api/items/${(editor as Item).id}`, { method: editor === 'new' ? 'POST' : 'PATCH', body: JSON.stringify(payload) })
      setEditor(null); setNotice('Запись сохранена'); await refresh()
    } catch (e) { setNotice(e instanceof Error ? e.message : 'Ошибка сохранения') } finally { setBusy(false) }
  }
  async function deleteItem(item: Item) {
    if (!confirm(`Удалить «${item.title}»?`)) return
    try { await api(`/api/items/${item.id}`, { method:'DELETE' }); setNotice('Запись удалена'); await refresh() }
    catch (e) { setNotice(e instanceof Error ? e.message : 'Ошибка удаления') }
  }
  async function clearAll() {
    if (!confirm('Удалить ВСЕ желания из твоего вишлиста? Это действие нельзя отменить.')) return
    try { await api(`/api/wishlist/${ownerId}`, { method:'DELETE' }); setShowSettings(false); setNotice('Список очищен'); await refresh() }
    catch (e) { setNotice(e instanceof Error ? e.message : 'Ошибка удаления') }
  }
  async function addCategory() {
    if (!newCat.trim()) return
    try { await api('/api/categories', { method:'POST', body:JSON.stringify({ owner_id:ownerId, name:newCat.trim(), emoji:newEmoji }) }); setNewCat(''); setNotice('Категория добавлена'); await refresh() }
    catch (e) { setNotice(e instanceof Error ? e.message : 'Не удалось добавить категорию') }
  }
  async function removeCategory(cat: Category) {
    if (!confirm(`Удалить категорию «${cat.name}»? Желания останутся в списке без категории.`)) return
    try { await api(`/api/categories/${cat.id}`, { method:'DELETE' }); if (categoryId === cat.id) setCategoryId(null); setNotice('Категория удалена'); await refresh() }
    catch (e) { setNotice(e instanceof Error ? e.message : 'Ошибка') }
  }
  async function cancelReservation(item: Item) {
    if (!confirm(`Отменить бронирование «${item.title}»?`)) return
    try { await api(`/api/items/${item.id}/reserve`, { method:'DELETE' }); setNotice('Бронирование отменено'); await refresh() }
    catch (e) { setNotice(e instanceof Error ? e.message : 'Не удалось отменить бронирование') }
  }
  async function saveOwnerName() {
    if (!ownerName.trim()) return setNotice('Введите имя владельца')
    try { await api(`/api/owners/${ownerId}`, { method:'PATCH', body:JSON.stringify({display_name:ownerName.trim()}) }); setNotice('Имя сохранено'); await refresh() }
    catch (e) { setNotice(e instanceof Error ? e.message : 'Не удалось сохранить имя') }
  }
  async function reserve(item: Item) {
    if (!tg?.initData) return setNotice('Для безопасного бронирования откройте ссылку в Telegram')
    try { await api(`/api/items/${item.id}/reserve`, { method:'POST' }); setNotice('Подарок забронирован — сюрприз сохранён 🤫'); await refresh() }
    catch (e) { setNotice(e instanceof Error ? e.message : 'Не удалось забронировать') }
  }

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-icon"><Gift size={19}/></div><div><div className="brand-name">Личный список</div><div className="brand-sub">Список желаний</div></div></div>
      <div className="header-actions"><button className="icon-button theme-toggle" onClick={() => setTheme(v => v === 'light' ? 'dark' : 'light')} aria-label={theme === 'light' ? 'Включить тёмную тему' : 'Включить светлую тему'} title={theme === 'light' ? 'Тёмная тема' : 'Светлая тема'}>{theme === 'light' ? <Moon size={18}/> : <Sun size={18}/>}</button>{isOwner && <button className="icon-button" onClick={() => setShowSettings(v => !v)} aria-label="Настройки"><Settings2 size={19}/></button>}</div>
    </header>
    {notice && <button className="notice" onClick={() => setNotice('')}>{notice}<X size={15}/></button>}
    {!hasValidLink ? <section className="hero"><div className="eyebrow"><span className="dot"/> ДОСТУП ОГРАНИЧЕН</div><h1>Нет доступа</h1><p>Откройте персональную ссылку, чтобы просмотреть список.</p></section> : <section className="hero"><div className="eyebrow"><span className="dot"/> СПИСОК ЖЕЛАНИЙ</div><h1>Список</h1><p>Записи и категории.</p></section>}
    {hasValidLink && <div className="content">
      <div className="section-heading"><div><span className="kicker">СПИСОК</span><h2>{activeOwner?.display_name || 'Желания'} <span className="count">{items.length}</span></h2></div>
        {isOwner && <button className="add-button" onClick={() => openEditor(null)}><Plus size={17}/> Добавить</button>}
      </div>
      <div className="mode-tabs">
        <button className={mode==='all'?'selected':''} onClick={() => {setMode('all');setCategoryId(null)}}><List size={16}/> Все желания</button>
        <button className={mode==='category'?'selected':''} onClick={() => {setMode('category');setCategoryId(null)}}><Layers3 size={16}/> Категории</button>
      </div>
      {mode==='category' && !categoryId ? <div className="category-grid">
        {categories.map(c => <button className="category-card" key={c.id} onClick={() => setCategoryId(c.id)}><span className="category-emoji">{c.emoji}</span><span className="category-name">{c.name}</span><span className="category-bottom">{c.item_count} желаний <ChevronRight size={15}/></span></button>)}
        {isOwner && <button className="category-add" onClick={() => setShowSettings(true)}><CirclePlus size={21}/><span>Новая категория</span></button>}
      </div> : <>
        {categoryId && <button className="back-link" onClick={() => setCategoryId(null)}><ArrowLeft size={16}/> Все категории</button>}
        <label className="searchbox"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Найти желание..."/>{query && <button onClick={()=>setQuery('')}><X size={14}/></button>}</label>
        {filtered.length===0 ? <div className="empty"><div className="empty-icon"><Gift size={26}/></div><h3>Пока здесь тихо</h3><p>{isOwner?'Добавьте первую запись.':'В этом разделе пока нет записей.'}</p>{isOwner && <button className="primary-button" onClick={()=>openEditor(null)}>Добавить желание</button>}</div> :
          <div className="item-grid">{filtered.map(item => <article className="item-card" key={item.id} onClick={() => setSelectedItem(item)}>
            <div className="item-art">{item.image_url ? <img src={item.image_url} alt="" onError={e=>{e.currentTarget.style.display='none'}}/> : <div className="art-placeholder"><Gift size={29}/></div>}
              {item.is_reserved===1 && !isOwner && <span className="reserved"><LockKeyhole size={12}/> Забронировано</span>}
              {isOwner && <div className="card-actions" onClick={e=>e.stopPropagation()}><button className="card-edit" onClick={()=>openEditor(item)} aria-label="Редактировать">Изменить</button><button className="card-delete" onClick={()=>deleteItem(item)} aria-label="Удалить"><Trash2 size={15}/></button></div>}
            </div>
            <div className="item-info">{item.category_name && <div className="item-category">{item.category_emoji} {item.category_name}</div>}<h3>{item.title}</h3>{item.description && <p>{item.description}</p>}
              <div className="item-footer">{item.price && <strong>{item.price}</strong>}{item.url && <a className="link-button" onClick={e=>e.stopPropagation()} href={item.url} target="_blank" rel="noreferrer">Открыть товар <ArrowUpRight size={15}/></a>}</div>
              {!isOwner && item.is_reserved!==1 && <button className="reserve-button" onClick={e=>{e.stopPropagation(); reserve(item)}}><Gift size={15}/> Забронировать</button>}
              {!isOwner && item.can_cancel_reservation===1 && <button className="reserve-button cancel-reserve" onClick={e=>{e.stopPropagation(); cancelReservation(item)}}>Отменить бронирование</button>}
            </div>
          </article>)}</div>}
      </>}
      {isOwner && <div className="owner-note"><LockKeyhole size={15}/> Ты можешь редактировать только свой список.</div>}
    </div>}
    {selectedItem && <div className="overlay" onClick={()=>setSelectedItem(null)}><section className="sheet detail-sheet" onClick={e=>e.stopPropagation()}>
      <div className="sheet-head"><div><span className="kicker">ЖЕЛАНИЕ</span><h2>{selectedItem.title}</h2></div><button className="icon-button" onClick={()=>setSelectedItem(null)}><X size={18}/></button></div>
      {selectedItem.image_url ? <img className="detail-image" src={selectedItem.image_url} alt={selectedItem.title}/> : <div className="detail-placeholder"><Gift size={36}/></div>}
      {selectedItem.category_name && <div className="item-category">{selectedItem.category_emoji} {selectedItem.category_name}</div>}
      {selectedItem.price && <div className="detail-price">{selectedItem.price}</div>}
      {selectedItem.description && <p className="detail-description">{selectedItem.description}</p>}
      {selectedItem.url && <a className="primary-button full-button detail-link" href={selectedItem.url} target="_blank" rel="noreferrer">Открыть товар <ArrowUpRight size={16}/></a>}
      {isOwner ? <div className="detail-actions"><button className="primary-button" onClick={()=>{const item=selectedItem;setSelectedItem(null);openEditor(item)}}>Редактировать</button><button className="danger-button" onClick={()=>{const item=selectedItem;setSelectedItem(null);deleteItem(item)}}>Удалить</button></div> : selectedItem.is_reserved!==1 ? <button className="primary-button full-button" onClick={()=>reserve(selectedItem)}><Gift size={16}/> Забронировать</button> : <div className="reserved-detail"><LockKeyhole size={16}/> Уже забронировано</div>}
      {!isOwner && selectedItem.can_cancel_reservation===1 && <button className="reserve-button cancel-reserve" onClick={()=>cancelReservation(selectedItem)}>Отменить бронирование</button>}
    </section></div>}
    {showSettings && isOwner && <div className="overlay" onClick={()=>setShowSettings(false)}><section className="sheet" onClick={e=>e.stopPropagation()}>
      <div className="sheet-head"><div><span className="kicker">УПРАВЛЕНИЕ</span><h2>Настройки списка</h2></div><button className="icon-button" onClick={()=>setShowSettings(false)}><X size={18}/></button></div>
      <label className="field-label owner-name-field">Имя владельца списка<input value={ownerName} maxLength={80} onChange={e=>setOwnerName(e.target.value)} placeholder="Например, Алексей"/><button className="primary-button" onClick={saveOwnerName}>Сохранить имя</button></label>
      <h3 className="field-label">Новая категория</h3><div className="category-form"><input className="emoji-input" value={newEmoji} onChange={e=>setNewEmoji(e.target.value)} maxLength={4}/><input value={newCat} onChange={e=>setNewCat(e.target.value)} placeholder="Например, Путешествия"/><button className="primary-button" onClick={addCategory}>Добавить</button></div>
      <div className="manage-categories">{categories.map(c=><div key={c.id}><span>{c.emoji} {c.name}</span><button onClick={()=>removeCategory(c)}><Trash2 size={15}/></button></div>)}</div>
      <div className="danger-zone"><div><strong>Удалить все желания</strong><p>Категории останутся, желания и бронирования удалятся.</p></div><button className="danger-button" onClick={clearAll}>Очистить</button></div>
    </section></div>}
    {editor && isOwner && <div className="overlay" onClick={()=>setEditor(null)}><section className="sheet" onClick={e=>e.stopPropagation()}>
      <div className="sheet-head"><div><span className="kicker">ЗАПИСЬ</span><h2>{editor==='new'?'Новая запись':'Редактировать'}</h2></div><button className="icon-button" onClick={()=>setEditor(null)}><X size={18}/></button></div>
      <div className="form-fields">
        <label>Название *<input value={form.title} onChange={e=>setForm({...form,title:e.target.value})} placeholder="Название"/></label>
        <label>Категория<select value={form.category_id} onChange={e=>setForm({...form,category_id:e.target.value})}><option value="">Без категории</option>{categories.map(c=><option key={c.id} value={c.id}>{c.emoji} {c.name}</option>)}</select></label>
        <label>Ссылка на товар<input value={form.url} onChange={e=>setForm({...form,url:e.target.value})} placeholder="https://..."/></label>
        <label>Цена<input value={form.price} onChange={e=>setForm({...form,price:e.target.value})} placeholder="Например, 5 000 ₽"/></label>
        <label>Ссылка на фото<input value={form.image_url} onChange={e=>setForm({...form,image_url:e.target.value})} placeholder="https://..."/></label>
        <label>Комментарий<textarea value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="Размер, цвет, детали..." rows={3}/></label>
      </div>
      <button className="primary-button full-button" disabled={busy} onClick={saveItem}>{busy?'Сохраняю...':'Сохранить желание'}</button>
    </section></div>}
    {hasValidLink && <nav className="bottom-nav">
      <button className={mode==='all'?'active':''} onClick={()=>{setMode('all');setCategoryId(null)}}><List size={19}/><span>Желания</span></button>
      <button className={mode==='category'?'active':''} onClick={()=>{setMode('category');setCategoryId(null)}}><Layers3 size={19}/><span>Категории</span></button>
      {isOwner && <button className="nav-add" onClick={()=>openEditor(null)}><Plus size={22}/><span>Добавить</span></button>}
      <button onClick={()=>isOwner ? setShowSettings(true) : setNotice('Чтобы забронировать подарок, откройте приложение через Telegram')}><Settings2 size={19}/><span>{isOwner?'Профиль':'Помощь'}</span></button>
    </nav>}
    <footer><span>ЛИЧНЫЙ СПИСОК</span></footer>
  </main>
}
export default App
