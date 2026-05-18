import { FormEvent, useEffect, useMemo, useState } from "react"

type Category =
  | "invoice"
  | "payment_received"
  | "payroll"
  | "vendor"
  | "tax"
  | "rent"
  | "loan_emi"
  | "misc_income"
  | "misc_expense"

interface Transaction {
  id: string
  date: string
  amount: string
  category: Category
  source: string
  description?: string | null
  is_confirmed: boolean
  due_date?: string | null
  invoice_number?: string | null
  counterparty?: string | null
}

interface Draft {
  type: "receivable" | "payable" | "settled_inflow" | "settled_outflow"
  amount: string
  date: string
  due_date: string
  counterparty: string
  invoice_number: string
  description: string
  category: Category
}

const today = new Date().toISOString().slice(0, 10)

const initialDraft: Draft = {
  type: "receivable",
  amount: "",
  date: today,
  due_date: today,
  counterparty: "",
  invoice_number: "",
  description: "",
  category: "invoice",
}

function formatMoney(value: string | number) {
  const amount = typeof value === "number" ? value : Number(value)
  return `INR ${Math.round(amount).toLocaleString("en-IN")}`
}

function categoryFor(type: Draft["type"], selected: Category): Category {
  if (type === "receivable") return "invoice"
  if (type === "payable") return selected === "invoice" || selected === "payment_received" ? "vendor" : selected
  if (type === "settled_inflow") return selected === "invoice" ? "payment_received" : selected
  return selected === "invoice" || selected === "payment_received" ? "misc_expense" : selected
}

export default function TransactionsPage({
  businessId,
  apiBase,
}: {
  businessId: string
  apiBase: string
}) {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [draft, setDraft] = useState<Draft>(initialDraft)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const pending = useMemo(
    () => transactions.filter(tx => !tx.is_confirmed),
    [transactions],
  )

  async function loadTransactions() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/transactions/?business_id=${businessId}&limit=200`)
      if (!res.ok) throw new Error(await res.text())
      setTransactions(await res.json())
    } catch (e: any) {
      setError(e.message || "Could not load transactions")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTransactions()
  }, [businessId, apiBase])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)

    const rawAmount = Number(draft.amount)
    const isOutflow = draft.type === "payable" || draft.type === "settled_outflow"
    const isPending = draft.type === "receivable" || draft.type === "payable"

    const payload = {
      date: draft.date,
      amount: isOutflow ? -Math.abs(rawAmount) : Math.abs(rawAmount),
      category: categoryFor(draft.type, draft.category),
      source: "manual",
      description: draft.description || `${draft.counterparty} ${draft.invoice_number}`.trim(),
      is_confirmed: !isPending,
      due_date: isPending ? draft.due_date : null,
      invoice_number: draft.invoice_number || null,
      counterparty: draft.counterparty || null,
    }

    try {
      const res = await fetch(`${apiBase}/api/transactions/?business_id=${businessId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(await res.text())
      setDraft(initialDraft)
      await loadTransactions()
    } catch (e: any) {
      setError(e.message || "Could not save transaction")
    } finally {
      setSaving(false)
    }
  }

  async function settle(id: string) {
    await fetch(`${apiBase}/api/transactions/${id}/settle`, { method: "POST" })
    await loadTransactions()
  }

  async function remove(id: string) {
    await fetch(`${apiBase}/api/transactions/${id}`, { method: "DELETE" })
    await loadTransactions()
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Transactions</h1>
        <p className="page-sub">Add demo invoices, payables, and cash movements without paid API keys.</p>
      </div>

      <form className="entry-panel" onSubmit={submit}>
        <div className="form-grid">
          <label>
            Type
            <select value={draft.type} onChange={e => setDraft({ ...draft, type: e.target.value as Draft["type"] })}>
              <option value="receivable">Pending receivable</option>
              <option value="payable">Pending payable</option>
              <option value="settled_inflow">Settled inflow</option>
              <option value="settled_outflow">Settled outflow</option>
            </select>
          </label>
          <label>
            Amount
            <input required min="1" step="0.01" type="number" value={draft.amount} onChange={e => setDraft({ ...draft, amount: e.target.value })} />
          </label>
          <label>
            Date
            <input required type="date" value={draft.date} onChange={e => setDraft({ ...draft, date: e.target.value })} />
          </label>
          {(draft.type === "receivable" || draft.type === "payable") && (
            <label>
              Due date
              <input required type="date" value={draft.due_date} onChange={e => setDraft({ ...draft, due_date: e.target.value })} />
            </label>
          )}
          <label>
            Counterparty
            <input value={draft.counterparty} onChange={e => setDraft({ ...draft, counterparty: e.target.value })} placeholder="Client or vendor" />
          </label>
          <label>
            Invoice no.
            <input value={draft.invoice_number} onChange={e => setDraft({ ...draft, invoice_number: e.target.value })} placeholder="INV-001" />
          </label>
          <label className="span-2">
            Notes
            <input value={draft.description} onChange={e => setDraft({ ...draft, description: e.target.value })} placeholder="Optional description" />
          </label>
        </div>
        <button className="primary-button" disabled={saving}>{saving ? "Saving..." : "Add transaction"}</button>
      </form>

      {error && <div className="upload-result error-box"><p className="result-body">{error}</p></div>}

      {pending.length > 0 && (
        <section className="table-section">
          <p className="section-title">Pending items</p>
          <div className="transaction-list">
            {pending.map(tx => (
              <div className="transaction-row" key={tx.id}>
                <div>
                  <p className="tx-title">{tx.counterparty || tx.description || tx.category}</p>
                  <p className="tx-meta">Due {tx.due_date || tx.date} · {tx.category}</p>
                </div>
                <div className={Number(tx.amount) >= 0 ? "tx-positive" : "tx-negative"}>{formatMoney(tx.amount)}</div>
                <button className="small-button" onClick={() => settle(tx.id)}>Mark settled</button>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="table-section">
        <p className="section-title">All transactions</p>
        {loading ? (
          <div className="state-msg">Loading transactions...</div>
        ) : (
          <div className="transaction-list">
            {transactions.map(tx => (
              <div className="transaction-row" key={tx.id}>
                <div>
                  <p className="tx-title">{tx.counterparty || tx.description || tx.category}</p>
                  <p className="tx-meta">{tx.date} · {tx.source} · {tx.is_confirmed ? "settled" : "pending"}</p>
                </div>
                <div className={Number(tx.amount) >= 0 ? "tx-positive" : "tx-negative"}>{formatMoney(tx.amount)}</div>
                <button className="small-button muted" onClick={() => remove(tx.id)}>Delete</button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
