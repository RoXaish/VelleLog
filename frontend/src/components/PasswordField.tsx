import React, { useState } from 'react';

interface PasswordFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  error?: string;
  autoComplete: string;
  disabled?: boolean;
}

const EyeIcon: React.FC<{ crossed: boolean }> = ({ crossed }) => (
  <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
    <path
      d="M2.5 10C4.2 6.6 6.9 4.8 10 4.8C13.1 4.8 15.8 6.6 17.5 10C15.8 13.4 13.1 15.2 10 15.2C6.9 15.2 4.2 13.4 2.5 10Z"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinejoin="round"
    />
    <circle cx="10" cy="10" r="2.4" stroke="currentColor" strokeWidth="1.4" />
    {crossed && (
      <path
        d="M4 16L16 4"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    )}
  </svg>
);

export const PasswordField: React.FC<PasswordFieldProps> = ({
  id,
  label,
  value,
  onChange,
  error,
  autoComplete,
  disabled = false,
}) => {
  const [visible, setVisible] = useState(false);
  const errorId = error ? `${id}-error` : undefined;

  return (
    <div className={`field${error ? ' field--invalid' : ''}`}>
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      <div className="field__control">
        <input
          id={id}
          className="field__input"
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          disabled={disabled}
          required
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId}
        />
        <button
          type="button"
          className="field__toggle"
          onClick={() => setVisible((current) => !current)}
          aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`}
          aria-pressed={visible}
          disabled={disabled}
        >
          <EyeIcon crossed={visible} />
        </button>
      </div>
      {error && (
        <p id={errorId} className="field__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};
