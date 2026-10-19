/**
 * 把「开始分析…正在…正在…## 报告」这类被误拼进正文的进度，拆成竖排列表 + 正文。
 */

/** 一段连续「xxx...yyy...」进度链 → 竖排行 + 剩余正文 */
export function splitProgressPrefix(content: string): {
  progressLines: string[];
  body: string;
} {
  const text = content || '';
  if (!text) return { progressLines: [], body: '' };

  // 已是「、进度」换行格式
  if (/^[、•·]\s*\S/m.test(text) && text.includes('\n')) {
    const lines = text.split('\n');
    const progressLines: string[] = [];
    let i = 0;
    for (; i < lines.length; i++) {
      const raw = lines[i];
      const m = raw.match(/^[、•·\-]\s*(.+)$/);
      if (!m) break;
      const line = m[1].trim();
      if (!/^(开始|正在)/.test(line) && !/[…\.]{3}$|…$/.test(line)) break;
      progressLines.push(line);
    }
    if (progressLines.length > 0) {
      return { progressLines, body: lines.slice(i).join('\n').trimStart() };
    }
  }

  const progressLines: string[] = [];
  let rest = text;
  // 匹配「开始…」或「正在…」并以 ... / … 结尾的短进度句
  const re = /^(开始[^#\n]{0,100}?|正在[^#\n]{0,100}?)(?:\.{3}|…)/;
  while (true) {
    const m = rest.match(re);
    if (!m) break;
    progressLines.push(m[0]);
    rest = rest.slice(m[0].length);
  }

  if (progressLines.length === 0) {
    return { progressLines: [], body: text };
  }
  return { progressLines, body: rest.trimStart() };
}

export function formatProgressLines(lines: string[], bullet = '、'): string {
  return lines.map((l) => `${bullet}${l}`).join('\n');
}
