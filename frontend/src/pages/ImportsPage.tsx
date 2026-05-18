import { useRef, useState } from "react"

interface ImportResult {
  status: string
  saved: number
  skipped: number
}

export default function ImportsPage({
  businessId,
  apiBase,
}: {
  businessId: string
  apiBase: string
}) {
  const gstRef = useRef<HTMLInputElement>(null)
  const tallyRef = useRef<HTMLInputElement>(null)
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  async function upload(path: string, file?: File) {
    if (!file) return
    setUploading(true)
    setResult(null)
    setError(null)
    const form = new FormData()
    form.append("file", file)

    try {
      const res = await fetch(`${apiBase}${path}?business_id=${businessId}`, {
        method: "POST",
        body: form,
      })
      if (!res.ok) throw new Error(await res.text())
      const data: ImportResult = await res.json()
      setResult(`Imported ${data.saved} rows. Skipped ${data.skipped}.`)
    } catch (e: any) {
      setError(e.message || "Import failed")
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">GST and Tally imports</h1>
        <p className="page-sub">Free demo imports using files you upload, no paid GST or Tally API required.</p>
      </div>

      <div className="import-grid">
        <div className="import-card">
          <p className="chart-title">GST CSV import</p>
          <p className="import-copy">Upload a sales or purchase invoice CSV with date, amount, party, and invoice number columns.</p>
          <input ref={gstRef} type="file" accept=".csv" hidden onChange={e => upload("/api/imports/gst-csv", e.target.files?.[0])} />
          <button className="primary-button" disabled={uploading} onClick={() => gstRef.current?.click()}>
            Upload GST CSV
          </button>
        </div>
        <div className="import-card">
          <p className="chart-title">Tally XML import</p>
          <p className="import-copy">Upload exported Tally vouchers. The parser reads receipts, sales, purchases, and payments.</p>
          <input ref={tallyRef} type="file" accept=".xml" hidden onChange={e => upload("/api/imports/tally-xml", e.target.files?.[0])} />
          <button className="primary-button" disabled={uploading} onClick={() => tallyRef.current?.click()}>
            Upload Tally XML
          </button>
        </div>
      </div>

      {result && <div className="upload-result success"><p className="result-body">{result}</p></div>}
      {error && <div className="upload-result error-box"><p className="result-body">{error}</p></div>}
    </div>
  )
}
