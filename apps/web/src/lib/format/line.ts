/** What to call a line: its item name, else its description; null when it has neither. */
export function lineName(line: {
  item_name: string | null
  description: string | null
}): string | null {
  const name = line.item_name?.trim()
  if (name) {
    return name
  }
  const description = line.description?.trim()
  if (description) {
    return description
  }
  return null
}
