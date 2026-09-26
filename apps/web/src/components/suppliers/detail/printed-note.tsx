import { TriangleAlert } from 'lucide-react'

function normalized(value: string): string {
  return value.replace(/\s+/g, '').toUpperCase()
}

export type PrintedComparison = 'none' | 'agrees' | 'only-printed' | 'differs'

/** How what the supplier's invoices print compares with what the ERP holds. */
export function comparePrinted(
  erp: string | null,
  printed: string | null,
): PrintedComparison {
  if (!printed) {
    return 'none'
  }
  if (!erp) {
    return 'only-printed'
  }
  return normalized(erp) === normalized(printed) ? 'agrees' : 'differs'
}

export interface PrintedNoteProps {
  erp: string | null
  printed: string | null
  /** How to say the printed value, such as a country's name for its code. */
  describe?: (value: string) => string
}

/** A note under an ERP fact: where it came from the invoices, or where the invoices disagree. */
export function PrintedNote({
  erp,
  printed,
  describe = (value) => value,
}: PrintedNoteProps) {
  const comparison = comparePrinted(erp, printed)
  if (comparison === 'only-printed') {
    return <p className="text-xs text-muted-foreground">From its invoices</p>
  }
  if (comparison !== 'differs' || printed === null) {
    return null
  }
  return (
    <p className="flex items-start gap-1 text-xs text-warning">
      <TriangleAlert aria-hidden="true" className="mt-px size-3.5 shrink-0" />
      <span>
        Its invoices say {describe(printed)}; your ERP may be out of date.
      </span>
    </p>
  )
}
