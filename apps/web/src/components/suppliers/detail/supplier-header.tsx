import { ArrowLeft, ExternalLink, Receipt } from 'lucide-react'
import { Button, IconButton } from '#/components/ui'
import type { VendorDetailRead } from '#/lib/api/types'
import { SupplierCountry } from '../supplier-country'

const DESCRIPTION_SOURCES: Record<string, string> = {
  web: 'Researched from the web',
  erp: 'From your ERP',
  human: 'Written by a person',
}

/** The website's host, as a reader would say it. */
export function websiteLabel(website: string): string {
  try {
    return new URL(website).hostname.replace(/^www\./, '')
  } catch {
    return website
  }
}

function Fact({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <dt className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
        {label}
      </dt>
      <dd className="min-w-0 text-sm">{children}</dd>
    </div>
  )
}

export interface SupplierHeaderProps {
  supplier: VendorDetailRead
  onBack: () => void
  onViewLines: () => void
}

/** Who the supplier is: its name, country, VAT number, website and what it sells. */
export function SupplierHeader({
  supplier,
  onBack,
  onViewLines,
}: SupplierHeaderProps) {
  const source = supplier.description_source
    ? DESCRIPTION_SOURCES[supplier.description_source]
    : undefined

  return (
    <header className="flex flex-col gap-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <IconButton aria-label="Back to suppliers" onClick={onBack}>
            <ArrowLeft className="size-4" />
          </IconButton>
          <h1 className="min-w-0 font-display text-2xl font-semibold tracking-tight break-words">
            {supplier.name}
          </h1>
        </div>
        <Button onClick={onViewLines}>
          <Receipt className="size-4" />
          View spend lines
        </Button>
      </div>

      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Fact label="Country">
          <SupplierCountry code={supplier.country_code} />
        </Fact>
        <Fact label="VAT number">
          {supplier.vat_number ? (
            <span className="font-mono tabular-nums break-all">
              {supplier.vat_number}
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
        </Fact>
        <Fact label="Website">
          {supplier.website ? (
            <a
              href={supplier.website}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex max-w-full items-center gap-1.5 font-medium text-primary hover:underline"
            >
              <span className="truncate">{websiteLabel(supplier.website)}</span>
              <ExternalLink aria-hidden="true" className="size-3.5 shrink-0" />
            </a>
          ) : (
            <span className="text-muted-foreground">Not known</span>
          )}
        </Fact>
      </dl>

      <section aria-label="What they sell" className="flex flex-col gap-1">
        <h2 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          What they sell
        </h2>
        {supplier.description ? (
          <p className="max-w-prose text-sm leading-relaxed">
            {supplier.description}
          </p>
        ) : (
          <p className="text-sm text-muted-foreground">Not described yet.</p>
        )}
        {supplier.description && source ? (
          <p className="text-xs text-muted-foreground">{source}</p>
        ) : null}
      </section>
    </header>
  )
}
