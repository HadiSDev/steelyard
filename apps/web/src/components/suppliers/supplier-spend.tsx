import { formatCount, formatMoney } from '#/lib/format/format'
import type { VendorSpendRead } from '#/lib/api/types'

/** A supplier's spend, one amount per base currency, noting invoices left unconverted. */
export function SupplierSpend({ spend }: { spend: Array<VendorSpendRead> }) {
  if (spend.length === 0) {
    return <span className="text-muted-foreground">—</span>
  }
  return (
    <div className="flex flex-col items-end gap-0.5">
      {spend.map((entry) => (
        <span
          key={entry.currency ?? 'none'}
          className="flex flex-col items-end"
        >
          <span className="font-mono tabular-nums">
            {formatMoney(entry.amount, entry.currency)}
          </span>
          {entry.unconverted_count > 0 ? (
            <span className="text-xs text-muted-foreground">
              {formatCount(entry.unconverted_count)} not converted
            </span>
          ) : null}
        </span>
      ))}
    </div>
  )
}
