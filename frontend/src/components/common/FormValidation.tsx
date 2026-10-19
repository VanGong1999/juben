/**
 * 表单验证组件
 * 提供实时表单验证和错误提示
 */

import React, { useState, useEffect } from 'react';
import { AlertCircle, Check, Eye, EyeOff } from 'lucide-react';
import { useI18n, translate } from '@/i18n';

export interface ValidationRule {
  /** 验证函数 */
  validate: (value: string) => boolean;
  /** 错误消息 */
  message: string;
}

export interface FieldValidation {
  /** 是否有效 */
  isValid: boolean;
  /** 错误消息 */
  error?: string;
}

/**
 * 预定义的验证规则
 */
export const ValidationRules = {
  required: (message = translate('ui.validation.required')): ValidationRule => ({
    validate: (value: string) => value.trim().length > 0,
    message,
  }),

  minLength: (min: number, message?: string): ValidationRule => ({
    validate: (value: string) => value.length >= min,
    message: message || translate('ui.validation.minLength', undefined, { count: min }),
  }),

  maxLength: (max: number, message?: string): ValidationRule => ({
    validate: (value: string) => value.length <= max,
    message: message || translate('ui.validation.maxLength', undefined, { count: max }),
  }),

  email: (message = translate('ui.validation.email')): ValidationRule => ({
    validate: (value: string) => {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return emailRegex.test(value);
    },
    message,
  }),

  password: (message = translate('ui.validation.password')): ValidationRule => ({
    validate: (value: string) => {
      const hasLetter = /[a-zA-Z]/.test(value);
      const hasNumber = /[0-9]/.test(value);
      const hasMinLength = value.length >= 8;
      return hasLetter && hasNumber && hasMinLength;
    },
    message,
  }),

  url: (message = translate('ui.validation.url')): ValidationRule => ({
    validate: (value: string) => {
      try {
        new URL(value);
        return true;
      } catch {
        return false;
      }
    },
    message,
  }),

  pattern: (pattern: RegExp, message = translate('ui.validation.pattern')): ValidationRule => ({
    validate: (value: string) => pattern.test(value),
    message,
  }),

  custom: (validate: (value: string) => boolean, message: string): ValidationRule => ({
    validate,
    message,
  }),
};

/**
 * 表单字段组件
 */
interface FormFieldProps {
  /** 字段名 */
  name: string;
  /** 标签 */
  label?: string;
  /** 类型 */
  type?: 'text' | 'email' | 'password' | 'url' | 'textarea';
  /** 占位符 */
  placeholder?: string;
  /** 值 */
  value: string;
  /** 变更回调 */
  onChange: (value: string) => void;
  /** 验证规则 */
  rules?: ValidationRule[];
  /** 是否禁用 */
  disabled?: boolean;
  /** 是否只读 */
  readOnly?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 是否立即验证 */
  validateOnChange?: boolean;
  /** 帮助文本 */
  helpText?: string;
  /** 是否显示密码切换 */
  showPasswordToggle?: boolean;
}

export function FormField({
  name,
  label,
  type = 'text',
  placeholder,
  value,
  onChange,
  rules = [],
  disabled = false,
  readOnly = false,
  className = '',
  validateOnChange = false,
  helpText,
  showPasswordToggle = type === 'password',
}: FormFieldProps) {
  const [touched, setTouched] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [validation, setValidation] = useState<FieldValidation>({
    isValid: true,
    error: undefined,
  });
  const { t } = useI18n();

  useEffect(() => {
    if (validateOnChange || touched) {
      validateField(value);
    }
  }, [value]);

  const validateField = (fieldValue: string): FieldValidation => {
    if (rules.length === 0) {
      return { isValid: true };
    }

    for (const rule of rules) {
      if (!rule.validate(fieldValue)) {
        const result = { isValid: false, error: rule.message };
        setValidation(result);
        return result;
      }
    }

    const result = { isValid: true };
    setValidation(result);
    return result;
  };

  const handleBlur = () => {
    setTouched(true);
    validateField(value);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    onChange(e.target.value);
  };

  const inputType = type === 'password' && showPassword ? 'text' : type;
  const hasError = touched && !validation.isValid;

  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <label htmlFor={name} className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}

      <div className="relative">
        <input
          id={name}
          type={inputType}
          value={value}
          onChange={handleChange}
          onBlur={handleBlur}
          disabled={disabled}
          readOnly={readOnly}
          placeholder={placeholder}
          className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors ${
            hasError
              ? 'border-red-300 focus:ring-red-500'
              : 'border-gray-300'
          } ${disabled ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : ''} ${
            readOnly ? 'bg-gray-50' : ''
          }`}
          aria-invalid={hasError}
          aria-describedby={hasError ? `${name}-error` : helpText ? `${name}-help` : undefined}
        />

        {showPasswordToggle && value && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            aria-label={showPassword ? t('ui.hidePassword') : t('ui.showPassword')}
          >
            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}

        {hasError && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-red-500">
            <AlertCircle className="w-4 h-4" />
          </div>
        )}
      </div>

      {hasError && validation.error && (
        <p id={`${name}-error`} className="text-sm text-red-600 flex items-center gap-1">
          <AlertCircle className="w-3 h-3" />
          {validation.error}
        </p>
      )}

      {helpText && !hasError && (
        <p id={`${name}-help`} className="text-sm text-gray-500">
          {helpText}
        </p>
      )}
    </div>
  );
}

/**
 * 文本区域字段
 */
export function TextareaField({
  name,
  label,
  placeholder,
  value,
  onChange,
  rules = [],
  disabled = false,
  rows = 4,
  className = '',
  validateOnChange = false,
  helpText,
}: Omit<FormFieldProps, 'type' | 'showPasswordToggle'> & { rows?: number }) {
  const [touched, setTouched] = useState(false);
  const [validation, setValidation] = useState<FieldValidation>({
    isValid: true,
    error: undefined,
  });

  useEffect(() => {
    if (validateOnChange || touched) {
      validateField(value);
    }
  }, [value]);

  const validateField = (fieldValue: string): FieldValidation => {
    if (rules.length === 0) {
      return { isValid: true };
    }

    for (const rule of rules) {
      if (!rule.validate(fieldValue)) {
        const result = { isValid: false, error: rule.message };
        setValidation(result);
        return result;
      }
    }

    const result = { isValid: true };
    setValidation(result);
    return result;
  };

  const handleBlur = () => {
    setTouched(true);
    validateField(value);
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
  };

  const hasError = touched && !validation.isValid;

  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <label htmlFor={name} className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}

      <textarea
        id={name}
        value={value}
        onChange={handleChange}
        onBlur={handleBlur}
        disabled={disabled}
        rows={rows}
        placeholder={placeholder}
        className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors resize-none ${
          hasError ? 'border-red-300 focus:ring-red-500' : 'border-gray-300'
        } ${disabled ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : ''}`}
        aria-invalid={hasError}
        aria-describedby={hasError ? `${name}-error` : helpText ? `${name}-help` : undefined}
      />

      {hasError && validation.error && (
        <p id={`${name}-error`} className="text-sm text-red-600 flex items-center gap-1">
          <AlertCircle className="w-3 h-3" />
          {validation.error}
        </p>
      )}

      {helpText && !hasError && (
        <p id={`${name}-help`} className="text-sm text-gray-500">
          {helpText}
        </p>
      )}
    </div>
  );
}

/**
 * 表单验证 Hook
 */
export function useFormValidation<T extends Record<string, string>>(initialValues: T) {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({});

  const setValue = (name: keyof T, value: string) => {
    setValues((prev) => ({ ...prev, [name]: value }));
  };

  const setTouchedField = (name: keyof T) => {
    setTouched((prev) => ({ ...prev, [name]: true }));
  };

  const setError = (name: keyof T, error: string | undefined) => {
    setErrors((prev) => {
      if (error) {
        return { ...prev, [name]: error };
      }
      const newErrors = { ...prev };
      delete newErrors[name];
      return newErrors;
    });
  };

  const clearErrors = () => {
    setErrors({});
  };

  const reset = () => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  };

  const isValid = Object.keys(errors).length === 0;

  return {
    values,
    errors,
    touched,
    setValue,
    setTouchedField,
    setError,
    clearErrors,
    reset,
    isValid,
  };
}
