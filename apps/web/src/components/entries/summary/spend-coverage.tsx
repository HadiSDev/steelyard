import * as React from 'react'
import { Card, Progress, Skeleton } from '#/components/ui'
import { formatCount, formatMoney, toNumber } from '#/lib/format/format'
import type { SpendCoverageRow } from '#/lib/api/types'
import { LineMix } from './line-mix'

const percentFormatter = new Intl.NumberFormat('en-GB', {
  style: 'percent',
  maximumFractionDigits: 0,
})

/** The categorized share of posted spend, or null when nothing was posted to compare with. */
export function categorizedShare(row: SpendCoverageRow): number | null {
  const posted = toNumber(row.posted_spend)
  if (posted <= 0) {
    return null
  }
  return toNumber(row.categorized_spend) / posted
}

function formatShare(share: number): string {
  if (share > 0 && share < 0.01) {
    return '<1%'
  }
  return percentFormatter.format(share)
}

function Metric({
  caption,
  value,
  children,
}: {
  caption: string
  value: React.ReactNode
  children: React.ReactNode
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
        {value}
      </div>
      <div className="text-sm text-muted-foreground">{children}</div>
    </section>
  )
}

function vouchersText(row: SpendCoverageRow): string {
  const vouchers = `${formatCount(row.voucher_count)} voucher${row.voucher_count === 1 ? '' : 's'}`
  if (row.unconverted_vouchers === 0) {
    return vouchers
  }
  return `${vouchers} · ${formatCount(row.unconverted_vouchers)} not converted`
}

function CoverageCard({
  row,
  showCurrency,
}: {
  row: SpendCoverageRow
  showCurrency: boolean
}) {
  const share = categorizedShare(row)
  const suffix = showCurrency ? ` · ${row.currency}` : ''

  return (
    <Card className="grid divide-y divide-border p-0 md:grid-cols-3 md:divide-x md:divide-y-0">
      <Metric
        caption={`Posted spend${suffix}`}
        value={formatMoney(row.posted_spend, row.currency)}
      >
        {vouchersText(row)}
      </Metric>
      <Metric
        caption={`Categorized spend${suffix}`}
        value={formatMoney(row.categorized_spend, row.currency)}
      >
        {share === null ? (
          'No posted spend to compare with'
        ) : (
          <div className="flex flex-col gap-2">
            <span>{formatShare(share)} of posted spend</span>
            <Progress
              aria-label="Share of posted spend categorized"
              value={Math.min(100, Math.round(share * 100))}
            />
          </div>
        )}
      </Metric>
      <Metric
        caption={`Lines categorized${suffix}`}
        value={
          <>
            {formatCount(row.categorized_lines)}
            <span className="text-base font-medium text-muted-foreground">
              {' '}
              of {formatCount(row.line_count)}
            </span>
          </>
        }
      >
        {row.line_count === 0 ? 'No lines yet' : <LineMix row={row} />}
      </Metric>
    </Card>
  )
}

function CoverageSkeleton() {
  return (
    <Card
      data-testid="spend-coverage-loading"
      className="grid divide-y divide-border p-0 md:grid-cols-3 md:divide-x md:divide-y-0"
    >
      {[0, 1, 2].map((index) => (
        <div key={index} className="flex flex-col gap-2 px-5 py-4">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-36" />
          <Skeleton className="h-4 w-full" />
        </div>
      ))}
    </Card>
  )
}

export interface SpendCoverageProps {
  /** One row per base currency; undefined until first loaded. */
  rows: Array<SpendCoverageRow> | undefined
}

/** Posted spend against how much of it, and how many lines, have been categorized. */
export function SpendCoverage({ rows }: SpendCoverageProps) {
  if (rows === undefined) {
    return <CoverageSkeleton />
  }
  const listed = rows.filter((row) => row.voucher_count > 0)
  if (listed.length === 0) {
    return null
  }
  return (
    <div className="flex flex-col gap-3">
      {listed.map((row) => (
        <CoverageCard
          key={row.currency}
          row={row}
          showCurrency={listed.length > 1}
        />
      ))}
    </div>
  )
}
