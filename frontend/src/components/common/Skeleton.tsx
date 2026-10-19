/**
 * 骨架屏组件
 * 用于在内容加载时提供占位符
 */

import React from 'react';

interface SkeletonProps {
  /** 骨架类型 */
  type?: 'text' | 'avatar' | 'card' | 'list' | 'custom';
  /** 宽度 */
  width?: string | number;
  /** 高度 */
  height?: string | number;
  /** 行数 (仅文本类型) */
  lines?: number;
  /** 是否显示动画 */
  animated?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 自定义样式 */
  style?: React.CSSProperties;
}

export default function Skeleton({
  type = 'text',
  width,
  height,
  lines = 3,
  animated = true,
  className = '',
  style,
}: SkeletonProps) {
  const baseClasses = 'rounded bg-gray-200';
  const animationClass = animated ? 'animate-pulse-skeleton' : '';
  const combinedClasses = `${baseClasses} ${animationClass} ${className}`.trim();

  const commonStyle = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
    ...style,
  };

  // 文本骨架
  if (type === 'text') {
    return (
      <div className="space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={combinedClasses}
            style={{
              ...commonStyle,
              height: height || '16px',
              width: i === lines - 1 ? '60%' : '100%',
            }}
          />
        ))}
      </div>
    );
  }

  // 头像骨架
  if (type === 'avatar') {
    return (
      <div
        className={`${combinedClasses} rounded-full`}
        style={{
          ...commonStyle,
          width: width || '40px',
          height: height || '40px',
        }}
      />
    );
  }

  // 卡片骨架
  if (type === 'card') {
    return (
      <div className="p-4 border rounded-lg space-y-3">
        {/* 标题 */}
        <div
          className={combinedClasses}
          style={{ height: '24px', width: '60%' }}
        />
        {/* 描述 */}
        <div className="space-y-2">
          <div className={combinedClasses} style={{ height: '16px' }} />
          <div className={combinedClasses} style={{ height: '16px', width: '80%' }} />
        </div>
        {/* 底部 */}
        <div className="flex justify-between items-center pt-2">
          <div className={`${combinedClasses} rounded-full`} style={{ width: '32px', height: '32px' }} />
          <div className={combinedClasses} style={{ width: '80px', height: '24px' }} />
        </div>
      </div>
    );
  }

  // 列表项骨架
  if (type === 'list') {
    return (
      <div className="flex items-start gap-3 p-3 border-b">
        <div className={`${combinedClasses} rounded-full`} style={{ width: '40px', height: '40px' }} />
        <div className="flex-1 space-y-2">
          <div className={combinedClasses} style={{ height: '20px', width: '40%' }} />
          <div className={combinedClasses} style={{ height: '16px' }} />
          <div className={combinedClasses} style={{ height: '16px', width: '70%' }} />
        </div>
      </div>
    );
  }

  // 自定义骨架
  return (
    <div
      className={combinedClasses}
      style={commonStyle}
    />
  );
}

/**
 * 消息骨架屏
 */
export function MessageSkeleton() {
  return (
    <div className="flex gap-4 p-4 animate-fade-in">
      {/* 头像 */}
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gray-200 animate-pulse-skeleton" />

      {/* 内容 */}
      <div className="flex-1 space-y-3">
        {/* 名称 */}
        <div className="h-4 w-24 bg-gray-200 rounded animate-pulse-skeleton" />

        {/* 消息气泡 */}
        <div className="p-4 bg-gray-50 rounded-xl space-y-2">
          <div className="h-4 bg-gray-200 rounded animate-pulse-skeleton" />
          <div className="h-4 bg-gray-200 rounded animate-pulse-skeleton" />
          <div className="h-4 bg-gray-200 rounded animate-pulse-skeleton w-3/4" />
        </div>
      </div>
    </div>
  );
}

/**
 * Agent 列表项骨架屏
 */
export function AgentListItemSkeleton() {
  return (
    <div className="flex items-center gap-3 p-3 border-b animate-fade-in hover:bg-gray-50 transition-colors">
      <div className="w-12 h-12 rounded-lg bg-gray-200 animate-pulse-skeleton" />
      <div className="flex-1 space-y-2">
        <div className="h-4 w-32 bg-gray-200 rounded animate-pulse-skeleton" />
        <div className="h-3 w-48 bg-gray-200 rounded animate-pulse-skeleton" />
      </div>
      <div className="h-8 w-16 bg-gray-200 rounded animate-pulse-skeleton" />
    </div>
  );
}

/**
 * 输入框骨架屏
 */
export function InputSkeleton() {
  return (
    <div className="p-4 border-t bg-white animate-fade-in">
      <div className="h-24 bg-gray-200 rounded-lg animate-pulse-skeleton" />
    </div>
  );
}

/**
 * 聊天容器骨架屏
 */
export function ChatContainerSkeleton() {
  return (
    <div className="flex flex-col h-screen">
      {/* 头部 */}
      <div className="h-14 border-b bg-white flex items-center justify-between px-4">
        <div className="h-6 w-32 bg-gray-200 rounded animate-pulse-skeleton" />
        <div className="flex gap-2">
          <div className="h-8 w-8 bg-gray-200 rounded animate-pulse-skeleton" />
          <div className="h-8 w-8 bg-gray-200 rounded animate-pulse-skeleton" />
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <MessageSkeleton />
        <MessageSkeleton />
      </div>

      {/* 输入框 */}
      <InputSkeleton />
    </div>
  );
}
