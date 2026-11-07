import { createRef } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CameraPanel } from "./CameraPanel";

class FakeWebSocket {
  static OPEN = 1;
  readyState = FakeWebSocket.OPEN;
  listeners = new Map<string, () => void>();

  addEventListener(event: string, listener: () => void) {
    this.listeners.set(event, listener);
    if (event === "open") queueMicrotask(listener);
  }

  close() {
    this.readyState = 3;
  }

  send() {}
}

describe("CameraPanel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("finishes the session and reports automatic save when stopped", async () => {
    const stopTrack = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({
          getTracks: () => [{ stop: stopTrack }],
        }),
      },
    });
    vi.stubGlobal("WebSocket", FakeWebSocket);
    vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
      drawImage: vi.fn(),
    } as unknown as CanvasRenderingContext2D);
    vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation((callback) => {
      callback(new Blob(["frame"], { type: "image/jpeg" }));
    });
    const onStopped = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    const videoRef = createRef<HTMLVideoElement>();
    render(
      <>
        <video ref={videoRef} />
        <CameraPanel
          mode="collect"
          employeeId="employee-1"
          disabled={false}
          onMessage={() => undefined}
          onStopped={onStopped}
          videoRef={videoRef}
          onActiveChange={() => undefined}
        />
      </>,
    );

    await user.click(screen.getByRole("button", { name: /开启摄像头/ }));
    await screen.findByRole("button", { name: /停止并保存结果/ });
    await user.click(screen.getByRole("button", { name: /停止并保存结果/ }));

    await waitFor(() => expect(onStopped).toHaveBeenCalledWith(0));
    expect(stopTrack).toHaveBeenCalled();
  });
});
