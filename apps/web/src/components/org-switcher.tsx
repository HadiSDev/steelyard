import { useAuth } from '@clerk/tanstack-react-start'
import { useNavigate } from '@tanstack/react-router'
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxIcon,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
  ComboboxTrigger,
  Skeleton,
  cn,
  useToast,
} from '#/components/ui'
import { useOrgMemberships } from '#/lib/auth/orgs'
import type { OrgMembership } from '#/lib/auth/orgs'
import { initials } from '#/lib/format/initials'

const CHIP_CLASS =
  'flex w-full items-center gap-2.5 rounded-lg border border-border bg-muted/40 px-2 py-1.5'

/** The organization's logo, or its initials, beside its name under an "Organization" caption. */
function OrgIdentity({
  organization,
  placeholder,
}: {
  organization?: OrgMembership
  placeholder: string
}) {
  const name = organization?.name ?? placeholder
  return (
    <span className="flex min-w-0 flex-1 items-center gap-2.5">
      <Avatar className="size-8 rounded-md bg-inverted text-xs font-semibold text-inverted-foreground">
        {organization?.imageUrl ? (
          <AvatarImage src={organization.imageUrl} alt="" />
        ) : null}
        <AvatarFallback>{initials(name)}</AvatarFallback>
      </Avatar>
      <span className="flex min-w-0 flex-col text-left leading-tight">
        <span className="text-[11px] font-medium text-muted-foreground">
          Organization
        </span>
        <span className="truncate text-sm font-semibold text-foreground">
          {name}
        </span>
      </span>
    </span>
  )
}

/** Switches the active organization, or shows its name when there is only one. */
export function OrgSwitcher() {
  const { orgId } = useAuth()
  const { isLoaded, memberships, setActive } = useOrgMemberships()
  const toast = useToast()
  const navigate = useNavigate()

  const active = memberships.find((m) => m.id === orgId)

  async function handleChange(next: OrgMembership | null) {
    if (!next || !setActive || next.id === orgId) {
      return
    }
    try {
      await setActive({ organization: next.id })
      await navigate({ to: '/' })
    } catch {
      toast.add({
        title: 'Couldn’t switch organization',
        description: 'Please try again.',
      })
    }
  }

  if (!isLoaded) {
    return (
      <Skeleton
        className="h-[46px] w-full rounded-lg"
        data-testid="org-switcher-loading"
      />
    )
  }

  if (memberships.length <= 1) {
    const organization = active ?? memberships.at(0)
    return (
      <div className={CHIP_CLASS} title={organization?.name}>
        <OrgIdentity
          organization={organization}
          placeholder="No organization"
        />
      </div>
    )
  }

  return (
    <Combobox
      items={memberships}
      value={active}
      onValueChange={handleChange}
      itemToStringLabel={(m: OrgMembership) => m.name}
      isItemEqualToValue={(a: OrgMembership, b: OrgMembership) => a.id === b.id}
    >
      <ComboboxTrigger
        aria-label="Switch organization"
        className={cn(
          CHIP_CLASS,
          'h-auto cursor-pointer transition-colors hover:bg-muted',
        )}
      >
        <OrgIdentity organization={active} placeholder="Select organization" />
        <ComboboxIcon />
      </ComboboxTrigger>
      <ComboboxContent className="w-64">
        <div className="p-1">
          <ComboboxInput
            placeholder="Search organizations…"
            aria-label="Search organizations"
            hideIcon
          />
        </div>
        <ComboboxEmpty>No organizations found.</ComboboxEmpty>
        <ComboboxList>
          {(membership: OrgMembership) => (
            <ComboboxItem key={membership.id} value={membership}>
              {membership.name}
            </ComboboxItem>
          )}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  )
}
