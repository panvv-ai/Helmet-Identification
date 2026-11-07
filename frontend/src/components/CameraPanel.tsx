import { useEffect, useRef, useState } from "react";

import type { CameraMessage } from "../api/types";

interface CameraPanelProps {
  mode: "collect" | "analysis" | "business";
  employeeId: string | null;
  disabled: boolean;
  onMessage: (message: CameraMessage) => void;
  onStopped: (saved: number) => Promise<void>;
  onActiveChange: (active: boolean) => void;
}

const modeLabels = {
  collect: "人脸样本采集",
  analysis: "实时画面检测",
  business: "签到与违规记录",
};

export function CameraPanel({
  mode,
  employeeId,
  disabled,
  onMessage,
  onStopped,
  onActiveChange,
}: CameraPanelProps) {
  const [active, setActive] = useState(false);
  const [saved, setSaved] = useState(0);
  const [frameCount, setFrameCount] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      socketRef.current?.close();
      if (timerRef.current !== null) window.clearInterval(timerRef.current);
    };
  }, []);

  async function start() {
    if (!navigator.mediaDevices?.getUserMedia) {
      onMessage({ type: "error", message: "当前浏览器无法访问摄像头" });
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 } },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) {
        stream.getTracks().forEach((track) => track.stop());
        onMessage({ type: "error", message: "摄像头画面尚未准备好" });
        return;
      }
      video.srcObject = stream;
      await video.play();
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const query = new URLSearchParams({ mode });
      if (employeeId) query.set("employee_id", employeeId);
      const socket = new WebSocket(
        `${protocol}://${window.location.host}/api/ws/camera?${query.toString()}`,
      );
      socket.binaryType = "arraybuffer";
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data as string) as CameraMessage;
        if (message.type === "collection" && message.saved) {
          setSaved((current) => current + (message.saved ?? 0));
        }
        if (message.type === "detection") {
          setFrameCount((current) => current + 1);
        }
        onMessage(message);
      };
      socket.onerror = () => onMessage({ type: "error", message: "摄像头连接已中断" });
      socketRef.current = socket;
      await new Promise<void>((resolve) => {
        socket.addEventListener("open", () => resolve(), { once: true });
      });
      setSaved(0);
      setFrameCount(0);
      setActive(true);
      onActiveChange(true);
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");
      timerRef.current = window.setInterval(() => {
        if (
          socket.readyState !== WebSocket.OPEN ||
          video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
          !context
        ) {
          return;
        }
        const longest = Math.max(video.videoWidth, video.videoHeight);
        const scale = longest > 960 ? 960 / longest : 1;
        canvas.width = Math.round(video.videoWidth * scale);
        canvas.height = Math.round(video.videoHeight * scale);
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob(
          (blob) => {
            if (blob) socket.send(blob);
          },
          "image/jpeg",
          0.78,
        );
      }, 1000 / 6);
    } catch (error) {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      onMessage({
        type: "error",
        message: error instanceof Error ? error.message : "摄像头启动失败",
      });
    }
  }

  async function stop() {
    if (timerRef.current !== null) window.clearInterval(timerRef.current);
    timerRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    socketRef.current?.close();
    socketRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setActive(false);
    onActiveChange(false);
    await onStopped(saved);
  }

  return (
    <div className={`camera-unit ${active ? "is-active" : ""}`}>
      <video
        ref={videoRef}
        className="camera-unit__video"
        aria-label="摄像头实时画面"
        muted
        playsInline
      />
      {!active && (
        <div className="camera-unit__empty" aria-live="polite">
          <div className="scan-radar" aria-hidden="true">
            <span className="scan-radar__ring scan-radar__ring--one" />
            <span className="scan-radar__ring scan-radar__ring--two" />
            <span className="scan-radar__sweep" />
            <span className="scan-radar__helmet">◠</span>
          </div>
          <strong>
            {mode === "collect" ? "对准员工，开始采集人脸" : "开启摄像头，开始现场检测"}
          </strong>
          <p>{modeLabels[mode]} · 画面只在本机处理</p>
        </div>
      )}
      <div className="camera-unit__control">
        <div className="camera-unit__meta">
          <span className={active ? "pulse-dot is-live" : "pulse-dot"} />
          <span>
            <strong>{active ? modeLabels[mode] : "摄像头待机"}</strong>
            <small>
              {active
                ? mode === "collect"
                  ? `已保存 ${saved} 张 · 持续采集`
                  : `已处理 ${frameCount} 帧 · 实时分析`
                : "启动后可在同一画面停止并保存"}
            </small>
          </span>
        </div>
        <button
          type="button"
          className={active ? "camera-action is-stop" : "camera-action"}
          disabled={disabled}
          onClick={active ? stop : start}
        >
          <span aria-hidden="true">{active ? "■" : "◉"}</span>
          {active ? "停止并保存结果" : "开启摄像头"}
        </button>
      </div>
    </div>
  );
}
