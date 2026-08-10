export function formatDualValueLabel(
  primary: string | null | undefined,
  secondary: string | null | undefined,
  formatter: (val: string) => string,
  secondaryLabel: string = "raw"
): string {
  if (!primary) return "—";
  
  const formattedPrimary = formatter(primary);
  
  if (!secondary) return formattedPrimary;
  
  const formattedSecondary = formatter(secondary);
  
  // Parse numerically to avoid string differences like "150" vs "150.0"
  const numPrimary = parseFloat(primary);
  const numSecondary = parseFloat(secondary);
  
  // If numerically equal (or both NaN), treat as equal
  if (numPrimary === numSecondary || (isNaN(numPrimary) && isNaN(numSecondary))) {
    return formattedPrimary;
  }
  
  // Fallback to string comparison just in case
  if (formattedPrimary === formattedSecondary) {
    return formattedPrimary;
  }
  
  return `${formattedPrimary} (${secondaryLabel}: ${formattedSecondary})`;
}

export function formatCurrency(value: string): string {
  return `$${Number(value).toFixed(2)}`;
}

export function formatPriceLabel(adjustedPrice: string, rawPrice: string): string {
  return formatDualValueLabel(adjustedPrice, rawPrice, formatCurrency);
}
