import type { Model } from "../api/types";

interface ModelLedgerProps {
  models: Model[];
  onActivate: (modelId: string) => void;
}

export function ModelLedger({ models, onActivate }: ModelLedgerProps) {
  return (
    <section className="panel ledger ledger--models" aria-label="模型历史">
      <div className="panel__head">
        <div>
          <span className="eyebrow">MODEL LEDGER</span>
          <h2>身份模型</h2>
        </div>
        <span className="ledger-count">{models.length} 个版本</span>
      </div>
      {models.length === 0 ? (
        <div className="empty-state">
          <strong>等待第一个模型</strong>
          <span>至少准备 2 名员工、每人 2 张可读人脸，然后开始训练。</span>
        </div>
      ) : (
        <div className="model-list">
          {models.map((model) => (
            <button
              type="button"
              key={model.id}
              className={model.active ? "model-row is-active" : "model-row"}
              onClick={() => onActivate(model.id)}
              disabled={model.active}
            >
              <span>
                <strong>{model.name}</strong>
                <small>宏平均 F1 {((model.metrics.macroF1 ?? 0) * 100).toFixed(1)}%</small>
              </span>
              <span>{model.active ? "当前启用" : "切换"}</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
