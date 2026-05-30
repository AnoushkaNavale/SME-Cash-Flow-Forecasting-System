import { useEffect, useState } from "react"
import ClientsPage, { Business } from "./pages/ClientsPage"
import Dashboard from "./pages/Dashboard"
import ImportsPage from "./pages/ImportsPage"
import LendingPage from "./pages/LendingPage"
import NotificationsPage from "./pages/NotificationsPage"
import TransactionsPage from "./pages/TransactionsPage"
import UploadPage from "./pages/UploadPage"
import "./index.css"

type Page = "clients" | "dashboard" | "transactions" | "imports" | "upload" | "notifications" | "lending"

const DEMO_BUSINESS: Business = {
  id: "11111111-1111-1111-1111-111111111111",
  name: "Test SME Pvt Ltd",
  email: "test@sme.com",
}
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

export default function App() {
  const pageFromHash = (): Page => {
    const hash = window.location.hash.replace("#", "") as Page
    return ["clients", "dashboard", "transactions", "imports", "upload", "notifications", "lending"].includes(hash)
      ? hash
      : "dashboard"
  }
  const [page, setPageState] = useState<Page>(pageFromHash)
  const [business, setBusiness] = useState<Business>(DEMO_BUSINESS)

  const setPage = (nextPage: Page) => {
    window.location.hash = nextPage
    setPageState(nextPage)
  }

  useEffect(() => {
    fetch(`${API_BASE}/api/businesses/${business.id}`)
      .then(res => res.ok ? res.json() : DEMO_BUSINESS)
      .then(setBusiness)
      .catch(() => setBusiness(DEMO_BUSINESS))
  }, [])

  useEffect(() => {
    const onHashChange = () => setPageState(pageFromHash())
    window.addEventListener("hashchange", onHashChange)
    return () => window.removeEventListener("hashchange", onHashChange)
  }, [])

  const navItems: Array<[Page, string]> = [
    ["clients", "Clients"],
    ["dashboard", "Dashboard"],
    ["transactions", "Transactions"],
    ["imports", "GST/Tally"],
    ["upload", "Bank CSV"],
    ["notifications", "Alerts"],
    ["lending", "Lending"],
  ]

  return (
    <div className="app">
      <nav className="navbar">
        <div className="nav-brand">
          <span className="nav-logo">CF</span>
          <div>
            <span className="nav-title">CashFlow</span>
            <p className="active-client">{business.name}</p>
          </div>
        </div>
        <div className="nav-links">
          {navItems.map(([id, label]) => (
            <button
              key={id}
              className={`nav-link ${page === id ? "active" : ""}`}
              onClick={() => setPage(id)}
            >
              {label}
            </button>
          ))}
        </div>
      </nav>

      <main className="main">
        {page === "clients" && (
          <ClientsPage
            apiBase={API_BASE}
            selectedBusinessId={business.id}
            onSelectBusiness={(selected) => {
              setBusiness(selected)
              setPage("dashboard")
            }}
          />
        )}
        {page === "dashboard" && <Dashboard businessId={business.id} apiBase={API_BASE} />}
        {page === "transactions" && <TransactionsPage businessId={business.id} apiBase={API_BASE} />}
        {page === "imports" && <ImportsPage businessId={business.id} apiBase={API_BASE} />}
        {page === "upload" && <UploadPage businessId={business.id} apiBase={API_BASE} />}
        {page === "notifications" && <NotificationsPage businessId={business.id} apiBase={API_BASE} />}
        {page === "lending" && <LendingPage businessId={business.id} apiBase={API_BASE} />}
      </main>
    </div>
  )
}
