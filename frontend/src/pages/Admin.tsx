import { useEffect, useMemo, useState } from "react";
import { UserPlus, Users as UsersIcon, History, Pencil, Trash2 } from "lucide-react";
import { api } from "../api";
import { matchesQuery } from "../format";
import { Badge, Card, Field, Loading, Modal, PageHeader, SearchInput, Table } from "../components/ui";
import * as V from "../validate";
import { ROLE_CASHIER, ROLE_OWNER } from "../roles";

export default function Admin() {
  const [tab, setTab] = useState("users");
  const [users, setUsers] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);
  const [audit, setAudit] = useState<any[]>([]);
  const [auditQ, setAuditQ] = useState("");
  const [auditAction, setAuditAction] = useState("");
  const [auditEntity, setAuditEntity] = useState("");
  const [ready, setReady] = useState(false);
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [err, setErr] = useState("");
  const emptyUser = { full_name: "", email: "", password: "", role_key: "cashier", is_active: true, branch_ids: [] as any[] };
  const [form, setForm] = useState<any>(emptyUser);

  const load = () => Promise.all([
    api.users().then(setUsers), api.roles().then(setRoles),
    api.branches().then(setBranches), api.audit().then(setAudit),
  ]);
  useEffect(() => { load().finally(() => setReady(true)); }, []);

  const auditActions = useMemo(() => [...new Set(audit.map((r) => r.action).filter(Boolean))], [audit]);
  const auditEntities = useMemo(() => [...new Set(audit.map((r) => r.entity_type).filter(Boolean))], [audit]);
  const filteredAudit = useMemo(() => audit.filter((r) => {
    if (auditAction && r.action !== auditAction) return false;
    if (auditEntity && r.entity_type !== auditEntity) return false;
    return matchesQuery(auditQ, r.created_at, r.action, r.entity_type, r.entity_id, r.actor_user_id);
  }), [audit, auditQ, auditAction, auditEntity]);

  const openCreate = () => { setEditId(null); setForm(emptyUser); setErr(""); setOpen(true); };
  const openEdit = (u: any) => {
    setEditId(u.id); setErr("");
    setForm({ full_name: u.full_name, email: u.email, password: "", role_key: u.role, is_active: u.is_active, branch_ids: (u.branch_ids || []).map(String) });
    setOpen(true);
  };
  const remove = async (u: any) => {
    if (!confirm(`Delete user "${u.full_name}"?`)) return;
    try { await api.deleteUser(u.id); await api.users().then(setUsers); } catch (e: any) { alert(e.message); }
  };

  const submit = async () => {
    setErr("");
    const errs = V.firstError(
      V.minLen(form.full_name, "Full name", 2),
      editId ? null : V.email(form.email),
      editId ? V.password(form.password, { required: false }) : V.password(form.password),
      form.role_key !== ROLE_OWNER && form.role_key !== ROLE_CASHIER ? "Role must be owner or cashier." : null,
      form.role_key === ROLE_CASHIER && form.branch_ids.length === 0 ? "Assign the cashier to at least one branch." : null,
    );
    if (errs) { setErr(errs); return; }
    try {
      if (editId) {
        const payload: any = { full_name: form.full_name, role_key: form.role_key, is_active: form.is_active, branch_ids: form.branch_ids.map(Number) };
        if (form.password) payload.password = form.password;
        await api.updateUser(editId, payload);
      } else {
        await api.createUser({ ...form, branch_ids: form.branch_ids.map(Number) });
      }
      setOpen(false); setForm(emptyUser); setEditId(null);
      await api.users().then(setUsers);
    } catch (e: any) { setErr(e.message); }
  };

  if (!ready) return <Loading />;

  return (
    <div>
      <PageHeader
        title="Users & Audit Trail"
        subtitle="Role-based access control and a full audit log for compliance"
        actions={tab === "users" && <button className="btn btn-primary" onClick={openCreate}><UserPlus size={16} /> Add User</button>}
      />
      <div className="tabs">
        {[["users", "Users & Roles"], ["audit", "Audit Log"]].map(([k, l]) => (
          <button key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => setTab(k)}>{l}</button>
        ))}
      </div>

      {tab === "users" && (
        <Card title="Users" icon={<UsersIcon size={16} />}>
          <Table
            columns={[
              { key: "full_name", label: "Name" },
              { key: "email", label: "Email" },
              { key: "role", label: "Role", render: (r) => <Badge tone="info">{r.role}</Badge> },
              { key: "branches", label: "Branches", render: (r) =>
                (r.role === ROLE_OWNER)
                  ? <span className="muted">All</span>
                  : (r.branch_names?.length ? r.branch_names.join(", ") : "—")
              },
              { key: "is_active", label: "Status", render: (r) => <Badge tone={r.is_active ? "success" : "danger"}>{r.is_active ? "active" : "disabled"}</Badge> },
              { key: "totp_enabled", label: "2FA", render: (r) => r.totp_enabled ? <Badge tone="success">on</Badge> : <Badge>off</Badge> },
              { key: "actions", label: "", render: (r) => (
                <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                  <button className="icon-btn" style={{ width: 30, height: 30 }} title="Edit" onClick={() => openEdit(r)}><Pencil size={14} /></button>
                  <button className="icon-btn" style={{ width: 30, height: 30 }} title="Delete" onClick={() => remove(r)}><Trash2 size={14} /></button>
                </div>
              ) },
            ]}
            rows={users}
          />
        </Card>
      )}

      {tab === "audit" && (
        <Card title="Audit Log" icon={<History size={16} />}>
          <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10 }}>
            <SearchInput value={auditQ} onChange={setAuditQ} placeholder="Search action, entity, ID or actor…" />
            <select value={auditAction} onChange={(e) => setAuditAction(e.target.value)} style={{ width: "auto" }}>
              <option value="">All actions</option>
              {auditActions.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
            <select value={auditEntity} onChange={(e) => setAuditEntity(e.target.value)} style={{ width: "auto" }}>
              <option value="">All entities</option>
              {auditEntities.map((e) => <option key={e} value={e}>{e.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <Table
            columns={[
              { key: "created_at", label: "When", render: (r) => r.created_at?.replace("T", " ").slice(0, 19) },
              { key: "action", label: "Action", render: (r) => <Badge tone={r.action === "create" ? "success" : r.action === "delete" ? "danger" : "info"}>{r.action}</Badge> },
              { key: "entity_type", label: "Entity" },
              { key: "entity_id", label: "ID" },
              { key: "actor_user_id", label: "Actor" },
            ]}
            rows={filteredAudit}
            empty={audit.length ? "No audit entries match the filters" : "No audit entries"}
          />
        </Card>
      )}

      {open && (
        <Modal title={editId ? "Edit User" : "Add User"} onClose={() => setOpen(false)}
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={submit}>{editId ? "Save" : "Create"}</button></>}>
          {err && <div className="error">{err}</div>}
          <div className="grid grid-2">
            <Field label="Full name" required><input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
            <Field label="Email" required><input value={form.email} disabled={!!editId} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
            <Field label={editId ? "New password (leave blank to keep)" : "Password"} required={!editId}><input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
            <Field label="Role" required>
              <select value={form.role_key} onChange={(e) => setForm({ ...form, role_key: e.target.value, branch_ids: e.target.value === ROLE_OWNER ? form.branch_ids : form.branch_ids })}>
                {(roles.length ? roles : [{ key: ROLE_OWNER, name: "Owner" }, { key: ROLE_CASHIER, name: "Cashier" }]).map((r) => <option key={r.key} value={r.key}>{r.name}</option>)}
              </select>
            </Field>
          </div>
          {editId && (
            <label className="row" style={{ gap: 8, cursor: "pointer", marginBottom: 8 }}>
              <input type="checkbox" style={{ width: "auto" }} checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
              Active
            </label>
          )}
          <Field label="Branch access">
            <select multiple value={form.branch_ids} onChange={(e) => setForm({ ...form, branch_ids: Array.from(e.target.selectedOptions).map((o) => o.value) })} style={{ height: 90 }}>
              {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
            <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
              {form.role_key === ROLE_OWNER
                ? "Owner always sees every branch — assignment is optional."
                : "Hold Ctrl/Cmd to select. A cashier only sees the assigned branch(es)."}
            </div>
          </Field>
        </Modal>
      )}
    </div>
  );
}
