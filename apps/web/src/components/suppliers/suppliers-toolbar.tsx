import * as React from 'react'
import { Search } from 'lucide-react'
import {
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '#/components/ui'
import { CountryFlag } from '#/components/fields/country-flag'
import type { CompanyRead, SupplierFilters } from '#/lib/api/types'

const ALL = '__all__'
export const SEARCH_DELAY_MS = 300

export interface SuppliersToolbarProps {
  filters: SupplierFilters
  companies: Array<CompanyRead>
  onChange: (changes: Partial<SupplierFilters>) => void
}

/** Search by name or VAT number, and narrow to one company. */
export function SuppliersToolbar({
  filters,
  companies,
  onChange,
}: SuppliersToolbarProps) {
  const [query, setQuery] = React.useState(filters.q ?? '')

  React.useEffect(() => {
    setQuery(filters.q ?? '')
  }, [filters.q])

  React.useEffect(() => {
    const next = query.trim() === '' ? undefined : query.trim()
    if (next === filters.q) {
      return
    }
    const timer = window.setTimeout(() => {
      onChange({ q: next })
    }, SEARCH_DELAY_MS)
    return () => {
      window.clearTimeout(timer)
    }
  }, [query, filters.q, onChange])

  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="flex w-full flex-col gap-1.5 sm:w-72">
        <span className="text-xs font-medium text-muted-foreground">
          Search
        </span>
        <span className="relative">
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            type="search"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value)
            }}
            placeholder="Supplier name or VAT number"
            className="pl-9"
          />
        </span>
      </label>

      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium text-muted-foreground">
          Company
        </span>
        <Select
          value={filters.company_id ?? ''}
          onValueChange={(next: string | null) => {
            onChange({ company_id: next && next !== ALL ? next : undefined })
          }}
        >
          <SelectTrigger className="w-52">
            <SelectValue
              placeholder="All companies"
              items={companies.map((c) => ({ value: c.id, label: c.name }))}
            />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All companies</SelectItem>
            {companies.map((company) => (
              <SelectItem key={company.id} value={company.id}>
                <span className="flex min-w-0 items-center gap-2">
                  {company.country_code ? (
                    <CountryFlag country={company.country_code} />
                  ) : null}
                  <span className="min-w-0">{company.name}</span>
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </label>
    </div>
  )
}
