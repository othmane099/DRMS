'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
}

export function Switch({ checked, onChange, label, disabled }: SwitchProps) {
  return (
    <label className="flex items-center cursor-pointer">
      <div className="relative">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="sr-only"
        />
        <div
          className={cn(
            'w-10 h-6 rounded-full transition-colors',
            checked ? 'bg-black' : 'bg-gray-300',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        />
        <div
          className={cn(
            'absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform',
            checked && 'translate-x-4'
          )}
        />
      </div>
      {label && (
        <span className={cn('ml-3 text-sm', disabled && 'text-gray-400')}>
          {label}
        </span>
      )}
    </label>
  );
}
