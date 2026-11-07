import { useEffect, useRef, useState } from "react";

import type { CameraMessage } from "../api/types";

interface CameraPanelProps {
  mode: "collect" | "analysis" | "business";
  employeeId: string | null;
  disabled: boolean;
  onMessage: (message: CameraMessage) => void;
  onStopped: (saved: number) => Promise<void>;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  onActiveChange: (active: boolean) => void;
}

export function CameraPanel({
  mode,
  employeeId,
  disabled,
  onMessage,
  onStopped,
  videoRef,
  onActiveChange,
}: CameraPanelProps) {
  const [active, setActive] = useState(false);
  const [saved, setSaved] = useState(0);
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
      if (!video) return;
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
        onMessage(message);
      };
      socket.onerror = () => onMessage({ type: "error", message: "摄像头连接已中断" });
      socketRef.current = socket;
      await new Promise<void>((resolve) => {
        socket.addEventListener("open", () => resolve(), { once: true });
      });
      setSaved(0);
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
    <button
      type="button"
      className={active ? "primary-action is-stop" : "primary-action"}
      disabled={disabled}
      onClick={active ? stop : start}
    >
      <span aria-hidden="true">{active ? "■" : "◉"}</span>
      {active ? "停止并保存结果" : "开启摄像头"}
    </button>
  );
}
