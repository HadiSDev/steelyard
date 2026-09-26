"""Prompt text shared by the text and vision extraction paths."""

SUPPLIER_WEBSITE = (
    "If the document prints the supplier's own website — usually in the header, "
    "the footer or beside its address — report it as printed. Do not report the "
    "buyer's website, a payment portal, or an email address as the supplier's "
    "website, and leave it null when none is printed."
)

TOTALS_BLOCK_CHARGES = (
    "A charge printed in or beside the totals block — shipping, freight, "
    "postage, packing, handling, a payment or card fee, a surcharge — is a line "
    "item like any other, even though it sits outside the line table. Return it "
    "as a line, named as the document names it. Do NOT return a discount, a "
    "rebate or a promotion as a line, and do not return the totals themselves "
    "(subtotal, VAT, total) as lines: those have fields of their own."
)
