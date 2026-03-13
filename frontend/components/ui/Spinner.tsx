/**
 * Loading spinner component.
 */

interface Props {
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function Spinner({ size = "md", className = "" }: Props) {
  const sizeClasses = {
    sm: "h-4 w-4 border-2",
    md: "h-8 w-8 border-2",
    lg: "h-12 w-12 border-4",
  };

  return (
    <div
      role="status"
      aria-label="Loading"
      className={`animate-spin rounded-full border-slate-600 border-t-blue-500 ${sizeClasses[size]} ${className}`}
    />
  );
}
