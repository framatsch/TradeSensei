export function formatSplitRatio(ratioStr: string): string {
  const ratio = parseFloat(ratioStr);
  if (isNaN(ratio) || ratio <= 0) return ratioStr;

  // Common fractions to ratios
  const tolerance = 0.0001;
  for (let denominator = 1; denominator <= 1000; denominator++) {
    const numerator = ratio * denominator;
    if (Math.abs(numerator - Math.round(numerator)) < tolerance) {
      return `${Math.round(numerator)}:${denominator}`;
    }
  }

  // Fallback
  return ratioStr;
}
