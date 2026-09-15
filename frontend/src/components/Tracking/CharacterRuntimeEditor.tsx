import { useState } from 'react';
import { Button, Input } from 'antd';

import type { CharacterRuntimeState } from '@/api/tracking';

interface CharacterRuntimeEditorProps {
  state: CharacterRuntimeState;
  saving: boolean;
  onSave: (next: CharacterRuntimeState) => void;
}

/** 单角色运行时状态表单：位置 / 目标 / 已知 / 未知。 */
export function CharacterRuntimeEditor({ state, saving, onSave }: CharacterRuntimeEditorProps) {
  const [location, setLocation] = useState(state.location);
  const [goal, setGoal] = useState(state.goal);
  const [known, setKnown] = useState(state.known_facts.join('\n'));
  const [unknown, setUnknown] = useState(state.unknown_facts.join('\n'));

  return (
    <div className="p-2 rounded bg-surface-container-lowest text-body-sm flex flex-col gap-2">
      <div className="font-semibold">{state.name || state.character_id}</div>
      <label className="text-label-sm text-on-surface-variant">位置</label>
      <Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="此刻在哪" />
      <label className="text-label-sm text-on-surface-variant">目标</label>
      <Input value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="此刻想做什么" />
      <label className="text-label-sm text-on-surface-variant">已知（每行一条）</label>
      <Input.TextArea rows={2} value={known} onChange={(e) => setKnown(e.target.value)} />
      <label className="text-label-sm text-on-surface-variant">未知（每行一条，正文不得让其开口说出）</label>
      <Input.TextArea rows={2} value={unknown} onChange={(e) => setUnknown(e.target.value)} />
      <Button
        size="small"
        type="primary"
        loading={saving}
        onClick={() =>
          onSave({
            ...state,
            location,
            goal,
            known_facts: splitLines(known),
            unknown_facts: splitLines(unknown),
          })
        }
      >
        保存状态
      </Button>
    </div>
  );
}

/** 把多行文本拆成账本列表。 */
function splitLines(value: string): string[] {
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
}
