import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { bootstrapFixture } from "./test/fixtures";

const fetchMock = vi.fn();

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

function jsonResponse(payload: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("Helmet Workbench", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
    fetchMock.mockImplementation((input: string) => {
      if (input === "/api/bootstrap") return jsonResponse(bootstrapFixture);
      if (input === "/api/jobs") return jsonResponse([]);
      if (input === "/api/records/attendance") return jsonResponse([]);
      if (input === "/api/records/violations") return jsonResponse([]);
      if (input === "/api/employees/employee-1/samples") return jsonResponse([]);
      if (input === "/api/employees/employee-2/samples") return jsonResponse([]);
      return jsonResponse({});
    });
  });

  it("switches source and exposes the business-mode warning", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("现场工作台");

    await user.click(screen.getByRole("tab", { name: /检测/ }));

    expect(screen.getByText("业务模式会写入签到与违规记录")).toBeInTheDocument();
    expect(screen.queryByText(/OpenCV|TensorFlow|SQLite/)).not.toBeInTheDocument();
  });

  it("shows missing helmet model guidance", async () => {
    render(<App />);
    expect(await screen.findByText("检测模型尚未安装")).toBeInTheDocument();
  });

  it("creates an employee and refreshes the ledger", async () => {
    const user = userEvent.setup();
    fetchMock.mockImplementation((input: string, options?: RequestInit) => {
      if (input === "/api/bootstrap") return jsonResponse(bootstrapFixture);
      if (input === "/api/employees" && options?.method === "POST") {
        return jsonResponse(
          {
            id: "employee-3",
            employeeNo: "A-1003",
            name: "王五",
            active: true,
            sampleCount: 0,
            createdAt: "2026-11-07T08:00:00Z",
          },
          201,
        );
      }
      if (input === "/api/jobs") return jsonResponse([]);
      if (input === "/api/records/attendance") return jsonResponse([]);
      if (input === "/api/records/violations") return jsonResponse([]);
      if (input === "/api/employees/employee-1/samples") return jsonResponse([]);
      if (input === "/api/employees/employee-2/samples") return jsonResponse([]);
      return jsonResponse({});
    });
    render(<App />);
    await screen.findByText("现场工作台");

    await user.click(screen.getByRole("button", { name: /添加员工/ }));
    const dialog = await screen.findByRole("dialog", { name: "添加员工" });
    await user.type(within(dialog).getByLabelText("员工编号"), "A-1003");
    await user.type(within(dialog).getByLabelText("姓名"), "王五");
    await user.click(within(dialog).getByRole("button", { name: "确认添加" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/employees",
        expect.objectContaining({ method: "POST" }),
      );
    });
    await waitFor(() => expect(document.body.style.overflow).toBe(""));
  });

  it("keeps a stop control available after camera startup", async () => {
    fetchMock.mockImplementation((input: string) => {
      if (input === "/api/bootstrap") {
        return jsonResponse({ ...bootstrapFixture, helmetModelReady: true });
      }
      if (input === "/api/jobs") return jsonResponse([]);
      if (input === "/api/records/attendance") return jsonResponse([]);
      if (input === "/api/records/violations") return jsonResponse([]);
      if (input === "/api/employees/employee-1/samples") return jsonResponse([]);
      if (input === "/api/employees/employee-2/samples") return jsonResponse([]);
      return jsonResponse({});
    });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue({
          getTracks: () => [{ stop: vi.fn() }],
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
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "现场工作台" });

    await user.click(screen.getByRole("button", { name: /开启摄像头/ }));

    expect(
      await screen.findByRole("button", { name: /停止并保存结果/ }),
    ).toBeInTheDocument();
  });
});
