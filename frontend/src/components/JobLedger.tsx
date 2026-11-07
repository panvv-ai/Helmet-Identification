import type { Job } from "../api/types";

function statusLabel(job: Job) {
  if (job.status === "succeeded") return "已完成";
  if (job.status === "failed") return "失败";
  if (job.status === "running") return `${job.progress}%`;
  if (job.status === "interrupted") return "已中断";
  return "排队中";
}

export function JobLedger({ jobs }: { jobs: Job[] }) {
  return (
    <section className="panel job-ledger" aria-label="任务记录">
      <div className="panel__head">
        <div>
          <span className="eyebrow">JOB TRACE</span>
          <h2>最近任务</h2>
        </div>
        <span className="ledger-count">{jobs.length} 条</span>
      </div>
      {jobs.length === 0 ? (
        <div className="empty-state empty-state--inline">
          <span>训练、照片分析或视频分析完成后会在这里留下记录。</span>
        </div>
      ) : (
        <div className="job-list">
          {jobs.slice(0, 6).map((job) => (
            <div className="job-row" key={job.id}>
              <span className={`job-status job-status--${job.status}`} />
              <span>
                <strong>
                  {job.kind === "train"
                    ? "身份模型训练"
                    : job.kind === "analyze"
                      ? "现场分析"
                      : "样本采集"}
                </strong>
                <small>{job.message}</small>
              </span>
              <time>{statusLabel(job)}</time>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
