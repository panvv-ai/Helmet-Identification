import type { Workflow } from "../api/types";

const workflows: Array<{ id: Workflow; label: string; kicker: string }> = [
  { id: "collect", label: "采集", kicker: "DATASET" },
  { id: "train", label: "训练", kicker: "MODEL" },
  { id: "detect", label: "检测", kicker: "SCAN" },
];

interface WorkflowTabsProps {
  value: Workflow;
  onChange: (workflow: Workflow) => void;
}

export function WorkflowTabs({ value, onChange }: WorkflowTabsProps) {
  return (
    <div className="workflow-tabs" role="tablist" aria-label="运行类型">
      {workflows.map((workflow) => (
        <button
          key={workflow.id}
          type="button"
          role="tab"
          aria-selected={value === workflow.id}
          className={value === workflow.id ? "is-active" : ""}
          onClick={() => onChange(workflow.id)}
        >
          <span>{workflow.kicker}</span>
          <strong>{workflow.label}</strong>
        </button>
      ))}
    </div>
  );
}
