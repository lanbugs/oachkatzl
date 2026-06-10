/**
 * Log line formatter:
 *  1. Oachkatzl internal lines ([oachkatzl], [git]) → prefix-based CSS colors
 *  2. Subprocess output (Ansible, bash, …) → ANSI escape code → HTML
 *
 * Reason: ESC (0x1B) can be lost in MongoDB → JSON → browser round-trips,
 * making ANSI unreliable for our own log messages. Prefix coloring is
 * encoding-independent and always works.
 */

// ── ANSI palette ──────────────────────────────────────────────────────────
const FG: Record<string, string> = {
  '30': '#4a4a4a', '31': '#e74c3c', '32': '#27ae60', '33': '#f39c12',
  '34': '#3498db', '35': '#9b59b6', '36': '#16a085', '37': '#bdc3c7',
  '90': '#7f8c8d', '91': '#ff6b6b', '92': '#55efc4', '93': '#fdcb6e',
  '94': '#74b9ff', '95': '#fd79a8', '96': '#00cec9', '97': '#dfe6e9',
}

function escHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

/** Strip all ANSI escape codes from a string. */
function stripAnsi(s: string): string {
  // Handle both actual ESC char and common serialized forms
  return s
    .replace(/\[[0-9;]*m/g, '')
    .replace(/\x1b\[[0-9;]*m/g, '')
    .replace(/\\u001b\[[0-9;]*m/g, '')
    .replace(/\\x1b\[[0-9;]*m/g, '')
}

/** Convert ANSI escape codes to HTML spans. */
function ansiToHtml(raw: string): string {
  // Normalize all known serialized forms of ESC to the actual char
  const normalized = raw
    .replace(/\\u001b/gi, '')
    .replace(/\\x1b/gi, '')
    .replace(/\\033/g, '')

  let out = normalized
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  let depth = 0
  out = out.replace(/\[([0-9;]*)m/g, (_, codes: string) => {
    const parts = (codes || '0').split(';').filter(Boolean)
    if (!parts.length || parts[0] === '0') {
      const close = '</span>'.repeat(depth)
      depth = 0
      return close
    }
    const styles: string[] = []
    for (const code of parts) {
      if (FG[code]) styles.push(`color:${FG[code]}`)
      if (code === '1') styles.push('font-weight:700')
      if (code === '2') styles.push('opacity:0.6')
      if (code === '4') styles.push('text-decoration:underline')
    }
    if (!styles.length) return ''
    depth++
    return `<span style="${styles.join(';')}">`
  })

  if (depth > 0) out += '</span>'.repeat(depth)
  return out
}

// ── Prefix-based coloring for Oachkatzl internal messages ──────────────────
const PREFIX_RULES: Array<{ test: (l: string) => boolean; style: string }> = [
  {
    test: l => /^\[oachkatzl\].*(error|failed|exception)/i.test(l),
    style: 'color:#e74c3c;font-weight:700',
  },
  {
    test: l => /^\[oachkatzl\].*(warn|warning)/i.test(l),
    style: 'color:#f39c12',
  },
  {
    test: l => /^\[oachkatzl\].*(success|ready|finished.*success)/i.test(l),
    style: 'color:#27ae60',
  },
  {
    test: l => l.startsWith('[oachkatzl]'),
    style: 'color:#3498db',
  },
  {
    test: l => l.startsWith('[git]'),
    style: 'color:#16a085',
  },
]

/**
 * Format a single log line for v-html rendering.
 * Internal [oachkatzl]/[git] lines → prefix color.
 * Everything else → ANSI-to-HTML conversion.
 */
export function formatLogLine(raw: string): string {
  const clean = stripAnsi(raw)   // strip any stray ANSI from internal messages

  for (const rule of PREFIX_RULES) {
    if (rule.test(clean)) {
      return `<span style="${rule.style}">${escHtml(clean)}</span>`
    }
  }

  // Subprocess output: use ANSI parser (ansible, bash, etc.)
  return ansiToHtml(raw)
}
