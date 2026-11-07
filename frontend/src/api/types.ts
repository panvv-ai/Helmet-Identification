export type Source = "photo" | "video" | "camera";
export type Workflow = "collect" | "train" | "detect";
export type CameraMode = "collect" | "analysis" | "business";

export interface Employee {
  id: string;
  employeeNo: string;
  name: string;
  active: boolean;
  sampleCount: number;
  createdAt: string;
}

export interface Model {
  id: string;
  name: string;
  active: boolean;
  threshold: number;
  metrics: Record<string, number>;
  createdAt: string;
}

export interface Settings {
  shiftStart: string;
  evidenceEnabled: boolean;
  threshold: number;
  cameraMaxFps: number;
}

export interface Bootstrap {
  employees: Employee[];
  models: Model[];
  activeModel: Model | null;
  helmetModelReady: boolean;
  settings: Settings;
  attendanceToday: number;
  violationsToday: number;
}

export interface Sample {
  id: string;
  imageUrl: string;
  createdAt: string;
}

export interface Job {
  id: string;
  kind: string;
  status: string;
  progress: number;
  message: string;
  result?: Record<string, unknown> | null;
  errorCode?: string | null;
  errorMessage?: string | null;
  createdAt: string;
}

export interface Detection {
  box: { x: number; y: number; width: number; height: number };
  helmetState: "with_helmet" | "without_helmet" | "unknown";
  helmetConfidence: number;
  identity: string;
  employeeNo?: string | null;
  identityConfidence: number;
}

export interface CameraMessage {
  type: "session" | "collection" | "detection" | "error";
  sessionId?: string;
  mode?: string;
  saved?: number;
  duplicates?: number;
  detected?: number;
  detections?: Detection[];
  message?: string;
  actions?: string[];
  alertCount?: number;
}

export interface AttendanceRecord {
  id: string;
  employeeNo: string;
  employeeName: string;
  date: string;
  occurredAt: string;
  late: boolean;
  evidenceUrl?: string | null;
}

export interface ViolationRecord {
  id: string;
  employeeNo: string;
  employeeName: string;
  date: string;
  occurredAt: string;
  evidenceUrl?: string | null;
}
