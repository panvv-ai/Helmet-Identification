import { useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";

interface EmployeeDialogProps {
  open: boolean;
  employeeNo: string;
  name: string;
  onEmployeeNoChange: (value: string) => void;
  onNameChange: (value: string) => void;
  onSubmit: () => void;
  onClose: () => void;
}

export function EmployeeDialog({
  open,
  employeeNo,
  name,
  onEmployeeNoChange,
  onNameChange,
  onSubmit,
  onClose,
}: EmployeeDialogProps) {
  const titleId = useId();
  const descriptionId = useId();
  const employeeNoRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.setTimeout(() => employeeNoRef.current?.focus(), 0);

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = panelRef.current?.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        className="employee-modal panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
      >
        <div className="employee-modal__accent" aria-hidden="true" />
        <button
          type="button"
          className="employee-modal__close"
          aria-label="关闭添加员工弹窗"
          onClick={onClose}
        >
          ×
        </button>
        <div className="employee-modal__head">
          <span className="eyebrow">NEW PROFILE / 01</span>
          <h2 id={titleId}>添加员工</h2>
          <p id={descriptionId}>
            建立身份档案后，可继续从摄像头或照片采集训练样本。
          </p>
        </div>
        <form
          className="employee-modal__form"
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit();
          }}
        >
          <label>
            <span>员工编号</span>
            <input
              ref={employeeNoRef}
              aria-label="员工编号"
              value={employeeNo}
              onChange={(event) => onEmployeeNoChange(event.target.value)}
              placeholder="例如 A-1001"
              autoComplete="off"
            />
            <small>用于签到、违规记录和模型标签，保存后仍可修改。</small>
          </label>
          <label>
            <span>姓名</span>
            <input
              aria-label="姓名"
              value={name}
              onChange={(event) => onNameChange(event.target.value)}
              placeholder="例如 示例员工"
              autoComplete="off"
            />
          </label>
          <div className="employee-modal__actions">
            <button type="button" className="secondary-action" onClick={onClose}>
              取消
            </button>
            <button type="submit" className="primary-action">
              确认添加
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
}
