import type {
  Bootstrap,
  Employee,
  Job,
  Model,
  Sample,
  Settings,
} from "./types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `请求失败 (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: string };
      message = payload.detail ?? message;
    } catch {
      // Keep the HTTP fallback.
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export const api = {
  bootstrap: () => request<Bootstrap>("/api/bootstrap"),
  createEmployee: (employeeNo: string, name: string) =>
    request<Employee>("/api/employees", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ employeeNo, name }),
    }),
  deactivateEmployee: (employeeId: string) =>
    request<{ deleted: boolean }>(`/api/employees/${employeeId}`, { method: "DELETE" }),
  listSamples: (employeeId: string) =>
    request<Sample[]>(`/api/employees/${employeeId}/samples`),
  deleteSample: (sampleId: string) =>
    request<{ deleted: boolean }>(`/api/samples/${sampleId}`, { method: "DELETE" }),
  uploadSample: async (employeeId: string, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<{ detected: number; saved: number; duplicates: number }>(
      `/api/employees/${employeeId}/samples`,
      { method: "POST", body },
    );
  },
  train: () => request<Job>("/api/jobs/train", { method: "POST" }),
  analyze: async (source: "photo" | "video", files: File[]) => {
    const body = new FormData();
    body.append("source", source);
    files.forEach((file) => body.append("files", file));
    return request<Job>("/api/jobs/analyze", { method: "POST", body });
  },
  job: (jobId: string) => request<Job>(`/api/jobs/${jobId}`),
  jobs: () => request<Job[]>("/api/jobs"),
  models: () => request<Model[]>("/api/models"),
  activateModel: (modelId: string) =>
    request<Model>(`/api/models/${modelId}/activate`, { method: "POST" }),
  updateSettings: (payload: Partial<Settings>) =>
    request<Settings>("/api/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
};
