"use client";

import { useEffect, useState } from "react";

type Submission = { ticket_id: string; run_id: string };
type Run = { run_id: string; status: string; attempts: number; error_code: string | null;
  result: { intent: string; mode: string; reply: string; ticket_status: string } | null };

const names: Record<string, string> = {
  queued: "已入库，等待执行", running: "正在处理", succeeded: "处理完成", failed: "处理失败",
  logistics: "物流查询", damage: "商品破损", refund: "退款", return: "退货", other: "其他问题",
  resolved: "已回复，尚未关闭", waiting_customer: "等待补充信息", waiting_approval: "待人工处理（功能待接入）",
};

/**
 * 功能：显示合成工单表单，提交任务并轮询展示 Mock 处理结果。
 * 输入：无组件参数；用户输入令牌、合成订单号和消息。
 * 输出：React 页面节点；更新组件状态并请求同源 API，令牌仅保存在内存。
 */
export default function TicketDemo() {
  const [token, setToken] = useState("");
  const [order, setOrder] = useState("DEMO-1001");
  const [message, setMessage] = useState("我的订单物流一直没有更新，能帮我查询吗？");
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [pollKey, setPollKey] = useState(0);

  // 功能：建立当前执行的轮询；输入：submission/token/pollKey 闭包；输出：清理回调或 undefined。
  useEffect(() => {
    if (!submission) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    let attempts = 0;
    /**
     * 功能：读取执行状态，未结束时继续轮询，最多发起 120 次查询。
     * 输入：无参数；闭包读取执行 ID、令牌、取消信号与尝试次数。
     * 输出：Promise<void>；更新 run/error 状态及下一次计时器。
     */
    const poll = async () => {
      try {
        const response = await fetch(`/api/v1/runs/${submission.run_id}`, {
          headers: { Authorization: `Bearer ${token}` }, signal: controller.signal, cache: "no-store",
        });
        if (!response.ok) throw new Error("查询失败，请检查令牌与服务状态后重试。");
        const result: Run = await response.json();
        setRun(result);
        if (!["succeeded", "failed"].includes(result.status)) {
          if (++attempts >= 120) throw new Error("任务仍在等待，已暂停轮询。工单已保存，可稍后重试查询。");
          timer = setTimeout(poll, 1000);
        }
      } catch (err) {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "查询失败");
      }
    };
    poll();
    // 功能：停止旧轮询；输入：闭包中的 controller/timer；输出：void，取消请求与计时器。
    return () => { controller.abort(); clearTimeout(timer); };
  }, [submission, token, pollKey]);

  /**
   * 功能：阻止表单跳转，创建工单并触发执行状态轮询。
   * 输入：event 表单提交事件；闭包中的 token/order/message。
   * 输出：Promise<void>；更新 submission、busy、run、error，失败显示可读提示。
   */
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(""); setBusy(true); setRun(null); setSubmission(null);
    try {
      const response = await fetch("/api/v1/tickets", {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message, order_id: order || null }),
      });
      if (!response.ok) throw new Error(response.status === 401 ? "演示令牌无效，请从本机 .env 填入。" : "提交失败，请检查输入与服务状态。");
      setSubmission(await response.json());
    } catch (err) { setError(err instanceof Error ? err.message : "提交失败"); }
    finally { setBusy(false); }
  }

  return (
    <div className="workspace">
      <section className="card"><div className="section-title"><span className="step">01</span><h2>提交售后问题</h2></div>
        <form onSubmit={submit}>
          <label htmlFor="token">本机演示令牌</label>
          {/* 功能：更新内存令牌；输入：输入框变更事件 e；输出：void，设置 token。 */}
          <input id="token" type="password" value={token} onChange={e => setToken(e.target.value)} minLength={32} required autoComplete="off" placeholder="复制 .env 中的 DEMO_API_TOKEN" />
          <p className="hint">仅保存在当前页面内存，刷新后清除。请勿填入云服务密钥。</p>
          <label htmlFor="order">合成订单号</label>
          {/* 功能：更新合成订单号；输入：输入框变更事件 e；输出：void，设置 order。 */}
          <input id="order" value={order} onChange={e => setOrder(e.target.value)} maxLength={64} pattern="[A-Za-z0-9_\-]*" />
          <p className="hint">DEMO-1001：运输延迟 / DEMO-1002：已签收</p>
          <label htmlFor="message">问题描述</label>
          {/* 功能：更新问题描述；输入：文本域变更事件 e；输出：void，设置 message。 */}
          <textarea id="message" value={message} onChange={e => setMessage(e.target.value)} required maxLength={4000} rows={4} />
          <button disabled={busy || !message.trim() || token.length < 32} type="submit">{busy ? "正在提交…" : "提交演示工单 →"}</button>
        </form>
      </section>
      <section className="card result" aria-live="polite"><div className="section-title"><span className="step">02</span><h2>查看处理结果</h2></div>
        {submission ? <>
          <p className="status"><span className="dot" />{run ? names[run.status] || run.status : "正在读取任务状态"}</p>
          <dl><dt>工单编号</dt><dd>{submission.ticket_id}</dd><dt>执行编号</dt><dd>{submission.run_id}</dd></dl>
          {run?.result ? <><div className="result-tags"><span>{names[run.result.intent] || run.result.intent}</span><span>模拟模式</span></div>
            <p className="reply">{run.result.reply}</p><p className="hint">工单状态：{names[run.result.ticket_status] || run.result.ticket_status}</p></> : <p className="hint">任务已写入数据库。Worker 启动后将自动消费。</p>}
          {run?.status === "failed" ? <p role="alert">后台执行失败。错误代码：{run.error_code}，请检查 Worker 日志。</p> : null}
          {/* 功能：清除错误并重新轮询；输入：点击事件（不使用）；输出：void，更新 error/pollKey。
              内层更新函数功能：递增轮询版本；输入：旧值 k；输出：k + 1。 */}
          <button className="secondary" type="button" onClick={() => { setError(""); setPollKey(k => k + 1); }}>重新查询当前任务</button>
        </> : <div className="empty"><span>↗</span><h3>从一条工单开始</h3><p>左侧提交后，这里会显示执行状态、分类与模拟回复。</p></div>}
        {error ? <p className="error" role="alert">{error}</p> : null}
      </section>
    </div>
  );
}
