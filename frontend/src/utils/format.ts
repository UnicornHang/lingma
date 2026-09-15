/** 把字数显示成「1.2万字」或「860字」。 */
export function formatWordCount(count: number): string {
  if (count >= 10_000) {
    const wan = count / 10_000;
    const text = wan >= 10 ? wan.toFixed(0) : wan.toFixed(1).replace(/\.0$/, '');
    return `${text}万字`;
  }
  return `${count.toLocaleString()}字`;
}
