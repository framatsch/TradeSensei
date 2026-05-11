import React from 'react';
import { AnnotationDefinitionResponse } from '@/lib/api';

export interface AnnotationInputProps {
  definition: AnnotationDefinitionResponse;
  value: string | number | boolean | null;
  onChange: (value: string | number | boolean | null) => void;
  disabled?: boolean;
}

export function AnnotationInput({ definition, value, onChange, disabled = false }: AnnotationInputProps) {
  const { type, scale_labels, name, description } = definition;

  switch (type) {
    case 'int':
    case 'float': {
      const min = scale_labels?.min as number | undefined;
      const max = scale_labels?.max as number | undefined;
      const step = type === 'int' ? 1 : 'any';

      return (
        <div className="flex flex-col space-y-1">
          <label className="text-sm font-medium text-foreground">{name}</label>
          {description && <p className="text-xs text-muted-foreground">{description}</p>}
          <input
            type="number"
            value={value !== null && value !== undefined ? Number(value) : ''}
            onChange={(e) => {
              if (e.target.value === '') {
                onChange(null);
              } else {
                onChange(type === 'int' ? parseInt(e.target.value, 10) : parseFloat(e.target.value));
              }
            }}
            disabled={disabled}
            min={min}
            max={max}
            step={step}
            className="w-full rounded border border-border bg-secondary px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
          />
        </div>
      );
    }
    case 'bool': {
      const boolValue = Boolean(value);
      return (
        <div className="flex items-center space-x-3">
          <input
            type="checkbox"
            checked={boolValue}
            onChange={(e) => onChange(e.target.checked)}
            disabled={disabled}
            className="h-4 w-4 rounded border-border text-primary focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
          />
          <div className="flex flex-col">
            <label className="text-sm font-medium text-foreground">{name}</label>
            {description && <p className="text-xs text-muted-foreground">{description}</p>}
          </div>
        </div>
      );
    }
    case 'string_enum': {
      const options = (scale_labels?.options as string[]) || [];
      const hasOptions = options.length > 0;

      return (
        <div className="flex flex-col space-y-1">
          <label className="text-sm font-medium text-foreground">{name}</label>
          {description && <p className="text-xs text-muted-foreground">{description}</p>}
          <select
            value={value !== null && value !== undefined ? String(value) : ''}
            onChange={(e) => {
              if (e.target.value === '') {
                onChange(null);
              } else {
                onChange(e.target.value);
              }
            }}
            disabled={disabled || !hasOptions}
            className="w-full rounded border border-border bg-secondary px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50 transition-colors appearance-none"
          >
            <option value="">{hasOptions ? 'Select an option...' : 'No options defined'}</option>
            {options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
      );
    }
    default:
      return null;
  }
}
