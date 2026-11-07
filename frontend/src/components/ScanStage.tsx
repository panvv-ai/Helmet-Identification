import type { CameraMessage, Detection, Source } from "../api/types";

interface ScanStageProps {
  source: Source;
  previewUrl: string | null;
  busy: boolean;
  cameraActive: boolean;
  latestMessage: CameraMessage | null;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  resultUrl: string | null;
}

function DetectionChip({ detection }: { detection: Detection }) {
  const compliant = detection.helmetState === "with_helmet";
  return (
    <div className={`detection-chip ${compliant ? "is-safe" : "is-alert"}`}>
      <span>{compliant ? "已戴安全帽" : "未戴安全帽"}</span>
      <strong>{detection.employeeNo ?? detection.identity}</strong>
    </div>
  );
}

export function ScanStage({
  source,
  previewUrl,
  busy,
  cameraActive,
  latestMessage,
  videoRef,
  resultUrl,
}: ScanStageProps) {
  const detections = latestMessage?.detections ?? [];
  return (
    <section className="scan-stage panel" aria-label="检测舞台">
      <div className="panel__head">
        <div>
          <span className="eyebrow">LIVE FIELD</span>
          <h2>现场扫描舞台</h2>
        </div>
        <div className="stage-status">
          <span className={busy || cameraActive ? "pulse-dot is-live" : "pulse-dot"} />
          {busy ? "处理中" : cameraActive ? "实时连接" : "等待画面"}
        </div>
      </div>
      <div className={`scan-canvas scan-canvas--${source}`}>
        {resultUrl ? (
          <img className="stage-media" src={resultUrl} alt="分析后的现场画面" />
        ) : previewUrl ? (
          source === "video" ? (
            <video className="stage-media" src={previewUrl} controls />
          ) : (
            <img className="stage-media" src={previewUrl} alt="待分析画面预览" />
          )
        ) : cameraActive ? (
          <video className="stage-media" ref={videoRef} muted playsInline />
        ) : (
          <div className="scan-placeholder" aria-live="polite">
            <div className="scan-radar" aria-hidden="true">
              <span className="scan-radar__ring scan-radar__ring--one" />
              <span className="scan-radar__ring scan-radar__ring--two" />
              <span className="scan-radar__sweep" />
              <span className="scan-radar__helmet">◠</span>
            </div>
            <strong>
              {source === "photo"
                ? "选择一张现场照片"
                : source === "video"
                  ? "载入一段现场视频"
                  : "开启摄像头，开始现场扫描"}
            </strong>
            <p>检测佩戴状态、识别员工身份，并把本次结果留在本机。</p>
          </div>
        )}
        {cameraActive && (
          <div className="scan-corners" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </div>
        )}
        {detections.length > 0 && (
          <div className="detection-stack">
            {detections.slice(0, 4).map((detection, index) => (
              <DetectionChip
                key={`${detection.employeeNo ?? detection.identity}-${index}`}
                detection={detection}
              />
            ))}
          </div>
        )}
      </div>
      <footer className="stage-footer">
        <span>
          {latestMessage?.type === "collection"
            ? `本次已保存 ${latestMessage.saved ?? 0} 张`
            : latestMessage?.type === "detection"
              ? `发现 ${detections.length} 个有效目标`
              : "本地图像处理 · 不外传"}
        </span>
        <span>CAMERA / {source.toUpperCase()} / LOCAL</span>
      </footer>
    </section>
  );
}
