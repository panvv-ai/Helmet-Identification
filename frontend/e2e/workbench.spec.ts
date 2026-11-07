import { expect, test } from "@playwright/test";

const bootstrap = {
  employees: [
    {
      id: "employee-1",
      employeeNo: "DEMO-01",
      name: "演示员工甲",
      active: true,
      sampleCount: 3,
      createdAt: "2026-11-07T08:00:00Z",
    },
    {
      id: "employee-2",
      employeeNo: "DEMO-02",
      name: "演示员工乙",
      active: true,
      sampleCount: 3,
      createdAt: "2026-11-07T08:00:00Z",
    },
  ],
  models: [
    {
      id: "model-1",
      name: "人脸模型 2 类",
      active: true,
      threshold: 0.7,
      metrics: { macroF1: 0.92 },
      createdAt: "2026-11-07T08:30:00Z",
    },
  ],
  activeModel: {
    id: "model-1",
    name: "人脸模型 2 类",
    active: true,
    threshold: 0.7,
    metrics: { macroF1: 0.92 },
    createdAt: "2026-11-07T08:30:00Z",
  },
  helmetModelReady: true,
  settings: {
    shiftStart: "08:00",
    evidenceEnabled: true,
    threshold: 0.7,
    cameraMaxFps: 6,
  },
  attendanceToday: 2,
  violationsToday: 0,
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/bootstrap", (route) =>
    route.fulfill({ json: bootstrap }),
  );
  await page.route("**/api/jobs", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/records/attendance", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.route("**/api/records/violations", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.route("**/api/employees/employee-1/samples", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.route("**/api/employees/employee-3/samples", (route) =>
    route.fulfill({ json: [] }),
  );
  await page.route("**/api/employees", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 201,
        json: {
          id: "employee-3",
          employeeNo: "DEMO-03",
          name: "演示员工丙",
          active: true,
          sampleCount: 0,
          createdAt: "2026-11-07T09:00:00Z",
        },
      });
      return;
    }
    await route.fulfill({ json: bootstrap.employees });
  });
});

test("workflow and employee creation render on desktop", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /看清每一位现场人员/ })).toBeVisible();
  await page.getByRole("button", { name: /添加员工/ }).click();
  await page.getByLabel("员工编号").fill("DEMO-03");
  await page.getByLabel("姓名").fill("演示员工丙");
  await page.getByRole("button", { name: "确认添加" }).click();
  await expect(page.getByText("员工已添加，可以开始采集人脸样本")).toBeVisible();
  await page.getByRole("tab", { name: /训练/ }).click();
  await expect(page.getByText("样本已满足训练条件")).toBeVisible();
});

test("camera permission failure is explained without breaking layout", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: () =>
          Promise.reject(new Error("摄像头权限被拒绝，请在浏览器设置中允许访问")),
      },
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: /开启摄像头/ }).click();
  await expect(page.getByText(/摄像头权限被拒绝/)).toBeVisible();
  await expect(page.locator("main")).toBeVisible();
});

test("mobile viewport has no horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await expect(page.getByText("现场工作台")).toBeVisible();
  const dimensions = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    client: document.documentElement.clientWidth,
  }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.client + 1);
});
