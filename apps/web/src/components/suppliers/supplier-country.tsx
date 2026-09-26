import { CountryFlag } from '#/components/fields/country-flag'
import { findCountry } from '#/lib/format/countries'

/** A supplier's country as its flag and name; the code when the name is unknown. */
export function SupplierCountry({ code }: { code: string | null }) {
  if (!code) {
    return <span className="text-muted-foreground">—</span>
  }
  const name = findCountry(code)?.name ?? code.toUpperCase()
  return (
    <span className="flex min-w-0 items-center gap-2">
      <CountryFlag country={code} />
      <span className="truncate">{name}</span>
    </span>
  )
}
