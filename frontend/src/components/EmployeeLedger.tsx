import type { Employee, Sample } from "../api/types";

interface EmployeeLedgerProps {
  employees: Employee[];
  selectedId: string | null;
  samples: Sample[];
  onSelect: (employeeId: string) => void;
  onContinue: (employeeId: string) => void;
  onDeleteEmployee: (employeeId: string) => void;
  onDeleteSample: (sampleId: string) => void;
}

export function EmployeeLedger({
  employees,
  selectedId,
  samples,
  onSelect,
  onContinue,
  onDeleteEmployee,
  onDeleteSample,
}: EmployeeLedgerProps) {
  const selected = employees.find((employee) => employee.id === selectedId);
  return (
    <section className="panel ledger ledger--people" aria-label="员工数据">
      <div className="panel__head">
        <div>
          <span className="eyebrow">PEOPLE / DATASET</span>
          <h2>人员与人脸样本</h2>
        </div>
        <span className="ledger-count">{employees.length} 人</span>
      </div>
      <div className="employee-table">
        {employees.length === 0 ? (
          <div className="empty-state">
            <strong>还没有员工</strong>
            <span>先建立员工档案，再从照片或摄像头采集训练样本。</span>
          </div>
        ) : (
          employees.map((employee) => (
            <button
              key={employee.id}
              type="button"
              className={`employee-row ${selectedId === employee.id ? "is-selected" : ""}`}
              onClick={() => onSelect(employee.id)}
            >
              <span className="employee-avatar">{employee.name.slice(0, 1)}</span>
              <span className="employee-copy">
                <strong>{employee.name}</strong>
                <span>{employee.employeeNo}</span>
              </span>
              <span className="sample-count">{employee.sampleCount} 张样本</span>
              <span className="row-arrow">↗</span>
            </button>
          ))
        )}
      </div>
      {selected && (
        <div className="sample-manager">
          <div className="sample-manager__head">
            <div>
              <span className="eyebrow">CURRENT PROFILE</span>
              <strong>{selected.name}</strong>
            </div>
            <div className="inline-actions">
              <button type="button" onClick={() => onContinue(selected.id)}>
                继续采集
              </button>
              <button
                type="button"
                className="danger-link"
                onClick={() => onDeleteEmployee(selected.id)}
              >
                停用人员
              </button>
            </div>
          </div>
          <div className="sample-grid">
            {samples.length === 0 ? (
              <span className="subtle">当前人员还没有可训练样本人脸。</span>
            ) : (
              samples.map((sample) => (
                <figure key={sample.id} className="sample-card">
                  <img src={sample.imageUrl} alt={`${selected.name} 的人脸样本`} />
                  <button
                    type="button"
                    aria-label="删除这张样本"
                    onClick={() => onDeleteSample(sample.id)}
                  >
                    ×
                  </button>
                </figure>
              ))
            )}
          </div>
        </div>
      )}
    </section>
  );
}
