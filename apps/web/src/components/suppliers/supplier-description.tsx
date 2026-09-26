import { Tooltip, TooltipContent, TooltipTrigger } from '#/components/ui'

/** What a supplier sells, on one line, with the full text on hover or focus. */
export function SupplierDescription({
  description,
}: {
  description: string | null
}) {
  if (!description) {
    return <span className="text-muted-foreground italic">Not described</span>
  }
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span
            tabIndex={0}
            className="block truncate rounded-sm text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        }
      >
        {description}
      </TooltipTrigger>
      <TooltipContent className="max-w-sm">{description}</TooltipContent>
    </Tooltip>
  )
}
