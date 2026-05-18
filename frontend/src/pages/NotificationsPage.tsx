import { useEffect, useState } from "react"

interface Notification {
  id: string
  type: string
  severity: "low" | "medium" | "high"
  title: string
  message: string
  date: string
}

export default function NotificationsPage({
  businessId,
  apiBase,
}: {
  businessId: string
  apiBase: string
}) {
  const [items, setItems] = useState<Notification[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${apiBase}/api/notifications/${businessId}`)
      .then(res => {
        if (!res.ok) throw new Error("Could not load notifications")
        return res.json()
      })
      .then(setItems)
      .catch(e => setError(e.message))
  }, [apiBase, businessId])

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Notifications</h1>
        <p className="page-sub">In-app alerts for demo use, no paid WhatsApp or SMS provider needed.</p>
      </div>
      {error && <div className="upload-result error-box"><p className="result-body">{error}</p></div>}
      <div className="notification-list">
        {items.length === 0 && <div className="state-msg">No notifications yet.</div>}
        {items.map(item => (
          <div className={`notification-card ${item.severity}`} key={item.id}>
            <div>
              <p className="action-title">{item.title}</p>
              <p className="action-body">{item.message}</p>
            </div>
            <span className="alert-date">{item.date}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
