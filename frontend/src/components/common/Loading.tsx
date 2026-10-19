/**
 * 加载动画组件
 * 提供多种加载动画效果
 */

import { translate } from '@/i18n';

interface LoadingProps {
  /** 加载类型 */
  type?: 'dots' | 'bars' | 'pulse' | 'spinner' | 'bounce' | 'shimmer';
  /** 尺寸 */
  size?: 'sm' | 'md' | 'lg';
  /** 颜色 */
  color?: string;
  /** 文字 */
  text?: string;
  /** 是否全屏显示 */
  fullScreen?: boolean;
}

export default function Loading({
  type = 'dots',
  size = 'md',
  color = '#000000',
  text,
  fullScreen = false,
}: LoadingProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  const content = (
    <div className="flex flex-col items-center justify-center gap-3">
      {/* Dots 动画 */}
      {type === 'dots' && (
        <div className="flex items-center gap-2">
          <div
            className="rounded-full animate-bounce"
            style={{
              width: size === 'sm' ? '8px' : size === 'md' ? '12px' : '16px',
              height: size === 'sm' ? '8px' : size === 'md' ? '12px' : '16px',
              backgroundColor: color,
              animationDelay: '0ms',
            }}
          />
          <div
            className="rounded-full animate-bounce"
            style={{
              width: size === 'sm' ? '8px' : size === 'md' ? '12px' : '16px',
              height: size === 'sm' ? '8px' : size === 'md' ? '12px' : '16px',
              backgroundColor: color,
              animationDelay: '150ms',
            }}
          />
          <div
            className="rounded-full animate-bounce"
            style={{
              width: size === 'sm' ? '8px' : size === 'md' ? '12px' : '16px',
              height: size === 'sm' ? '8px' : size === 'md' ? '12px' : '16px',
              backgroundColor: color,
              animationDelay: '300ms',
            }}
          />
        </div>
      )}

      {/* Bars 动画 */}
      {type === 'bars' && (
        <div className="flex items-end gap-1">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="rounded-sm animate-pulse-bar"
              style={{
                width: size === 'sm' ? '3px' : size === 'md' ? '4px' : '6px',
                height: size === 'sm' ? '12px' : size === 'md' ? '20px' : '32px',
                backgroundColor: color,
                animationDelay: `${i * 100}ms`,
              }}
            />
          ))}
        </div>
      )}

      {/* Pulse 动画 */}
      {type === 'pulse' && (
        <div
          className={`rounded-full ${sizeClasses[size]} animate-pulse-ring`}
          style={{ backgroundColor: color }}
        />
      )}

      {/* Spinner 动画 */}
      {type === 'spinner' && (
        <div className="relative">
          <div
            className={`${sizeClasses[size]} rounded-full border-2 border-transparent animate-spin`}
            style={{
              borderTopColor: color,
              borderRightColor: color,
            }}
          />
        </div>
      )}

      {/* Bounce 动画 */}
      {type === 'bounce' && (
        <div className="flex items-center gap-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="rounded-full animate-bounce-in"
              style={{
                width: size === 'sm' ? '10px' : size === 'md' ? '14px' : '20px',
                height: size === 'sm' ? '10px' : size === 'md' ? '14px' : '20px',
                backgroundColor: color,
                animationDelay: `${i * 150}ms`,
              }}
            />
          ))}
        </div>
      )}

      {/* Shimmer 动画 */}
      {type === 'shimmer' && (
        <div
          className="animate-shimmer rounded"
          style={{
            width: size === 'sm' ? '40px' : size === 'md' ? '60px' : '80px',
            height: size === 'sm' ? '8px' : size === 'md' ? '12px' : '16px',
            background: `linear-gradient(90deg, ${color}20 25%, ${color}60 50%, ${color}20 75%)`,
            backgroundSize: '200% 100%',
          }}
        />
      )}

      {/* 加载文字 */}
      {text && (
        <p className="text-sm text-gray-500 animate-fade-in" style={{ animationDelay: '300ms' }}>
          {text}
        </p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-sm">
        {content}
      </div>
    );
  }

  return content;
}

/**
 * 行内加载指示器
 */
export function InlineLoader({ size = 'sm' }: { size?: 'sm' | 'md' }) {
  return (
    <div className="inline-flex items-center gap-1">
      <div
        className={`rounded-full animate-pulse`}
        style={{
          width: size === 'sm' ? '6px' : '8px',
          height: size === 'sm' ? '6px' : '8px',
          backgroundColor: '#000',
          animationDelay: '0ms',
        }}
      />
      <div
        className={`rounded-full animate-pulse`}
        style={{
          width: size === 'sm' ? '6px' : '8px',
          height: size === 'sm' ? '6px' : '8px',
          backgroundColor: '#000',
          animationDelay: '150ms',
        }}
      />
      <div
        className={`rounded-full animate-pulse`}
        style={{
          width: size === 'sm' ? '6px' : '8px',
          height: size === 'sm' ? '6px' : '8px',
          backgroundColor: '#000',
          animationDelay: '300ms',
        }}
      />
    </div>
  );
}

/**
 * 按钮加载状态
 */
export function ButtonLoader({ text = translate('ui.loading') }: { text?: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      <span>{text}</span>
    </div>
  );
}
