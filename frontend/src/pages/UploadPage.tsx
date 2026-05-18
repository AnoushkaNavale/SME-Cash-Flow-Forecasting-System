import { useState, useRef } from "react"

interface UploadResult {
  saved:   number
  skipped: number
  message: string
}

export default function UploadPage({
  businessId,
  apiBase,
}: {
  businessId: string
  apiBase: string
}) {
  const [dragging, setDragging]   = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult]       = useState<UploadResult | null>(null)
  const [error, setError]         = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFile(file: File) {
    if (!file.name.endsWith(".csv")) {
      setError("Please upload a .csv file. Export your bank statement as CSV.")
      return
    }

    setUploading(true)
    setError(null)
    setResult(null)

    const form = new FormData()
    form.append("file", file)

    try {
      const res = await fetch(
        `${apiBase}/api/upload/bank-statement?business_id=${businessId}`,
        { method: "POST", body: form }
      )
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setResult(data)
    } catch (e: any) {
      setError(e.message || "Upload failed")
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Upload bank statement</h1>
        <p className="page-sub">
          Export your bank statement as CSV and upload it here.
          Works with HDFC, ICICI, SBI, Axis, and most Indian banks.
        </p>
      </div>

      <div
        className={`drop-zone ${dragging ? "dragging" : ""} ${uploading ? "uploading" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => {
          e.preventDefault()
          setDragging(false)
          const file = e.dataTransfer.files[0]
          if (file) handleFile(file)
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          style={{ display: "none" }}
          onChange={e => { if (e.target.files?.[0]) handleFile(e.target.files[0]) }}
        />
        <div className="drop-icon">⬆</div>
        {uploading
          ? <p className="drop-text">Importing transactions…</p>
          : <p className="drop-text">Drop your CSV here or click to browse</p>
        }
        <p className="drop-sub">Supports HDFC, ICICI, SBI, Axis Bank CSV exports</p>
      </div>

      {result && (
        <div className="upload-result success">
          <p className="result-title">Import complete</p>
          <p className="result-body">{result.message}</p>
          <p className="result-body">{result.skipped} rows skipped (unreadable dates or zero amounts)</p>
        </div>
      )}

      {error && (
        <div className="upload-result error-box">
          <p className="result-title">Upload failed</p>
          <p className="result-body">{error}</p>
        </div>
      )}

      <div className="how-to">
        <p className="section-title">How to export from your bank</p>
        <div className="bank-list">
          {[
            ["HDFC",  "NetBanking → My Accounts → Download Statement → CSV"],
            ["ICICI", "iMobile / NetBanking → Statements → Download → CSV"],
            ["SBI",   "YONO / NetBanking → Account Statement → Download → Excel (save as CSV)"],
            ["Axis",  "NetBanking → Accounts → Statement → Download → CSV"],
          ].map(([bank, steps]) => (
            <div key={bank} className="bank-row">
              <span className="bank-name">{bank}</span>
              <span className="bank-steps">{steps}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
