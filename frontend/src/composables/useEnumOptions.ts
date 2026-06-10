/**
 * Parse enum option strings stored in SurveyVar.values.
 *
 * Format per list entry:
 *   "value"           → { value: "value", label: "value" }
 *   "value|My Label"  → { value: "value", label: "My Label" }
 *
 * Backward-compatible: plain values without pipe work as before.
 */
export interface EnumOption {
  value: string
  label: string
}

export function parseEnumOption(raw: string): EnumOption {
  const idx = raw.indexOf('|')
  if (idx === -1) {
    const v = raw.trim()
    return { value: v, label: v }
  }
  return {
    value: raw.slice(0, idx).trim(),
    label: raw.slice(idx + 1).trim(),
  }
}

export function parseEnumOptions(raws: string[]): EnumOption[] {
  return raws.map(parseEnumOption).filter(o => o.value)
}

/** Convert EnumOption[] back to the pipe-separated string for textarea display. */
export function serializeEnumOption(opt: EnumOption): string {
  return opt.label && opt.label !== opt.value
    ? `${opt.value}|${opt.label}`
    : opt.value
}
