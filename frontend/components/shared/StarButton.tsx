import { Star } from "lucide-react";

interface StarButtonProps {
  isStarred: boolean;
  isLoading?: boolean;
  onClick: () => void;
  className?: string;
}

export function StarButton({ isStarred, isLoading, onClick, className = "" }: StarButtonProps) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-zinc-100 hover:text-zinc-900 disabled:pointer-events-none disabled:opacity-50 dark:hover:bg-zinc-800 dark:hover:text-zinc-50 h-9 w-9 ${className}`}
      onClick={onClick}
      disabled={isLoading}
      aria-label={isStarred ? "Unstar" : "Star"}
    >
      <Star
        className={`h-5 w-5 ${isStarred ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground"}`}
      />
    </button>
  );
}
