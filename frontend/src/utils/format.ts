/** 把字数显示成「1.2万字」或「860字」。 */
export function formatWordCount(count: number): string {
  if (count >= 10_000) {
    const wan = count / 10_000;
    const text = wan >= 10 ? wan.toFixed(0) : wan.toFixed(1).replace(/\.0$/, '');
    return `${text}万字`;
  }
  return `${count.toLocaleString()}字`;
}

/** 把 ISO 时间显示成相对时间。 */
export function formatRelativeTime(iso: string): string {
  if (!iso) return '';
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return '';
  const diff = Date.now() - t;
  const min = Math.floor(diff / 60_000);
  if (min < 1) return '刚刚';
  if (min < 60) return `${min} 分钟前`;
  const hour = Math.floor(min / 60);
  if (hour < 24) return `${hour} 小时前`;
  const day = Math.floor(hour / 24);
  if (day < 30) return `${day} 天前`;
  return new Date(iso).toLocaleDateString('zh-CN');
}
