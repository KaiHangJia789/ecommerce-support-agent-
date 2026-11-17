import TicketDemo from "../components/ticket-demo";

/**
 * 功能：渲染首页的项目边界说明与工单演示工作台。
 * 输入：无。
 * 输出：React 页面节点，包含 TicketDemo 交互组件。
 */
export default function Home() {
  return (
    <main>
      <header className="topbar"><span className="brand">工单 / SUPPORT</span><span className="badge">P0 · MOCK</span></header>
      <section className="intro"><p className="eyebrow">电商售后 · 工程基础演示</p>
        <h1>让每一个售后问题<br />都有迹可循。</h1>
        <p className="description">提交一条合成工单，观察数据库、任务队列与 LangGraph 的完整处理链路。</p>
      </section>
      <aside className="notice">当前使用确定性规则和合成订单，不调用真实模型或物流，不执行退款。图片理解、人工审批与真实模型将在后续阶段接入。</aside>
      <TicketDemo />
      <footer>FastAPI / PostgreSQL / Redis / Celery / LangGraph · 本地演示专用</footer>
    </main>
  );
}
