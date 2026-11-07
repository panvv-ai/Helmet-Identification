import type { AttendanceRecord, ViolationRecord } from "../api/types";

interface RecordPanelsProps {
  attendance: AttendanceRecord[];
  violations: ViolationRecord[];
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function RecordPanels({ attendance, violations }: RecordPanelsProps) {
  return (
    <section className="record-grid" aria-label="今日记录">
      <article className="panel record-panel">
        <div className="panel__head">
          <div>
            <span className="eyebrow">ATTENDANCE</span>
            <h2>今日签到</h2>
          </div>
          <span className="metric-number metric-number--safe">{attendance.length}</span>
        </div>
        <div className="record-list">
          {attendance.length === 0 ? (
            <span className="subtle">今天还没有签到记录。</span>
          ) : (
            attendance.slice(0, 5).map((record) => (
              <div className="record-row" key={record.id}>
                {record.evidenceUrl ? (
                  <img
                    className="record-thumb"
                    src={record.evidenceUrl}
                    alt={`${record.employeeNo} 签到证据`}
                  />
                ) : (
                  <span className="record-dot" aria-hidden="true" />
                )}
                <span>
                  <strong>{record.employeeNo}</strong>
                  <small>{record.employeeName}</small>
                </span>
                <span>
                  <strong>{formatTime(record.occurredAt)}</strong>
                  <small>{record.late ? "迟到" : "正常"}</small>
                </span>
              </div>
            ))
          )}
        </div>
      </article>
      <article className="panel record-panel record-panel--alert">
        <div className="panel__head">
          <div>
            <span className="eyebrow">SAFETY ALERTS</span>
            <h2>今日违规</h2>
          </div>
          <span className="metric-number metric-number--alert">{violations.length}</span>
        </div>
        <div className="record-list">
          {violations.length === 0 ? (
            <span className="subtle">今天没有未戴安全帽记录。</span>
          ) : (
            violations.slice(0, 5).map((record) => (
              <div className="record-row" key={record.id}>
                {record.evidenceUrl ? (
                  <img
                    className="record-thumb"
                    src={record.evidenceUrl}
                    alt={`${record.employeeNo} 违规证据`}
                  />
                ) : (
                  <span className="record-dot record-dot--alert" aria-hidden="true" />
                )}
                <span>
                  <strong>{record.employeeNo}</strong>
                  <small>{record.employeeName}</small>
                </span>
                <span>
                  <strong>{formatTime(record.occurredAt)}</strong>
                  <small>未戴安全帽</small>
                </span>
              </div>
            ))
          )}
        </div>
      </article>
    </section>
  );
}
