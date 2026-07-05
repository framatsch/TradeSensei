export function formatCurrency(value: string): string {
  return `$${Number(value).toFixed(2)}`;
}

export function formatPriceLabel(adjustedPrice: string, rawPrice: string): string {
  const adjusted = formatCurrency(adjustedPrice);
  if (Number(adjustedPrice) === Number(rawPrice)) {
    return adjusted;
  }

  return `${adjusted} (raw: ${formatCurrency(rawPrice)})`;
}
