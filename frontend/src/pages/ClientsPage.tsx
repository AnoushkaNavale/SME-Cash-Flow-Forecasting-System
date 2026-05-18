import { FormEvent, useEffect, useState } from "react"

export interface Business {
  id: string
  name: string
  email: string
  gstin?: string | null
  phone?: string | null
}

interface Summary {
  business: Business
  current_balance: number
  pending_receivables: number
  pending_payables: number
  transaction_count: number
  pending_count: number
}

function fmt(n: number) {
  return `INR ${Math.round(n).toLocaleString("en-IN")}`
}

export default function ClientsPage({
  apiBase,
  selectedBusinessId,
  onSelectBusiness,
}: {
  apiBase: string
  selectedBusinessId: string
  onSelectBusiness: (business: Business) => void
}) {
  const [businesses, setBusinesses] = useState<Business[]>([])
  const [summaries, setSummaries] = useState<Record<string, Summary>>({})
  const [draft, setDraft] = useState({ name: "", email: "", gstin: "", phone: "" })
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/businesses/`)
      if (!res.ok) throw new Error(await res.text())
      const items: Business[] = await res.json()
      setBusinesses(items)

      const loaded: Record<string, Summary> = {}
      await Promise.all(items.map(async item => {
        const summaryRes = await fetch(`${apiBase}/api/businesses/${item.id}/summary`)
        if (summaryRes.ok) loaded[item.id] = await summaryRes.json()
      }))
      setSummaries(loaded)
    } catch (e: any) {
      setError(e.message || "Could not load clients")
    }
  }

  useEffect(() => {
    load()
  }, [apiBase])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    const res = await fetch(`${apiBase}/api/businesses/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: draft.name,
        email: draft.email,
        gstin: draft.gstin || null,
        phone: draft.phone || null,
      }),
    })
    if (!res.ok) {
      setError(await res.text())
      return
    }
    const created = await res.json()
    setDraft({ name: "", email: "", gstin: "", phone: "" })
    onSelectBusiness(created)
    await load()
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">CA clients</h1>
        <p className="page-sub">Switch between demo businesses and monitor cash risk per client.</p>
      </div>

      <form className="entry-panel" onSubmit={submit}>
        <div className="form-grid">
          <label>
            Business name
            <input required value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} />
          </label>
          <label>
            Email
            <input required type="email" value={draft.email} onChange={e => setDraft({ ...draft, email: e.target.value })} />
          </label>
          <label>
            GSTIN
            <input maxLength={15} value={draft.gstin} onChange={e => setDraft({ ...draft, gstin: e.target.value.toUpperCase() })} />
          </label>
          <label>
            Phone
            <input value={draft.phone} onChange={e => setDraft({ ...draft, phone: e.target.value })} />
          </label>
        </div>
        <button className="primary-button">Add client</button>
      </form>

      {error && <div className="upload-result error-box"><p className="result-body">{error}</p></div>}

      <div className="client-grid">
        {businesses.map(business => {
          const summary = summaries[business.id]
          return (
            <button
              className={`client-card ${business.id === selectedBusinessId ? "selected" : ""}`}
              key={business.id}
              onClick={() => onSelectBusiness(business)}
            >
              <div className="client-head">
                <div>
                  <p className="client-name">{business.name}</p>
                  <p className="tx-meta">{business.email}</p>
                </div>
                <span className="client-status">{summary?.pending_count || 0} pending</span>
              </div>
              <div className="client-metrics">
                <span>Balance<br /><strong>{fmt(summary?.current_balance || 0)}</strong></span>
                <span>Receivables<br /><strong>{fmt(summary?.pending_receivables || 0)}</strong></span>
                <span>Payables<br /><strong>{fmt(summary?.pending_payables || 0)}</strong></span>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
