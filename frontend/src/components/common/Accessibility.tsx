/**
 * 可访问性工具组件和 Hooks
 * 提供 ARIA 标签、键盘导航和屏幕阅读器支持
 */

import { useEffect, useRef, useCallback } from 'react';
import { useI18n, translate } from '@/i18n';

/**
 * 跳转到主内容链接（用于屏幕阅读器）
 */
export function SkipToContent({ mainId = 'main-content' }: { mainId?: string }) {
  const { t } = useI18n();
  return (
    <a
      href={`#${mainId}`}
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-black focus:text-white focus:rounded-lg"
    >
      {t('ui.skipToContent')}
    </a>
  );
}

/**
 * 屏幕阅读器专用文本
 */
interface VisuallyHiddenProps {
  children: React.ReactNode;
  /** 是否可聚焦 (用于键盘用户) */
  focusable?: boolean;
}

export function VisuallyHidden({ children, focusable = false }: VisuallyHiddenProps) {
  return (
    <span
      className={focusable ? 'sr-only focus:not-sr-only' : 'sr-only'}
      aria-hidden={!focusable}
    >
      {children}
    </span>
  );
}

/**
 * 焦点陷阱组件（用于模态框）
 */
export function FocusTrap({
  children,
  active = true,
}: {
  children: React.ReactElement;
  active?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active || !ref.current) return;

    const focusableElements = ref.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[
      focusableElements.length - 1
    ] as HTMLElement;

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    document.addEventListener('keydown', handleTab);
    firstElement?.focus();

    return () => {
      document.removeEventListener('keydown', handleTab);
    };
  }, [active]);

  return <div ref={ref}>{children}</div>;
}

/**
 * 实时区域标记（用于动态内容通知）
 */
interface LiveRegionProps {
  children: React.ReactNode;
  /** 优先级 */
  level?: 'polite' | 'assertive';
  /** 是否显示 (用于调试) */
  show?: boolean;
}

export function LiveRegion({ children, level = 'polite', show = false }: LiveRegionProps) {
  return (
    <div
      aria-live={level}
      aria-atomic="true"
      className={show ? '' : 'sr-only'}
      role="status"
    >
      {children}
    </div>
  );
}

/**
 * 键盘导航 Hook
 */
export function useKeyboardNavigation(
  items: Array<{ id: string; element?: HTMLElement }>,
  options?: {
    loop?: boolean;
    orientation?: 'horizontal' | 'vertical' | 'both';
  }
) {
  const { loop = true, orientation = 'vertical' } = options || {};

  const handleKeyDown = useCallback(
    (currentIndex: number, e: KeyboardEvent) => {
      let nextIndex = currentIndex;

      switch (e.key) {
        case 'ArrowDown':
          if (orientation === 'vertical' || orientation === 'both') {
            e.preventDefault();
            nextIndex = currentIndex + 1;
          }
          break;
        case 'ArrowUp':
          if (orientation === 'vertical' || orientation === 'both') {
            e.preventDefault();
            nextIndex = currentIndex - 1;
          }
          break;
        case 'ArrowRight':
          if (orientation === 'horizontal' || orientation === 'both') {
            e.preventDefault();
            nextIndex = currentIndex + 1;
          }
          break;
        case 'ArrowLeft':
          if (orientation === 'horizontal' || orientation === 'both') {
            e.preventDefault();
            nextIndex = currentIndex - 1;
          }
          break;
        case 'Home':
          e.preventDefault();
          nextIndex = 0;
          break;
        case 'End':
          e.preventDefault();
          nextIndex = items.length - 1;
          break;
        default:
          return;
      }

      // 处理循环
      if (loop) {
        if (nextIndex >= items.length) nextIndex = 0;
        if (nextIndex < 0) nextIndex = items.length - 1;
      } else {
        nextIndex = Math.max(0, Math.min(items.length - 1, nextIndex));
      }

      const nextItem = items[nextIndex];
      nextItem?.element?.focus();
    },
    [items, loop, orientation]
  );

  return { handleKeyDown };
}

/**
 * 自动对焦 Hook
 */
export function useAutoFocus(
  active: boolean,
  selector?: string
) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!active) return;

    const element = selector
      ? ref.current?.querySelector(selector)
      : ref.current;

    if (element instanceof HTMLElement) {
      element.focus();
    }
  }, [active, selector]);

  return ref;
}

/**
 * ARIA 属性工具函数
 */
export const ARIA = {
  /** 描述标签 */
  describedBy: (id: string) => ({ 'aria-describedby': id }),

  /** 标签关联 */
  labelledBy: (id: string) => ({ 'aria-labelledby': id }),

  /** 当前状态 */
  current: (current: boolean) => ({ 'aria-current': current ? 'page' : undefined }),

  /** 展开状态 */
  expanded: (expanded: boolean) => ({ 'aria-expanded': expanded }),

  /** 选中状态 */
  selected: (selected: boolean) => ({ 'aria-selected': selected }),

  /** 隐藏状态 */
  hidden: (hidden: boolean) => ({ 'aria-hidden': hidden }),

  /** 必填状态 */
  required: (required: boolean) => ({ 'aria-required': required }),

  /** 无效状态 */
  invalid: (invalid: boolean) => ({ 'aria-invalid': invalid }),

  /** 禁用状态 */
  disabled: (disabled: boolean) => ({ 'aria-disabled': disabled }),

  /** 加载状态 */
  busy: (busy: boolean) => ({ 'aria-busy': busy }),

  /** 实时区域 */
  live: (level: 'polite' | 'assertive' = 'polite') => ({
    'aria-live': level,
    'aria-atomic': 'true',
  }),

  /** 弹出框角色 */
  dialog: () => ({ role: 'dialog', 'aria-modal': 'true' }),

  /** 警告角色 */
  alert: () => ({ role: 'alert' }),

  /** 状态角色 */
  status: () => ({ role: 'status' }),

  /** 导航角色 */
  navigation: () => ({ role: 'navigation' }),

  /** 主要内容角色 */
  main: () => ({ role: 'main' }),

  /** 补充内容角色 */
  complementary: () => ({ role: 'complementary' }),

  /** 搜索角色 */
  search: () => ({ role: 'search' }),

  /** 表单角色 */
  form: () => ({ role: 'form' }),

  /** 列表框角色 */
  listbox: () => ({ role: 'listbox' }),

  /** 选项角色 */
  option: (selected: boolean) => ({
    role: 'option',
    'aria-selected': selected,
  }),

  /** 标签角色 */
  tab: (selected: boolean) => ({
    role: 'tab',
    'aria-selected': selected,
  }),

  /** 标签面板角色 */
  tabPanel: (labelledBy: string) => ({
    role: 'tabpanel',
    'aria-labelledby': labelledBy,
  }),

  /** 按钮角色 */
  button: (pressed?: boolean) => ({
    role: 'button',
    'aria-pressed': pressed,
  }),

  /** 复选框角色 */
  checkbox: (checked: boolean | 'mixed') => ({
    role: 'checkbox',
    'aria-checked': checked,
  }),

  /** 单选框角色 */
  radio: (checked: boolean) => ({
    role: 'radio',
    'aria-checked': checked,
  }),

  /** 开关角色 */
  switch: (checked: boolean) => ({
    role: 'switch',
    'aria-checked': checked,
  }),

  /** 滑块角色 */
  slider: (value: number, min?: number, max?: number) => ({
    role: 'slider',
    'aria-valuenow': value,
    'aria-valuemin': min,
    'aria-valuemax': max,
  }),

  /** 进度条角色 */
  progressbar: (value: number, max?: number) => ({
    role: 'progressbar',
    'aria-valuenow': value,
    'aria-valuemax': max,
  }),

  /** 工具提示角色 */
  tooltip: () => ({ role: 'tooltip' }),
};

/**
 * 键盘快捷键提示组件
 */
interface KeyboardShortcutProps {
  shortcut: string[];
  description: string;
  /** 是否使用 macOS 风格的快捷键显示 */
  macStyle?: boolean;
}

export function KeyboardShortcut({
  shortcut,
  description,
  macStyle = true,
}: KeyboardShortcutProps) {
  const formatKey = (key: string) => {
    if (macStyle && navigator.platform.toUpperCase().indexOf('MAC') >= 0) {
      return key
        .replace('Ctrl', '⌘')
        .replace('Cmd', '⌘')
        .replace('Alt', '⌥')
        .replace('Shift', '⇧')
        .replace('Enter', '↵')
        .replace('Escape', '⎋')
        .replace('Backspace', '⌫');
    }
    return key;
  };

  return (
    <div className="flex items-center gap-2 text-xs text-gray-500">
      <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-300 rounded font-mono">
        {shortcut.map(formatKey).join(' + ')}
      </kbd>
      <span>{description}</span>
    </div>
  );
}

/**
 * 快捷键列表组件
 */
interface ShortcutListProps {
  shortcuts: Array<{
    keys: string[];
    description: string;
    action?: () => void;
  }>;
  /** 标题 */
  title?: string;
}

export function ShortcutList({ shortcuts, title = translate('ui.shortcuts') }: ShortcutListProps) {
  return (
    <div className="p-4 bg-gray-50 rounded-lg" role="region" aria-label={title}>
      {title && (
        <h4 className="text-sm font-medium text-gray-900 mb-3">{title}</h4>
      )}
      <div className="space-y-2">
        {shortcuts.map((shortcut, index) => (
          <div key={index} className="flex items-center justify-between">
            <span className="text-sm text-gray-600">{shortcut.description}</span>
            <div className="flex gap-1">
              {shortcut.keys.map((key, keyIndex) => (
                <kbd
                  key={keyIndex}
                  className="px-2 py-1 bg-white border border-gray-300 rounded text-xs font-mono"
                >
                  {key}
                </kbd>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
