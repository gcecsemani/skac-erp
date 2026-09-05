import type { CSSProperties } from "react";
import { Field, SearchSelect } from "./ui";
import { gstValue, modesFor, type ConfigBundle, type ConfigItem } from "../configBundle";

export function LocationFields({
  district,
  village,
  onChange,
  bundle,
  ready = true,
  required = false,
}: {
  district: string;
  village: string;
  onChange: (next: { district?: string; village?: string }) => void;
  bundle: ConfigBundle;
  ready?: boolean;
  required?: boolean;
}) {
  const districts = bundle.districts || [];
  const selected = districts.find((d) => d.name === district);
  const villages = selected?.villages || [];
  const districtMissing = !!district && !districts.some((d) => d.name === district);
  const villageMissing = !!village && !villages.some((v) => v.name === village);

  const districtOptions = districtMissing && district
    ? [{ id: `custom-${district}`, name: district }, ...districts]
    : districts;
  const villageOptions = villageMissing && village
    ? [{ id: `custom-${village}`, name: village }, ...villages]
    : villages;

  return (
    <>
      <Field label="District" required={required}>
        <SearchSelect
          value={district}
          options={districtOptions}
          disabled={!ready}
          allowEmpty
          emptyLabel={ready ? "Select district" : "Loading…"}
          placeholder={ready ? "Type to search district…" : "Loading…"}
          getId={(d) => d.name}
          onChange={(name) => onChange({ district: String(name || ""), village: "" })}
        />
      </Field>
      <Field label="Village" required={required}>
        <SearchSelect
          value={village}
          options={villageOptions}
          disabled={!ready || !district}
          allowEmpty
          emptyLabel={!district ? "Select district first" : "Select village"}
          placeholder={!district ? "Select district first" : "Type to search village…"}
          getId={(v) => v.name}
          onChange={(name) => onChange({ village: String(name || "") })}
        />
      </Field>
    </>
  );
}

export function PaymentSelect({
  value,
  onChange,
  use,
  bundle,
  allowEmpty,
  emptyLabel = "All payments",
  style,
}: {
  value: string;
  onChange: (v: string) => void;
  use: string;
  bundle: ConfigBundle;
  allowEmpty?: boolean;
  emptyLabel?: string;
  style?: CSSProperties;
}) {
  const modes = modesFor(bundle, use);
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} style={style}>
      {allowEmpty && <option value="">{emptyLabel}</option>}
      {modes.map((m) => (
        <option key={m.code} value={m.code}>{m.name}</option>
      ))}
    </select>
  );
}

export function ConfigOptions({
  items,
  valueKey = "name",
  labelKey = "name",
  current,
}: {
  items: ConfigItem[];
  valueKey?: "name" | "code";
  labelKey?: "name" | "code";
  current?: string;
}) {
  const values = items.map((i) => String(i[valueKey]));
  const missing = current && !values.includes(current);
  return (
    <>
      {missing && <option value={current}>{current}</option>}
      {items.map((i) => (
        <option key={i.id} value={String(i[valueKey])}>{String(i[labelKey])}</option>
      ))}
    </>
  );
}

export function GstSelect({
  value,
  onChange,
  bundle,
}: {
  value: string;
  onChange: (v: string) => void;
  bundle: ConfigBundle;
}) {
  const rates = bundle.gst_rates || [];
  if (!rates.length) {
    return <input type="number" value={value} onChange={(e) => onChange(e.target.value)} />;
  }
  const known = rates.some((r) => gstValue(r) === String(value));
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {!known && value !== "" && <option value={value}>{value}%</option>}
      {rates.map((r) => (
        <option key={r.id} value={gstValue(r)}>{r.name}</option>
      ))}
    </select>
  );
}
