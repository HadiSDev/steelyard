import { Card } from '#/components/ui'
import { formatCount, formatDay, formatMoney } from '#/lib/format/format'
import type { VendorDetailRead } from '#/lib/api/types'

function Figure({
  caption,
  children,
  note,
}: {
  caption: string
  children: React.ReactNode
  note?: React.ReactNode
}) {
  return (
    <section
      aria-label={caption}
      className="flex min-w-0 flex-col gap-1 px-5 py-4"
    >
      <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
        {caption}
      </h3>
      <div className="font-display text-2xl font-semibold tracking-tight tabular-nums">
        {children}
      </div>
      {note ? (
        <div className="text-sm text-muted-foreground">{note}</div>
      ) : null}
    </section>
  )
}

function unconvertedNote(supplier: VendorDetailRead): string | undefined {
  const unconverted = supplier.spend.reduce(
    (sum, entry) => sum + entry.unconverted_count,
    0,
  )
  if (unconverted === 0) {
    return undefined
  }
  return `${formatCount(unconverted)} invoice${unconverted === 1 ? '' : 's'} not converted`
}

/** What the organization has spent with the supplier, and over how long. */
export function SupplierFigures({ supplier }: { supplier: VendorDetailRead }) {
  return (
    <Card className="grid divide-y divide-border p-0 sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-4 lg:divide-x">
      <Figure caption="Spend, net of VAT" note={unconvertedNote(supplier)}>
        {supplier.spend.length === 0 ? (
          <span className="text-muted-foreground">—</span>
        ) : (
          <span className="flex flex-col">
            {supplier.spend.map((entry) => (
              <span key={entry.currency ?? 'none'}>
                {formatMoney(entry.amount, entry.currency)}
              </span>
            ))}
          </span>
        )}
      </Figure>
      <Figure caption="Invoices">{formatCount(supplier.invoice_count)}</Figure>
      <Figure caption="First invoice">
        {formatDay(supplier.first_invoice_date)}
      </Figure>
      <Figure caption="Last invoice">
        {formatDay(supplier.last_invoice_date)}
      </Figure>
    </Card>
  )
}
