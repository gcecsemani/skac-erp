import { useEffect, useState } from "react";
import { Check, Eye, MapPin, Plus, Trash2, X } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { isOwner } from "../roles";
import { Badge, BranchSelect, Card, Field, Loading, Modal, PageHeader, SearchInput, SearchSelect, Table } from "../components/ui";
import * as V from "../validate";

function MapPreview({ lat, lng, accuracy }: { lat: number; lng: number; accuracy?: number | null }) {
  const pad = 0.012;
  const src = `https://www.openstreetmap.org/export/embed.html?bbox=${lng - pad}%2C${lat - pad * 0.7}%2C${lng + pad}%2C${lat + pad * 0.7}&layer=mapnik&marker=${lat}%2C${lng}`;
  const maps = `https://www.google.com/maps?q=${lat},${lng}`;
  const weak = accuracy != null && accuracy > 80;
  return (
    <div>
      <iframe title="Field location" className="map-frame" src={src} loading="lazy" />
      <div className="row" style={{ justifyContent: "space-between", marginTop: 8, flexWrap: "wrap", gap: 8 }}>
        <span className="muted" style={{ fontSize: 12 }}>
          {lat.toFixed(6)}, {lng.toFixed(6)}
          {accuracy != null ? ` · GPS ±${Math.round(accuracy)} m` : ""}
          {weak ? " · weak GPS — check this pin" : ""}
        </span>
        <a href={maps} target="_blank" rel="noreferrer" className="muted" style={{ fontSize: 12, color: "var(--brand-600)" }}>
          Open in Google Maps
        </a>
      </div>
    </div>
  );
}

export default function FieldVisits() {
  const { user } = useAuth();
  const owner = isOwner(user);
  const [rows, setRows] = useState<any[] | null>(null);
  const [branches, setBranches] = useState<any[]>([]);
  const [staff, setStaff] = useState<any[]>([]);
  const [farmers, setFarmers] = useState<any[]>([]);
  const [status, setStatus] = useState("open");
  const [branchId, setBranchId] = useState(0);
  const [q, setQ] = useState("");
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<any | null>(null);
  const [photoUrls, setPhotoUrls] = useState<{ id: number; url: string }[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [gpsBusy, setGpsBusy] = useState(false);
  const [form, setForm] = useState<any>({});

  const load = () => {
    api.fieldVisits({
      status: status || undefined,
      branchId: branchId || undefined,
      search: q.trim() || undefined,
    }).then(setRows).catch(() => setRows([]));
  };
  useEffect(() => {
    api.branches().then((b) => { setBranches(b); }).catch(() => {});
    api.fieldVisitStaff().then(setStaff).catch(() => setStaff([]));
  }, []);
  useEffect(() => { load(); }, [status, branchId, q]);

  const searchFarmers = (needle: string) => {
    api.customers(needle || undefined, 40).then(setFarmers).catch(() => {});
  };

  const captureGps = (onErr?: (m: string) => void) => {
    if (!navigator.geolocation) {
      onErr?.("This device cannot capture GPS.");
      return;
    }
    setGpsBusy(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setForm((f: any) => ({
          ...f,
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          gps_accuracy: pos.coords.accuracy,
        }));
        setGpsBusy(false);
      },
      () => {
        setGpsBusy(false);
        onErr?.("Allow location access while you are in the field so the shop can verify this visit.");
      },
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 },
    );
  };

  const openNew = () => {
    setErr("");
    setFiles([]);
    setForm({
      branch_id: branches[0]?.id || "",
      visited_by_user_id: user?.id,
      customer_id: "",
      farmer_name: "",
      farmer_phone: "",
      village: "",
      complaint_notes: "",
      prescription_notes: "",
      latitude: null,
      longitude: null,
      gps_accuracy: null,
    });
    setOpen(true);
    searchFarmers("");
    captureGps(setErr);
  };

  const pickFarmer = (id: number | "") => {
    const c = farmers.find((f) => f.id === id);
    setForm((f: any) => ({
      ...f,
      customer_id: id,
      farmer_name: c?.name || f.farmer_name,
      farmer_phone: c?.phone || f.farmer_phone,
      village: c?.village || f.village,
    }));
  };

  const submit = async () => {
    setErr("");
    const msg = V.firstError(
      form.branch_id ? null : "Select a branch.",
      V.minLen(form.farmer_name, "Farmer name", 2),
      form.latitude && form.longitude ? null : "Capture GPS in the field before saving.",
      V.minLen(form.complaint_notes, "Crop / complaint notes", 5),
    );
    if (msg) { setErr(msg); return; }
    setSaving(true);
    try {
      const created = await api.createFieldVisit({
        branch_id: Number(form.branch_id),
        visited_by_user_id: Number(form.visited_by_user_id || user?.id),
        customer_id: form.customer_id ? Number(form.customer_id) : null,
        farmer_name: form.farmer_name.trim(),
        farmer_phone: form.farmer_phone || null,
        village: form.village || null,
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        gps_accuracy: form.gps_accuracy != null ? Number(form.gps_accuracy) : null,
        complaint_notes: form.complaint_notes,
        prescription_notes: form.prescription_notes || null,
      });
      if (files.length) await api.uploadVisitPhotos(created.id, files);
      setOpen(false);
      load();
    } catch (e: any) { setErr(e.message); }
    finally { setSaving(false); }
  };

  const loadPhotos = async (visit: any) => {
    const urls: { id: number; url: string }[] = [];
    for (const p of visit.photos || []) {
      try {
        const blob = await api.visitPhotoBlob(visit.id, p.id);
        urls.push({ id: p.id, url: URL.createObjectURL(blob) });
      } catch { /* skip broken files */ }
    }
    setPhotoUrls((prev) => {
      prev.forEach((p) => URL.revokeObjectURL(p.url));
      return urls;
    });
  };

  const openView = async (row: any) => {
    const fresh = await api.fieldVisit(row.id).catch(() => row);
    setView(fresh);
    await loadPhotos(fresh);
  };

  const closeView = () => {
    setPhotoUrls((prev) => {
      prev.forEach((p) => URL.revokeObjectURL(p.url));
      return [];
    });
    setView(null);
  };

  const deleteOnePhoto = async (photoId: number) => {
    if (!view || !confirm("Delete this photo from disk?")) return;
    try {
      const updated = await api.deleteVisitPhoto(view.id, photoId);
      setView(updated);
      await loadPhotos(updated);
      load();
    } catch (e: any) { alert(e.message); }
  };

  const deleteAllPhotos = async () => {
    if (!view || !confirm("Delete all photos for this visit? This frees disk space and cannot be undone.")) return;
    try {
      const updated = await api.deleteVisitPhotos(view.id);
      setView(updated);
      await loadPhotos(updated);
      load();
    } catch (e: any) { alert(e.message); }
  };

  const resolve = async (kind: "complete" | "cancel") => {
    if (!view) return;
    const note = kind === "cancel"
      ? prompt("Why cancel? (farmer did not come)")
      : prompt("Note (optional)", "Farmer came and took the order");
    if (kind === "cancel" && note === null) return;
    try {
      const updated = kind === "complete"
        ? await api.completeFieldVisit(view.id, note || undefined)
        : await api.cancelFieldVisit(view.id, note || undefined);
      setView(updated);
      load();
    } catch (e: any) { alert(e.message); }
  };

  if (!rows) return <Loading />;
  const tone = (s: string) => (s === "completed" ? "success" : s === "cancelled" ? "danger" : "warn");

  return (
    <div>
      <PageHeader
        title="Field visits"
        subtitle="Log crop-complaint visits with GPS. Shop staff complete the request when the farmer comes for the order — or cancel if they do not."
        actions={<button className="btn btn-primary" onClick={openNew}><Plus size={16} /> Log visit</button>}
      />
      <Card>
        <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10 }}>
          <SearchInput value={q} onChange={setQ} placeholder="Search farmer, phone, village, visit #…" />
          <BranchSelect value={branchId} onChange={setBranchId} branches={branches} />
          {[["open", "Open"], ["completed", "Completed"], ["cancelled", "Cancelled"], ["all", "All"]].map(([k, l]) => (
            <button key={k} className={`btn btn-sm ${status === k ? "btn-primary" : "btn-ghost"}`} onClick={() => setStatus(k)}>{l}</button>
          ))}
        </div>
        <Table
          columns={[
            { key: "visit_no", label: "Visit #" },
            { key: "visit_date", label: "Date" },
            { key: "farmer_name", label: "Farmer" },
            { key: "village", label: "Village", render: (r) => r.village || "—" },
            { key: "visited_by", label: "Visited by" },
            { key: "branch_name", label: "Branch" },
            { key: "gps", label: "GPS", render: (r) => r.latitude ? <Badge tone={r.gps_accuracy > 80 ? "warn" : "success"}>Pinned</Badge> : <Badge tone="danger">Missing</Badge> },
            { key: "status", label: "Status", render: (r) => <Badge tone={tone(r.status)}>{r.status}</Badge> },
            { key: "actions", label: "", render: (r) => (
              <button className="btn btn-ghost btn-sm" title="View" onClick={() => openView(r)}><Eye size={15} /></button>
            ) },
          ]}
          rows={rows}
          empty={status === "open" ? "No open field visits waiting at the shop" : "No field visits"}
          pageSize={50}
        />
      </Card>

      {open && (
        <Modal title="Log field visit" onClose={() => setOpen(false)} wide
          footer={<>
            <button className="btn btn-ghost" onClick={() => setOpen(false)} disabled={saving}>Cancel</button>
            <button className="btn btn-primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Save visit"}</button>
          </>}>
          {err && <div className="error">{err}</div>}
          <div className="grid grid-2">
            <Field label="Branch" required>
              <select value={form.branch_id} onChange={(e) => setForm({ ...form, branch_id: e.target.value })}>
                {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </Field>
            <Field label="Who visited" required>
              {owner ? (
                <select value={form.visited_by_user_id} onChange={(e) => setForm({ ...form, visited_by_user_id: e.target.value })}>
                  {staff.map((s) => <option key={s.id} value={s.id}>{s.full_name}</option>)}
                </select>
              ) : (
                <input value={user?.full_name || ""} readOnly />
              )}
            </Field>
            <Field label="Farmer (existing)">
              <SearchSelect
                value={form.customer_id}
                options={farmers}
                placeholder="Type farmer name or phone…"
                onChange={pickFarmer}
                onQuery={searchFarmers}
                allowEmpty
                emptyLabel="New farmer (type name below)"
                getLabel={(c) => `${c.name}${c.phone ? ` · ${c.phone}` : ""}${c.village ? ` · ${c.village}` : ""}`}
              />
            </Field>
            <Field label="Farmer name" required>
              <input value={form.farmer_name} onChange={(e) => setForm({ ...form, farmer_name: e.target.value })} placeholder="Name as on the field" />
            </Field>
            <Field label="Phone"><input value={form.farmer_phone} onChange={(e) => setForm({ ...form, farmer_phone: e.target.value })} inputMode="tel" /></Field>
            <Field label="Village / field location"><input value={form.village} onChange={(e) => setForm({ ...form, village: e.target.value })} /></Field>
          </div>
          <Field label="Crop complaint / issues" required>
            <textarea rows={3} value={form.complaint_notes} onChange={(e) => setForm({ ...form, complaint_notes: e.target.value })}
              placeholder="What the farmer reported — crop, pest, deficiency, weather damage…" />
          </Field>
          <Field label="Prescribed medicine / advice">
            <textarea rows={3} value={form.prescription_notes} onChange={(e) => setForm({ ...form, prescription_notes: e.target.value })}
              placeholder="Products / dose advised so the shop can bill when the farmer comes" />
          </Field>
          <Field label="Field location (GPS)" required>
            <div className="row" style={{ marginBottom: 8 }}>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => captureGps(setErr)} disabled={gpsBusy}>
                <MapPin size={14} /> {gpsBusy ? "Getting location…" : "Capture GPS now"}
              </button>
            </div>
            {form.latitude && form.longitude
              ? <MapPreview lat={Number(form.latitude)} lng={Number(form.longitude)} accuracy={form.gps_accuracy} />
              : <p className="muted" style={{ margin: 0 }}>Stand in the farmer’s field and tap Capture GPS. Shop staff will see this pin to confirm you were there.</p>}
          </Field>
          <Field label="Photos">
            <input type="file" accept="image/*" multiple onChange={(e) => setFiles(Array.from(e.target.files || []).slice(0, 8))} />
            <p className="muted" style={{ margin: "6px 0 0" }}>Up to 8 photos (crop damage, pests, labels). JPG/PNG, 6 MB each.</p>
            {files.length > 0 && <p className="muted" style={{ margin: "6px 0 0" }}>{files.length} photo{files.length === 1 ? "" : "s"} ready to upload</p>}
          </Field>
        </Modal>
      )}

      {view && (
        <Modal title={`${view.visit_no} · ${view.farmer_name}`} onClose={closeView} wide
          footer={<>
            <button className="btn btn-ghost" onClick={closeView}>Close</button>
            {view.status === "open" && (
              <>
                <button className="btn btn-danger" onClick={() => resolve("cancel")}><X size={16} /> Cancel (farmer did not come)</button>
                <button className="btn btn-primary" onClick={() => resolve("complete")}><Check size={16} /> Complete (farmer took order)</button>
              </>
            )}
          </>}>
          <div className="row mb-16" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
            <div><div className="muted">Date</div><strong>{view.visit_date}</strong></div>
            <div><div className="muted">Visited by</div><strong>{view.visited_by}</strong></div>
            <div><div className="muted">Branch</div><strong>{view.branch_name}</strong></div>
            <div><div className="muted">Status</div><Badge tone={tone(view.status)}>{view.status}</Badge></div>
          </div>
          <p style={{ marginTop: 0 }}>
            {view.farmer_phone ? <>Phone {view.farmer_phone} · </> : null}
            {view.village || "Field"}
          </p>
          {view.latitude && view.longitude
            ? <MapPreview lat={view.latitude} lng={view.longitude} accuracy={view.gps_accuracy} />
            : <p className="muted">No GPS was captured for this visit.</p>}
          <div className="grid grid-2" style={{ marginTop: 16 }}>
            <div>
              <div className="muted">Crop complaint / issues</div>
              <p style={{ whiteSpace: "pre-wrap" }}>{view.complaint_notes || "—"}</p>
            </div>
            <div>
              <div className="muted">Prescribed medicine / advice</div>
              <p style={{ whiteSpace: "pre-wrap" }}>{view.prescription_notes || "—"}</p>
            </div>
          </div>
          {view.status !== "open" && (view.photos?.length || photoUrls.length) > 0 && (
            <div className="row" style={{ justifyContent: "space-between", marginTop: 8 }}>
              <span className="muted">Photos — delete after billing to free disk space</span>
              <button type="button" className="btn btn-ghost btn-sm" onClick={deleteAllPhotos}>
                <Trash2 size={14} /> Delete all photos
              </button>
            </div>
          )}
          {photoUrls.length > 0 && (
            <div className="photo-grid" style={{ marginTop: 8 }}>
              {photoUrls.map((p, i) => (
                <div key={p.id} className="photo-tile">
                  <a href={p.url} target="_blank" rel="noreferrer">
                    <img src={p.url} alt={`Visit photo ${i + 1}`} />
                  </a>
                  {view.status !== "open" && (
                    <button type="button" className="photo-del" title="Delete photo" onClick={() => deleteOnePhoto(p.id)}>
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          {view.status !== "open" && !(view.photos?.length) && (
            <p className="muted">Photos have been deleted. Notes and GPS are kept.</p>
          )}
          {view.status !== "open" && (
            <p className="muted" style={{ marginBottom: 0 }}>
              {view.status} by {view.resolved_by || "—"}
              {view.resolved_at ? ` · ${view.resolved_at.slice(0, 16).replace("T", " ")}` : ""}
              {view.resolution_note ? ` · ${view.resolution_note}` : ""}
            </p>
          )}
        </Modal>
      )}
    </div>
  );
}
