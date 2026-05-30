const http = require("http");

const businessId = "11111111-1111-1111-1111-111111111111";
const today = new Date();
const iso = (offset) => {
  const d = new Date(today);
  d.setDate(d.getDate() + offset);
  return d.toISOString().slice(0, 10);
};

const forecast = Array.from({ length: 90 }, (_, i) => {
  const wave = Math.sin(i / 6) * 9000;
  const decline = i * 1800;
  const bump = i === 18 ? 90000 : 0;
  const balance = 210000 + wave - decline + bump;
  return {
    date: iso(i),
    balance: Math.round(balance),
    net_flow: Math.round(wave / 6 - 1800 + bump),
    is_risk: balance < 50000,
  };
});

const businesses = [
  { id: businessId, name: "Test SME Pvt Ltd", email: "test@sme.com", gstin: null, phone: "9876543210", created_at: new Date().toISOString() },
  { id: "22222222-2222-2222-2222-222222222222", name: "Anaya Textiles", email: "accounts@anayatextiles.in", gstin: "27ABCDE1234F1Z5", phone: "9898989898", created_at: new Date().toISOString() },
  { id: "33333333-3333-3333-3333-333333333333", name: "Navale Foods", email: "finance@navalefoods.in", gstin: "29ABCDE1234F1Z1", phone: "9797979797", created_at: new Date().toISOString() },
];

const transactions = [
  { id: "t1", business_id: businessId, date: iso(-2), amount: "150000", category: "payment_received", source: "manual", description: "Client A retainer", is_confirmed: true, due_date: null, invoice_number: "REC-104", counterparty: "Client A", created_at: new Date().toISOString() },
  { id: "t2", business_id: businessId, date: iso(0), amount: "120000", category: "invoice", source: "gst", description: "GST sales invoice", is_confirmed: false, due_date: iso(10), invoice_number: "INV-047", counterparty: "Client C", created_at: new Date().toISOString() },
  { id: "t3", business_id: businessId, date: iso(0), amount: "-45000", category: "payroll", source: "manual", description: "Upcoming payroll", is_confirmed: false, due_date: iso(15), invoice_number: null, counterparty: "Payroll", created_at: new Date().toISOString() },
  { id: "t4", business_id: businessId, date: iso(-4), amount: "-18000", category: "vendor", source: "tally", description: "Raw material purchase", is_confirmed: true, due_date: null, invoice_number: "PUR-210", counterparty: "Ravi Traders", created_at: new Date().toISOString() },
];

function send(res, data) {
  res.writeHead(200, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  });
  res.end(JSON.stringify(data));
}

const server = http.createServer((req, res) => {
  if (req.method === "OPTIONS") return send(res, {});
  const url = new URL(req.url, "http://localhost:8000");

  if (url.pathname === "/health") return send(res, { status: "healthy" });
  if (url.pathname === `/api/businesses/${businessId}`) return send(res, businesses[0]);
  if (url.pathname === "/api/businesses/") return send(res, businesses);
  if (url.pathname.endsWith("/summary")) {
    return send(res, {
      business: businesses.find((b) => url.pathname.includes(b.id)) || businesses[0],
      current_balance: 166000,
      pending_receivables: 120000,
      pending_payables: 45000,
      transaction_count: 18,
      pending_count: 2,
    });
  }
  if (url.pathname === `/api/forecast/${businessId}`) {
    return send(res, {
      business_id: businessId,
      generated_at: new Date().toISOString(),
      current_balance: 166000,
      minimum_safe_balance: 50000,
      horizon_days: 90,
      forecast,
      alerts: [
        { id: "a1", alert_date: iso(64), severity: "medium", message: "Balance drops below your INR 50,000 safety threshold around this date.", projected_balance: 46200, is_resolved: false },
      ],
      recommendations: [
        { title: "Chase receivables due soon", description: "Follow up with Client C for INR 120,000 due in 10 days.", priority: "medium", due_date: iso(10), impact: 120000 },
        { title: "Review upcoming outflows", description: "Consider deferring payroll or vendor payments if the risk window stays open.", priority: "low", due_date: iso(15), impact: 45000 },
        { title: "Prepare working capital buffer", description: "Keep INR 70,000 ready before the projected risk window.", priority: "medium", due_date: iso(64), impact: 70000 },
      ],
    });
  }
  if (url.pathname === "/api/transactions/") return send(res, transactions);
  if (url.pathname === `/api/notifications/${businessId}`) {
    return send(res, [
      { id: "n1", type: "risk", severity: "medium", title: "Cash risk detected", message: "Balance may fall below the safety threshold in the next 90 days.", date: iso(64), is_read: false },
      { id: "n2", type: "receivable", severity: "medium", title: "Upcoming receivable", message: "Client C invoice is due soon.", date: iso(10), is_read: false },
      { id: "n3", type: "payable", severity: "low", title: "Upcoming payable", message: "Payroll is due soon.", date: iso(15), is_read: false },
    ]);
  }
  if (url.pathname === `/api/lending/${businessId}/offer`) {
    return send(res, {
      eligible: true,
      status: "mock_preapproved",
      message: "Demo offer only: no lender API or credit bureau call has been made.",
      suggested_limit: 75000,
      risk_date: iso(64),
      apr: 18,
      tenure_days: 90,
    });
  }

  send(res, { status: "ok" });
});

server.listen(8000, "127.0.0.1", () => {
  console.log("Mock API running on http://127.0.0.1:8000");
});
