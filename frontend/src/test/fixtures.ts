import type { Bootstrap } from "../api/types";

export const bootstrapFixture: Bootstrap = {
  employees: [
    {
      id: "employee-1",
      employeeNo: "A-1001",
      name: "演示员工甲",
      active: true,
      sampleCount: 4,
      createdAt: "2026-11-07T08:00:00Z",
    },
    {
      id: "employee-2",
      employeeNo: "A-1002",
      name: "演示员工乙",
      active: true,
      sampleCount: 3,
      createdAt: "2026-11-07T08:10:00Z",
    },
  ],
  models: [],
  activeModel: null,
  helmetModelReady: false,
  settings: {
    shiftStart: "08:00",
    evidenceEnabled: true,
    threshold: 0.7,
    cameraMaxFps: 6,
  },
  attendanceToday: 12,
  violationsToday: 2,
};
