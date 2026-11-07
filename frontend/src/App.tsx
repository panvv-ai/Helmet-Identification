import { useEffect, useRef, useState } from "react";

import { api } from "./api/client";
import type {
  AttendanceRecord,
  Bootstrap,
  CameraMessage,
  Job,
  Sample,
  Source,
  ViolationRecord,
  Workflow,
} from "./api/types";
import { BrandMark } from "./components/BrandMark";
import { CameraPanel } from "./components/CameraPanel";
import { EmployeeDialog } from "./components/EmployeeDialog";
import { EmployeeLedger } from "./components/EmployeeLedger";
import { JobLedger } from "./components/JobLedger";
import { ModelLedger } from "./components/ModelLedger";
import { RecordPanels } from "./components/RecordPanels";
import { ScanStage } from "./components/ScanStage";
import { SourceSwitch } from "./components/SourceSwitch";
import { WorkflowTabs } from "./components/WorkflowTabs";

function sleep(duration: number) {
  return new Promise((resolve) => window.setTimeout(resolve, duration));
}

export default function App() {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [violations, setViolations] = useState<ViolationRecord[]>([]);
  const [workflow, setWorkflow] = useState<Workflow>("detect");
  const [source, setSource] = useState<Source>("camera");
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [showEmployeeForm, setShowEmployeeForm] = useState(false);
  const [employeeNo, setEmployeeNo] = useState("");
  const [employeeName, setEmployeeName] = useState("");
  const [businessMode, setBusinessMode] = useState(false);
  const [busy, setBusy] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [latestMessage, setLatestMessage] = useState<CameraMessage | null>(null);
  const [toast, setToast] = useState<{ tone: "success" | "error"; text: string } | null>(
    null,
  );
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedEmployee =
    bootstrap?.employees.find((employee) => employee.id === selectedEmployeeId) ?? null;

  async function loadDashboard() {
    try {
      const [dashboard, loadedJobs, loadedAttendance, loadedViolations] = await Promise.all([
        api.bootstrap(),
        api.jobs(),
        fetch("/api/records/attendance").then((response) => response.json()) as Promise<
          AttendanceRecord[]
        >,
        fetch("/api/records/violations").then((response) => response.json()) as Promise<
          ViolationRecord[]
        >,
      ]);
      setBootstrap(dashboard);
      setJobs(loadedJobs);
      setAttendance(loadedAttendance);
      setViolations(loadedViolations);
      setSelectedEmployeeId((current) => current ?? dashboard.employees[0]?.id ?? null);
    } catch (error) {
      setToast({
        tone: "error",
        text: error instanceof Error ? error.message : "工作台加载失败",
      });
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  useEffect(() => {
    if (!selectedEmployeeId) {
      setSamples([]);
      return;
    }
    void api
      .listSamples(selectedEmployeeId)
      .then(setSamples)
      .catch(() => setSamples([]));
  }, [selectedEmployeeId, bootstrap]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 4200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  function selectSource(next: Source) {
    setSource(next);
    setFile(null);
    setPreviewUrl(null);
    setResultUrl(null);
    setLatestMessage(null);
  }

  function chooseFile() {
    fileInputRef.current?.click();
  }

  function onFileSelected(selectedFile: File | null) {
    if (!selectedFile) return;
    setFile(selectedFile);
    setResultUrl(null);
    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);
  }

  async function createEmployee() {
    if (!employeeNo.trim() || !employeeName.trim()) {
      setToast({ tone: "error", text: "请填写员工编号和姓名" });
      return;
    }
    try {
      const created = await api.createEmployee(employeeNo, employeeName);
      setEmployeeNo("");
      setEmployeeName("");
      setShowEmployeeForm(false);
      setSelectedEmployeeId(created.id);
      await loadDashboard();
      setToast({ tone: "success", text: "员工已添加，可以开始采集人脸样本" });
    } catch (error) {
      setToast({
        tone: "error",
        text: error instanceof Error ? error.message : "员工添加失败",
      });
    }
  }

  function closeEmployeeDialog() {
    setShowEmployeeForm(false);
    setEmployeeNo("");
    setEmployeeName("");
  }

  async function collectFile() {
    if (!selectedEmployee || !file) {
      setToast({ tone: "error", text: "请选择员工并载入一张照片" });
      return;
    }
    setBusy(true);
    try {
      const result = await api.uploadSample(selectedEmployee.id, file);
      await loadDashboard();
      setToast({
        tone: "success",
        text: result.saved
          ? "人脸样本已保存"
          : result.duplicates
            ? "这张样本已经存在，无需重复保存"
            : "没有保存新的样本",
      });
    } catch (error) {
      setToast({
        tone: "error",
        text: error instanceof Error ? error.message : "样本采集失败",
      });
    } finally {
      setBusy(false);
    }
  }

  async function trackJob(job: Job) {
    let current = job;
    for (let attempt = 0; attempt < 300; attempt += 1) {
      if (["succeeded", "failed", "interrupted"].includes(current.status)) break;
      await sleep(450);
      current = await api.job(current.id);
      setJobs((items) => [current, ...items.filter((item) => item.id !== current.id)]);
    }
    await loadDashboard();
    if (current.status === "succeeded") {
      const output = (current.result?.outputs as Array<Record<string, unknown>> | undefined)?.[0];
      if (typeof output?.outputPath === "string") {
        setResultUrl(`/api/assets/${output.outputPath}`);
      }
      if (Array.isArray(output?.detections)) {
        setLatestMessage({
          type: "detection",
          detections: output.detections as CameraMessage["detections"],
        });
      }
      setToast({
        tone: "success",
        text: current.kind === "train" ? "身份模型训练完成" : "分析完成，结果已保存在本机",
      });
    } else {
      setToast({
        tone: "error",
        text: current.errorMessage ?? current.message ?? "任务执行失败",
      });
    }
  }

  async function analyzeFile() {
    if (source === "camera") return;
    if (!file) {
      setToast({ tone: "error", text: "请先选择要分析的文件" });
      return;
    }
    if (!bootstrap?.helmetModelReady) {
      setToast({
        tone: "error",
        text: "检测模型尚未安装，请先在终端运行模型下载命令",
      });
      return;
    }
    setBusy(true);
    try {
      const job = await api.analyze(source, [file]);
      setJobs((items) => [job, ...items]);
      await trackJob(job);
    } catch (error) {
      setToast({
        tone: "error",
        text: error instanceof Error ? error.message : "分析任务创建失败",
      });
    } finally {
      setBusy(false);
    }
  }

  async function trainModel() {
    setBusy(true);
    try {
      const job = await api.train();
      setJobs((items) => [job, ...items]);
      await trackJob(job);
    } catch (error) {
      setToast({
        tone: "error",
        text: error instanceof Error ? error.message : "训练任务创建失败",
      });
    } finally {
      setBusy(false);
    }
  }

  async function cameraStopped(saved: number) {
    await loadDashboard();
    if (selectedEmployeeId) {
      setSamples(await api.listSamples(selectedEmployeeId));
    }
    setToast({
      tone: "success",
      text: saved > 0 ? `采集已自动保存 ${saved} 张人脸样本` : "摄像头已停止，会话结果已保存",
    });
  }

  async function deleteEmployee(employeeId: string) {
    if (!window.confirm("停用后当前样本会删除，历史签到和违规记录保留。继续吗？")) return;
    await api.deactivateEmployee(employeeId);
    setSelectedEmployeeId(null);
    await loadDashboard();
    setToast({ tone: "success", text: "员工已停用，历史业务记录已保留" });
  }

  async function deleteSample(sampleId: string) {
    await api.deleteSample(sampleId);
    if (selectedEmployeeId) setSamples(await api.listSamples(selectedEmployeeId));
    await loadDashboard();
    setToast({ tone: "success", text: "样本已删除" });
  }

  async function activateModel(modelId: string) {
    await api.activateModel(modelId);
    await loadDashboard();
    setToast({ tone: "success", text: "已切换当前身份模型" });
  }

  function continueCollect(employeeId: string) {
    setSelectedEmployeeId(employeeId);
    setWorkflow("collect");
    selectSource("camera");
  }

  function handleCameraMessage(message: CameraMessage) {
    setLatestMessage(message);
    if (message.type === "error" && message.message) {
      setToast({ tone: "error", text: message.message });
    }
  }

  if (!bootstrap) {
    return (
      <main className="boot-screen">
        <BrandMark />
        <div className="boot-radar" aria-hidden="true" />
        <p>正在校验本地工作台…</p>
      </main>
    );
  }

  const canTrain =
    bootstrap.employees.length >= 2 &&
    bootstrap.employees.filter((employee) => employee.sampleCount >= 2).length >= 2;
  const cameraMode =
    workflow === "collect" ? "collect" : businessMode ? "business" : "analysis";
  const cameraDisabled =
    workflow === "collect"
      ? !selectedEmployeeId
      : !bootstrap.helmetModelReady;
  const cameraPanel =
    source === "camera" && workflow !== "train" ? (
      <CameraPanel
        mode={cameraMode}
        employeeId={workflow === "collect" ? selectedEmployeeId : null}
        disabled={cameraDisabled}
        onMessage={handleCameraMessage}
        onStopped={cameraStopped}
        onActiveChange={setCameraActive}
      />
    ) : undefined;

  return (
    <main className="app-shell">
      <nav className="top-nav" aria-label="主导航">
        <BrandMark />
        <div className="nav-pills">
          <span className="nav-pill is-active">
            <i />
            工作台
          </span>
          <a href="#people">人员</a>
          <a href="#records">记录</a>
        </div>
        <button type="button" onClick={() => setShowEmployeeForm((value) => !value)}>
          添加员工 <span>＋</span>
        </button>
      </nav>

      <section className="hero">
        <span className="hero-label">HELMET WORKBENCH / LOCAL SAFETY</span>
        <h1>
          看清每一位现场人员，
          <br />
          也看清每一顶安全帽。
        </h1>
        <p>
          在同一张工作台完成人员建档、身份训练、现场检测与每日安全记录。图像和模型只留在本机。
        </p>
        <div className="hero-stats">
          <div>
            <strong>{bootstrap.attendanceToday}</strong>
            <span>今日签到</span>
          </div>
          <div>
            <strong>{bootstrap.violationsToday}</strong>
            <span>今日违规</span>
          </div>
          <div>
            <strong>{bootstrap.employees.length}</strong>
            <span>在册员工</span>
          </div>
          <div>
            <strong>{bootstrap.models.length}</strong>
            <span>身份模型</span>
          </div>
        </div>
      </section>

      {!bootstrap.helmetModelReady && (
        <aside className="model-warning" role="status">
          <span className="warning-icon">!</span>
          <span>
            <strong>检测模型尚未安装</strong>
            <small>
              启动时会自动尝试下载模型；如仍失败，请检查终端网络与模型 Release。
            </small>
          </span>
        </aside>
      )}

      <section className="workbench" id="workflow">
        <ScanStage
          source={source}
          previewUrl={previewUrl}
          busy={busy}
          cameraActive={cameraActive}
          latestMessage={latestMessage}
          resultUrl={resultUrl}
          cameraPanel={cameraPanel}
        />

        <aside className="run-console panel">
          <div className="panel__head">
            <div>
              <span className="eyebrow">RUN CONSOLE</span>
              <h2>现场工作台</h2>
            </div>
            <span className="console-index">01 / LIVE</span>
          </div>

          <WorkflowTabs value={workflow} onChange={setWorkflow} />

          {workflow !== "train" && (
            <>
              <div className="field-label">
                <span>数据来源</span>
                <small>{source.toUpperCase()}</small>
              </div>
              <SourceSwitch value={source} onChange={selectSource} />
            </>
          )}

          {workflow === "collect" && (
            <div className="console-section">
              <label className="field-label" htmlFor="employee-select">
                <span>采集对象</span>
                <small>DATASET</small>
              </label>
              <select
                id="employee-select"
                value={selectedEmployeeId ?? ""}
                onChange={(event) => setSelectedEmployeeId(event.target.value || null)}
              >
                <option value="">请选择员工</option>
                {bootstrap.employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.employeeNo} · {employee.name}
                  </option>
                ))}
              </select>
              {source === "camera" ? (
                <div className="stage-action-hint">
                  <span className="eyebrow">CAMERA READY</span>
                  <strong>
                    {selectedEmployee
                      ? `准备采集 ${selectedEmployee.name} 的人脸`
                      : "先选择采集对象"}
                  </strong>
                  <p>在左侧“现场画面”中开启和停止摄像头。</p>
                </div>
              ) : (
                <>
                  <input
                    ref={fileInputRef}
                    className="visually-hidden"
                    type="file"
                    accept={source === "photo" ? "image/*" : "video/*"}
                    onChange={(event) => onFileSelected(event.target.files?.[0] ?? null)}
                  />
                  <button type="button" className="upload-zone" onClick={chooseFile}>
                    <span>{file ? "已选择文件" : "载入采集文件"}</span>
                    <strong>{file?.name ?? "选择照片或视频文件"}</strong>
                  </button>
                  <button
                    type="button"
                    className="primary-action"
                    disabled={busy || !selectedEmployee || !file}
                    onClick={collectFile}
                  >
                    {source === "photo" ? "提取并保存人脸" : "从视频采集人脸"}
                  </button>
                </>
              )}
              <p className="privacy-note">
                仅保存本机可识别的人脸样本；重复画面会自动去重。
              </p>
            </div>
          )}

          {workflow === "train" && (
            <div className="console-section train-section">
              <div className="train-meter">
                <span className="eyebrow">TRAINING READINESS</span>
                <strong>{canTrain ? "样本已满足训练条件" : "还需要更多样本"}</strong>
                <p>
                  至少 2 名员工，每人至少 2 张可读人脸。训练会固定随机种子并使用分层验证。
                </p>
                <div className="train-readiness">
                  {bootstrap.employees.map((employee) => (
                    <div key={employee.id}>
                      <span>
                        {employee.name}
                        <small>{employee.employeeNo}</small>
                      </span>
                      <strong className={employee.sampleCount >= 2 ? "is-ready" : ""}>
                        {employee.sampleCount}/2
                      </strong>
                    </div>
                  ))}
                </div>
              </div>
              <button
                type="button"
                className="primary-action"
                disabled={busy || !canTrain}
                onClick={trainModel}
              >
                <span aria-hidden="true">⌁</span>
                训练身份模型
              </button>
              <p className="privacy-note">安全帽检测模型使用固定版本，不在此处重训。</p>
            </div>
          )}

          {workflow === "detect" && (
            <div className="console-section">
              {source === "camera" ? (
                <>
                  <label className="mode-toggle">
                    <input
                      type="checkbox"
                      checked={businessMode}
                      onChange={(event) => setBusinessMode(event.target.checked)}
                    />
                    <span>
                      <strong>业务模式</strong>
                      <small>业务模式会写入签到与违规记录</small>
                    </span>
                  </label>
                  <div className="stage-action-hint">
                    <span className="eyebrow">CAMERA CONTROL</span>
                    <strong>
                      {businessMode ? "业务记录模式已启用" : "实时分析模式"}
                    </strong>
                    <p>摄像头启动与停止按钮位于左侧“现场画面”底部。</p>
                  </div>
                </>
              ) : (
                <>
                  <input
                    ref={fileInputRef}
                    className="visually-hidden"
                    type="file"
                    accept={source === "photo" ? "image/*" : "video/*"}
                    onChange={(event) => onFileSelected(event.target.files?.[0] ?? null)}
                  />
                  <button type="button" className="upload-zone" onClick={chooseFile}>
                    <span>{file ? "待分析文件" : "分析本地文件"}</span>
                    <strong>{file?.name ?? "选择照片或视频"}</strong>
                  </button>
                  <button
                    type="button"
                    className="primary-action"
                    disabled={busy || !file || !bootstrap.helmetModelReady}
                    onClick={analyzeFile}
                  >
                    开始现场分析
                  </button>
                </>
              )}
              <div className="active-model">
                <span>当前身份模型</span>
                <strong>{bootstrap.activeModel?.name ?? "尚未启用"}</strong>
                <small>
                  {bootstrap.activeModel
                    ? `识别阈值 ${bootstrap.activeModel.threshold.toFixed(2)}`
                    : "未启用时仍可检测安全帽，但身份显示为未知"}
                </small>
              </div>
            </div>
          )}
        </aside>
      </section>

      <section className="ledger-grid" id="people">
        <EmployeeLedger
          employees={bootstrap.employees}
          selectedId={selectedEmployeeId}
          samples={samples}
          onSelect={setSelectedEmployeeId}
          onContinue={continueCollect}
          onDeleteEmployee={deleteEmployee}
          onDeleteSample={deleteSample}
        />
        <ModelLedger models={bootstrap.models} onActivate={activateModel} />
      </section>

      <div id="records">
        <RecordPanels attendance={attendance} violations={violations} />
      </div>

      <JobLedger jobs={jobs} />

      <footer className="site-footer">
        <BrandMark />
        <p>Helmet Workbench · 本地优先的安全帽识别工作台</p>
        <span>MIT · LOCAL ONLY</span>
      </footer>

      <EmployeeDialog
        open={showEmployeeForm}
        employeeNo={employeeNo}
        name={employeeName}
        onEmployeeNoChange={setEmployeeNo}
        onNameChange={setEmployeeName}
        onSubmit={createEmployee}
        onClose={closeEmployeeDialog}
      />

      {toast && (
        <div className={`toast toast--${toast.tone}`} role="status">
          <span>{toast.tone === "success" ? "✓" : "!"}</span>
          {toast.text}
          <button type="button" onClick={() => setToast(null)} aria-label="关闭提示">
            ×
          </button>
        </div>
      )}
    </main>
  );
}
