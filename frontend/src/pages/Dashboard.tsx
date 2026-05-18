import { useEffect, useState } from "react"
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ReferenceLine, ResponsiveContainer, CartesianGrid,
} from "recharts"

interface ForecastDay {
  date: string
  balance: number
  net_flow: number
  is_risk: boolean
}

interface Alert {
  id: string
  alert_date: string
  severity: "low" | "medium" | "high"
  message: string
  projected_balance: number
  is_resolved: boolean
}

interface Recommendation {
  title: string
  description: string
  priority: "low" | "medium" | "high"
  due_date?: string | null
  impact?: number | null
}

interface ForecastResponse {
  current_balance: number
  minimum_safe_balance: number
  horizon_days: number
  forecast: ForecastDay[]
  alerts: Alert[]
  recommendations: Recommendation[]
}

const SEVERITY_COLOR = { low: "#BA7517", medium: "#E24B4A", high: "#A32D2D" }
const SEVERITY_BG = { low: "#FAEEDA", medium: "#FCEBEB", high: "#FCEBEB" }

function fmt(n: number) {
  return `INR ${Math.round(n).toLocaleString("en-IN")}`
}

export default function Dashboard({
  businessId,
  apiBase,
}: {
  businessId: string
  apiBase: string
}) {
  const [data, setData] = useState<ForecastResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${apiBase}/api/forecast/${businessId}`)
      .then(r => {
        if (!r.ok) throw new Error(`API error: ${r.status}`)
        return r.json()
      })
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [businessId, apiBase])

  if (loading) return <div className="state-msg">Building your forecast...</div>
  if (error) return <div className="state-msg error">Error: {error}</div>
  if (!data) return null

  const chartData = data.forecast.map(d => ({
    ...d,
    dateLabel: new Date(d.date).toLocaleDateString("en-IN", { day: "numeric", month: "short" }),
  }))
  const riskDays = data.forecast.filter(d => d.is_risk).length
  const lowestBal = Math.min(...data.forecast.map(d => d.balance))

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Cash flow forecast</h1>
        <p className="page-sub">Next {data.horizon_days} days, updated just now</p>
      </div>

      <div className="metrics">
        <div className="metric-card">
          <p className="metric-label">Current balance</p>
          <p className="metric-value">{fmt(data.current_balance)}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Lowest projected</p>
          <p className="metric-value" style={{ color: lowestBal < 0 ? "#A32D2D" : undefined }}>
            {fmt(lowestBal)}
          </p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Risk days</p>
          <p className="metric-value" style={{ color: riskDays > 0 ? "#A32D2D" : "#0F6E56" }}>
            {riskDays}
          </p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Safety threshold</p>
          <p className="metric-value">{fmt(data.minimum_safe_balance)}</p>
        </div>
      </div>

      <div className="chart-card">
        <p className="chart-title">90-day balance projection</p>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
            <XAxis dataKey="dateLabel" tick={{ fontSize: 11, fill: "#888" }} tickLine={false} interval={13} />
            <YAxis
              tickFormatter={v => `INR ${(Number(v) / 1000).toFixed(0)}k`}
              tick={{ fontSize: 11, fill: "#888" }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              formatter={(v: number) => [fmt(v), "Balance"]}
              labelStyle={{ fontSize: 12, fontWeight: 500 }}
              contentStyle={{ fontSize: 12, border: "0.5px solid #ddd", borderRadius: 8 }}
            />
            <ReferenceLine
              y={data.minimum_safe_balance}
              stroke="#E24B4A"
              strokeDasharray="5 3"
              label={{ value: "Safe threshold", fill: "#E24B4A", fontSize: 11, position: "right" }}
            />
            <Line
              type="monotone"
              dataKey="balance"
              stroke="#1D9E75"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#1D9E75" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {data.alerts.length > 0 ? (
        <div className="alerts-section">
          <p className="section-title">Risk alerts</p>
          <div className="alerts-list">
            {data.alerts.map(a => (
              <div
                key={a.id}
                className="alert-card"
                style={{
                  background: SEVERITY_BG[a.severity],
                  borderColor: SEVERITY_COLOR[a.severity],
                }}
              >
                <div className="alert-header">
                  <span className="alert-badge" style={{ background: SEVERITY_COLOR[a.severity] }}>
                    {a.severity}
                  </span>
                  <span className="alert-date">
                    {new Date(a.alert_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                  </span>
                </div>
                <p className="alert-msg" style={{ color: SEVERITY_COLOR[a.severity] }}>
                  {a.message}
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="no-alerts">
          <span>OK</span>
          <p>No cash flow risks detected in the next {data.horizon_days} days.</p>
        </div>
      )}

      <div className="actions-section">
        <p className="section-title">Recommended actions</p>
        <div className="actions-list">
          {data.recommendations.map((rec, index) => (
            <div key={`${rec.title}-${index}`} className="action-card">
              <div className="action-header">
                <span className="alert-badge" style={{ background: SEVERITY_COLOR[rec.priority] }}>
                  {rec.priority}
                </span>
                {rec.due_date && (
                  <span className="alert-date">
                    by {new Date(rec.due_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                  </span>
                )}
              </div>
              <p className="action-title">{rec.title}</p>
              <p className="action-body">{rec.description}</p>
              {typeof rec.impact === "number" && (
                <p className="action-impact">Estimated impact: {fmt(rec.impact)}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
