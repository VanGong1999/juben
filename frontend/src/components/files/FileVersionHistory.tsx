/**
 * 文件版本历史组件
 */

import React, { useState } from 'react';
import { History, Eye, Download, RotateCcw, X, ChevronDown, ChevronUp } from 'lucide-react';

export interface FileVersion {
  version: number;
  fileId: string;
  timestamp: string;
  size: number;
  author: string;
  changes: string;
  hash: string;
}

interface FileVersionHistoryProps {
  isOpen: boolean;
  onClose: () => void;
  fileId: string;
  fileName: string;
  versions: FileVersion[];
  onRestore: (version: number) => Promise<void>;
  onCompare: (version1: number, version2: number) => void;
}

export const FileVersionHistory: React.FC<FileVersionHistoryProps> = ({
  isOpen,
  onClose,
  fileId,
  fileName,
  versions,
  onRestore,
  onCompare,
}) => {
  const [expandedVersions, setExpandedVersions] = useState<Set<number>>(new Set());
  const [selectedVersions, setSelectedVersions] = useState<number[]>([]);
  const [isRestoring, setIsRestoring] = useState(false);

  if (!isOpen) return null;

  const toggleExpand = (version: number) => {
    const newExpanded = new Set(expandedVersions);
    if (newExpanded.has(version)) {
      newExpanded.delete(version);
    } else {
      newExpanded.add(version);
    }
    setExpandedVersions(newExpanded);
  };

  const handleVersionSelect = (version: number) => {
    if (selectedVersions.includes(version)) {
      setSelectedVersions(selectedVersions.filter((v) => v !== version));
    } else if (selectedVersions.length < 2) {
      setSelectedVersions([...selectedVersions, version]);
    }
  };

  const handleRestore = async (version: number) => {
    setIsRestoring(true);
    try {
      await onRestore(version);
    } finally {
      setIsRestoring(false);
    }
  };

  const handleCompare = () => {
    if (selectedVersions.length === 2) {
      onCompare(selectedVersions[0], selectedVersions[1]);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden mx-4">
        {/* 头部 */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <History className="w-6 h-6 text-purple-500" />
              <div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  版本历史
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {fileName}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* 版本比较 */}
          {selectedVersions.length > 0 && (
            <div className="mt-4 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg flex items-center justify-between">
              <div className="text-sm">
                <span className="font-medium text-purple-900 dark:text-purple-200">
                  已选择 {selectedVersions.length} 个版本
                </span>
                {selectedVersions.length === 2 && (
                  <span className="text-purple-700 dark:text-purple-300 ml-2">
                    v{selectedVersions[0]} vs v{selectedVersions[1]}
                  </span>
                )}
              </div>
              <button
                onClick={handleCompare}
                disabled={selectedVersions.length !== 2}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
              >
                比较版本
              </button>
            </div>
          )}
        </div>

        {/* 版本列表 */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          <div className="space-y-3">
            {versions.map((versionInfo, index) => (
              <div
                key={versionInfo.version}
                className={`border rounded-lg transition-all ${
                  selectedVersions.includes(versionInfo.version)
                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                }`}
              >
                <div className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4 flex-1">
                      {/* 版本选择框 */}
                      <input
                        type="checkbox"
                        checked={selectedVersions.includes(versionInfo.version)}
                        onChange={() => handleVersionSelect(versionInfo.version)}
                        className="mt-1 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                      />

                      {/* 版本信息 */}
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 text-xs font-medium rounded">
                            v{versionInfo.version}
                          </span>
                          <span className="text-sm text-gray-600 dark:text-gray-400">
                            {new Date(versionInfo.timestamp).toLocaleString()}
                          </span>
                          <span className="text-xs text-gray-500">
                            {formatFileSize(versionInfo.size)}
                          </span>
                          {index === 0 && (
                            <span className="px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs rounded">
                              当前版本
                            </span>
                          )}
                        </div>

                        <div className="text-sm text-gray-700 dark:text-gray-300 mb-2">
                          <span className="font-medium">{versionInfo.author}</span>
                          <span className="text-gray-500 mx-2">•</span>
                          <span>{versionInfo.changes}</span>
                        </div>

                        <div className="text-xs text-gray-500 font-mono">
                          SHA-256: {versionInfo.hash.substring(0, 16)}...
                        </div>
                      </div>
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex items-center gap-2 ml-4">
                      <button
                        onClick={() => toggleExpand(versionInfo.version)}
                        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        title={expandedVersions.has(versionInfo.version) ? '收起' : '展开'}
                      >
                        {expandedVersions.has(versionInfo.version) ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                      {index !== 0 && (
                        <button
                          onClick={() => handleRestore(versionInfo.version)}
                          disabled={isRestoring}
                          className="p-2 hover:bg-green-100 dark:hover:bg-green-900/30 rounded-lg transition-colors"
                          title="恢复此版本"
                        >
                          <RotateCcw className={`w-4 h-4 text-green-600 ${isRestoring ? 'animate-spin' : ''}`} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* 展开的详细内容 */}
                  {expandedVersions.has(versionInfo.version) && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">文件大小:</span>
                          <span className="ml-2 text-gray-900 dark:text-white">
                            {formatFileSize(versionInfo.size)}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">创建时间:</span>
                          <span className="ml-2 text-gray-900 dark:text-white">
                            {new Date(versionInfo.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">作者:</span>
                          <span className="ml-2 text-gray-900 dark:text-white">
                            {versionInfo.author}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">哈希值:</span>
                          <span className="ml-2 font-mono text-gray-900 dark:text-white text-xs">
                            {versionInfo.hash}
                          </span>
                        </div>
                      </div>

                      <div className="flex gap-2 mt-4">
                        <button className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-sm">
                          <Eye className="w-3 h-3" />
                          预览
                        </button>
                        <button className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-sm">
                          <Download className="w-3 h-3" />
                          下载
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {versions.length === 0 && (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              <History className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>暂无版本历史</p>
            </div>
          )}
        </div>

        {/* 底部 */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg font-medium transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};
