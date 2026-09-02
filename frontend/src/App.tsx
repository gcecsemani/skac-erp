import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import {
  LayoutDashboard, ShoppingCart, ReceiptText, Undo2, Users, Package,
  Boxes, ArrowLeftRight, Truck, Landmark, BarChart3, Sparkles, Brain,
  ShieldCheck, UserCog, Menu, Leaf, LogOut, Building2, Wallet, Settings2, MapPin,
} from "lucide-react";
import { useAuth } from "./auth";
import { prefetchMasters } from "./offline";
import { canAccessPath, homePath, isOwner } from "./roles";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import POS from "./pages/POS";
import Invoices from "./pages/Invoices";
import Returns from "./pages/Returns";
import Customers from "./pages/Customers";
import Products from "./pages/Products";
import Stock from "./pages/Stock";
import Transfers from "./pages/Transfers";
import Purchasing from "./pages/Purchasing";
import Accounting from "./pages/Accounting";
import Reports from "./pages/Reports";
import Assistant from "./pages/Assistant";
import PurchaseAI from "./pages/PurchaseAI";
import Compliance from "./pages/Compliance";
import Admin from "./pages/Admin";
import Branches from "./pages/Branches";
import Expenses from "./pages/Expenses";
import FieldVisits from "./pages/FieldVisits";
import Config from "./pages/Config";

const NAV = [
  { group: "Overview", items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard, ownerOnly: true }] },
  {
    group: "Sales", items: [
      { to: "/pos", label: "POS Billing", icon: ShoppingCart },
      { to: "/invoices", label: "Invoices", icon: ReceiptText },
      { to: "/returns", label: "Sales Returns", icon: Undo2 },
      { to: "/customers", label: "Farmers", icon: Users },
      { to: "/field-visits", label: "Field visits", icon: MapPin },
    ],
  },
  {
    group: "Inventory", items: [
      { to: "/products", label: "Products", icon: Package, ownerOnly: true },
      { to: "/stock", label: "Stock", icon: Boxes, ownerOnly: true },
      { to: "/transfers", label: "Transfers", icon: ArrowLeftRight, ownerOnly: true },
    ],
  },
  { group: "Purchasing", items: [{ to: "/purchasing", label: "Vendors & POs", icon: Truck, ownerOnly: true }] },
  {
    group: "Finance", items: [
      { to: "/expenses", label: "Expenses", icon: Wallet },
      { to: "/accounting", label: "Accounting", icon: Landmark, ownerOnly: true },
      { to: "/reports", label: "Reports", icon: BarChart3, ownerOnly: true },
    ],
  },
  {
    group: "AI", items: [
      { to: "/assistant", label: "AI Assistant", icon: Sparkles, ownerOnly: true },
      { to: "/purchase-ai", label: "AI Purchase", icon: Brain, ownerOnly: true },
    ],
  },
  {
    group: "Admin", items: [
      { to: "/branches", label: "Branches", icon: Building2, ownerOnly: true },
      { to: "/config", label: "Master data", icon: Settings2, ownerOnly: true },
      { to: "/compliance", label: "Compliance", icon: ShieldCheck, ownerOnly: true },
      { to: "/admin", label: "Users & Audit", icon: UserCog, ownerOnly: true },
    ],
  },
];

const TITLES: Record<string, string> = {
  "/": "Consolidated Dashboard", "/pos": "POS Billing", "/invoices": "Invoices",
  "/returns": "Sales Returns", "/customers": "Farmers / Customers", "/field-visits": "Field visits", "/products": "Products",
  "/stock": "Stock on Hand", "/transfers": "Stock Transfers", "/purchasing": "Purchasing",
  "/accounting": "Accounting & Finance", "/expenses": "Expenses", "/reports": "Reports & Analytics",
  "/assistant": "AI Business Assistant", "/purchase-ai": "AI Purchase Recommendations",
  "/compliance": "Compliance & Statutory", "/admin": "Users & Audit Trail", "/branches": "Branches",
  "/config": "Master data",
};

function Sidebar({ open, close }: { open: boolean; close: () => void }) {
  const { user, logout } = useAuth();
  const owner = isOwner(user);
  const initials = (user?.full_name || "U").split(" ").map((s: string) => s[0]).slice(0, 2).join("");
  return (
    <>
      <div className={`overlay ${open ? "show" : ""}`} onClick={close} />
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-logo"><Leaf size={22} /></div>
          <div>
            <div className="brand-name">SKAC</div>
            <div className="brand-sub">AGRI CLINIC ERP</div>
          </div>
        </div>
        {NAV.map((g) => {
          const items = g.items.filter((it) => owner || !it.ownerOnly);
          if (items.length === 0) return null;
          return (
            <div className="nav-group" key={g.group}>
              <div className="nav-group-label">{g.group}</div>
              {items.map((it) => (
                <NavLink key={it.to} to={it.to} end={it.to === "/"} className="nav-link" onClick={close}>
                  <it.icon size={18} /> {it.label}
                </NavLink>
              ))}
            </div>
          );
        })}
        <div className="sidebar-user">
          <div className="avatar">{initials}</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ color: "#fff", fontWeight: 600, fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{user?.full_name}</div>
            <div style={{ fontSize: 11, color: "#86efac", textTransform: "capitalize" }}>{user?.role}</div>
          </div>
          <button className="icon-btn" title="Logout" onClick={logout} style={{ background: "rgba(255,255,255,.12)", border: "none", color: "#fff" }}>
            <LogOut size={16} />
          </button>
        </div>
      </aside>
    </>
  );
}

function Guard({ path, children }: { path: string; children: JSX.Element }) {
  const { user } = useAuth();
  if (!canAccessPath(user, path)) return <Navigate to={homePath(user)} replace />;
  return children;
}

export default function App() {
  const { user, loading } = useAuth();
  const [open, setOpen] = useState(false);
  const loc = useLocation();

  useEffect(() => {
    if (user) prefetchMasters().catch(() => {});
  }, [user?.id]);

  if (loading) return <div className="loading">Loading…</div>;
  if (!user) return <Login />;

  const title = TITLES[loc.pathname] ?? "SKAC";

  return (
    <div className="layout">
      <Sidebar open={open} close={() => setOpen(false)} />
      <div className="main">
        <header className="topbar">
          <button className="icon-btn hamburger" onClick={() => setOpen(true)}><Menu size={20} /></button>
          <h1>{title}</h1>
          <div className="topbar-actions">
            <span className="badge badge-success">● Live</span>
          </div>
        </header>
        <div className="content">
          <Routes>
            <Route path="/" element={<Guard path="/"><Dashboard /></Guard>} />
            <Route path="/pos" element={<Guard path="/pos"><POS /></Guard>} />
            <Route path="/invoices" element={<Guard path="/invoices"><Invoices /></Guard>} />
            <Route path="/returns" element={<Guard path="/returns"><Returns /></Guard>} />
            <Route path="/customers" element={<Guard path="/customers"><Customers /></Guard>} />
            <Route path="/field-visits" element={<Guard path="/field-visits"><FieldVisits /></Guard>} />
            <Route path="/products" element={<Guard path="/products"><Products /></Guard>} />
            <Route path="/stock" element={<Guard path="/stock"><Stock /></Guard>} />
            <Route path="/transfers" element={<Guard path="/transfers"><Transfers /></Guard>} />
            <Route path="/purchasing" element={<Guard path="/purchasing"><Purchasing /></Guard>} />
            <Route path="/expenses" element={<Guard path="/expenses"><Expenses /></Guard>} />
            <Route path="/accounting" element={<Guard path="/accounting"><Accounting /></Guard>} />
            <Route path="/reports" element={<Guard path="/reports"><Reports /></Guard>} />
            <Route path="/assistant" element={<Guard path="/assistant"><Assistant /></Guard>} />
            <Route path="/purchase-ai" element={<Guard path="/purchase-ai"><PurchaseAI /></Guard>} />
            <Route path="/compliance" element={<Guard path="/compliance"><Compliance /></Guard>} />
            <Route path="/branches" element={<Guard path="/branches"><Branches /></Guard>} />
            <Route path="/config" element={<Guard path="/config"><Config /></Guard>} />
            <Route path="/admin" element={<Guard path="/admin"><Admin /></Guard>} />
            <Route path="*" element={<Navigate to={homePath(user)} replace />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}
