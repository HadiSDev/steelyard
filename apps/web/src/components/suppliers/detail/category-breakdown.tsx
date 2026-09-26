import { Card, CardContent, CardHeader, CardTitle, cn } from '#/components/ui'
import { formatCount, formatMoney, toNumber } from '#/lib/format/format'
import type { VendorCategorySpendRead } from '#/lib/api/types'

export const SHOWN_CATEGORIES = 6

const percentFormatter = new Intl.NumberFormat('en-GB', {
  style: 'percent',
  maximumFractionDigits: 0,
})

export interface CategoryBar {
  key: string
  label: string
  uncategorized: boolean
  amount: number
  lineCount: number
  share: number
}

export interface CurrencyBreakdown {
  currency: string | null
  total: number
  bars: Array<CategoryBar>
}

function bar(
  key: string,
  label: string,
  uncategorized: boolean,
  rows: Array<VendorCategorySpendRead>,
  total: number,
): CategoryBar {
  const amount = rows.reduce((sum, row) => sum + toNumber(row.amount), 0)
  return {
    key,
    label,
    uncategorized,
    amount,
    lineCount: rows.reduce((sum, row) => sum + row.line_count, 0),
    share: total > 0 ? amount / total : 0,
  }
}

/** The categories per base currency, largest first, with the tail folded into one "Other" bar. */
export function breakdownByCurrency(
  categories: Array<VendorCategorySpendRead>,
  shown: number = SHOWN_CATEGORIES,
): Array<CurrencyBreakdown> {
  const byCurrency = new Map<string | null, Array<VendorCategorySpendRead>>()
  for (const row of categories) {
    byCurrency.set(row.currency, [...(byCurrency.get(row.currency) ?? []), row])
  }

  return [...byCurrency.entries()].map(([currency, rows]) => {
    const total = rows.reduce((sum, row) => sum + toNumber(row.amount), 0)
    const sorted = [...rows].sort(
      (a, b) => toNumber(b.amount) - toNumber(a.amount),
    )
    const named = sorted.filter((row) => row.category_id !== null)
    const uncategorized = sorted.filter((row) => row.category_id === null)
    const bars = named
      .slice(0, shown)
      .map((row) =>
        bar(
          row.category_id ?? '',
          row.category_name ?? 'Unnamed category',
          false,
          [row],
          total,
        ),
      )
    const rest = named.slice(shown)
    if (rest.length > 0) {
      bars.push(
        bar(
          'other',
          `Other categories (${formatCount(rest.length)})`,
          false,
          rest,
          total,
        ),
      )
    }
    if (uncategorized.length > 0) {
      bars.push(
        bar('uncategorized', 'Not categorized', true, uncategorized, total),
      )
    }
    return { currency, total, bars }
  })
}

function formatShare(share: number): string {
  if (share > 0 && share < 0.01) {
    return '<1%'
  }
  return percentFormatter.format(share)
}

function CategoryRow({
  item,
  currency,
}: {
  item: CategoryBar
  currency: string | null
}) {
  return (
    <li className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span
          className={cn(
            'min-w-0 truncate',
            item.uncategorized ? 'text-muted-foreground italic' : 'font-medium',
          )}
          title={item.label}
        >
          {item.label}
        </span>
        <span className="shrink-0 font-mono tabular-nums">
          {formatMoney(item.amount, currency)}
          <span className="ml-2 inline-block w-10 text-right text-muted-foreground">
            {formatShare(item.share)}
          </span>
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <span
          className={cn(
            'block h-full rounded-full',
            item.uncategorized ? 'bg-muted-foreground/30' : 'bg-primary',
          )}
          style={{
            width: `${Math.max(item.share * 100, item.amount > 0 ? 1 : 0)}%`,
          }}
        />
      </div>
      <span className="text-xs text-muted-foreground">
        {formatCount(item.lineCount)} line{item.lineCount === 1 ? '' : 's'}
      </span>
    </li>
  )
}

/** Where the supplier's spend went, category by category. */
export function CategoryBreakdown({
  categories,
}: {
  categories: Array<VendorCategorySpendRead>
}) {
  const breakdowns = breakdownByCurrency(categories)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Spend by category</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {breakdowns.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            None of this supplier’s invoices have lines yet.
          </p>
        ) : (
          breakdowns.map((breakdown) => (
            <section
              key={breakdown.currency ?? 'none'}
              aria-label={`Spend by category in ${breakdown.currency ?? 'no currency'}`}
              className="flex flex-col gap-3"
            >
              {breakdowns.length > 1 ? (
                <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                  {breakdown.currency ?? 'No currency'}
                </h3>
              ) : null}
              <ul className="flex flex-col gap-4">
                {breakdown.bars.map((item) => (
                  <CategoryRow
                    key={item.key}
                    item={item}
                    currency={breakdown.currency}
                  />
                ))}
              </ul>
            </section>
          ))
        )}
      </CardContent>
    </Card>
  )
}
