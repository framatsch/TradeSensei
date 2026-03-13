/**
 * Page header component with title and optional subtitle.
 */

interface Props {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}

export function PageHeader({ title, subtitle, children }: Props) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">{title}</h1>
        {subtitle && (
          <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
        )}
      </div>
      {children && <div className="flex items-center gap-3">{children}</div>}
    </div>
  );
}
