import { useEffect, useState } from "react"

interface Offer {
  eligible: boolean
  status: string
  message: string
  suggested_limit: number
  risk_date?: string | null
  apr?: number | null
  tenure_days?: number | null
}

function fmt(n: number) {
  return `INR ${Math.round(n).toLocaleString("en-IN")}`
}

export default function LendingPage({
  businessId,
  apiBase,
}: {
  businessId: string
  apiBase: string
}) {
  const [offer, setOffer] = useState<Offer | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${apiBase}/api/lending/${businessId}/offer`)
      .then(res => {
        if (!res.ok) throw new Error("Could not calculate lending offer")
        return res.json()
      })
      .then(setOffer)
      .catch(e => setError(e.message))
  }, [apiBase, businessId])

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Working capital</h1>
        <p className="page-sub">Mock lending trigger for demo only. No lender, bureau, or payment API is called.</p>
      </div>
      {error && <div className="upload-result error-box"><p className="result-body">{error}</p></div>}
      {offer && (
        <div className="lending-panel">
          <p className="client-status">{offer.status}</p>
          <h2>{offer.eligible ? fmt(offer.suggested_limit) : "No credit needed"}</h2>
          <p>{offer.message}</p>
          {offer.eligible && (
            <div className="client-metrics">
              <span>Risk date<br /><strong>{offer.risk_date}</strong></span>
              <span>Demo APR<br /><strong>{offer.apr}%</strong></span>
              <span>Tenure<br /><strong>{offer.tenure_days} days</strong></span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
