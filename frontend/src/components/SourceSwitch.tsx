import type { Source } from "../api/types";

const sources: Array<{ id: Source; label: string; icon: string }> = [
  { id: "photo", label: "照片", icon: "▧" },
  { id: "video", label: "视频", icon: "▶" },
  { id: "camera", label: "摄像头", icon: "◉" },
];

interface SourceSwitchProps {
  value: Source;
  onChange: (source: Source) => void;
}

export function SourceSwitch({ value, onChange }: SourceSwitchProps) {
  return (
    <div className="segmented segmented--source" aria-label="数据来源">
      {sources.map((source) => (
        <button
          key={source.id}
          type="button"
          className={value === source.id ? "is-active" : ""}
          aria-pressed={value === source.id}
          onClick={() => onChange(source.id)}
        >
          <span aria-hidden="true">{source.icon}</span>
          {source.label}
        </button>
      ))}
    </div>
  );
}
