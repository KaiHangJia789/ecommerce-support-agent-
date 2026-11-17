from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class SupportState(TypedDict, total=False):
    message: str
    order_id: str | None
    shipment_status: str | None
    intent: str
    mode: str
    reply: str
    ticket_status: str
    state_schema_version: int


def classify(state: SupportState) -> dict:
    """功能：按关键词确定性分类售后意图，并显式标记 Mock 模式。

    输入：state：必须包含 message 的工作流状态。
    输出：dict：intent、mode=mock、state_schema_version=1 的状态增量。
    """
    message = state["message"].lower()
    categories = (
        ("damage", ("破损", "坏了", "damage")),
        ("refund", ("退款", "refund")),
        ("return", ("退货", "return")),
        ("logistics", ("物流", "快递", "发货", "shipment", "delivery")),
    )
    intent = next((name for name, words in categories if any(w in message for w in words)), "other")
    return {"intent": intent, "mode": "mock", "state_schema_version": 1}


def compose_reply(state: SupportState) -> dict:
    """功能：依据合成订单物流和意图生成模拟回复及工单状态。

    输入：state：含 intent、可选 shipment_status/order_id 的工作流状态。
    输出：dict：reply 与 ticket_status；不调用真实物流，也不执行退款/退货。
    """
    if state.get("shipment_status") is None:
        return {
            "reply": "【模拟演示】未找到合成订单，请使用 DEMO-1001 或 DEMO-1002 补充查询。",
            "ticket_status": "waiting_customer",
        }
    if state["intent"] == "logistics":
        status = {"delayed": "运输延迟", "delivered": "已签收"}.get(
            state["shipment_status"], "待核实"
        )
        return {
            "reply": f"【模拟演示】合成订单 {state['order_id']} 的物流状态为：{status}。"
            "此结果来自演示数据，未联系真实物流。",
            "ticket_status": "resolved",
        }
    return {
        "reply": "【模拟演示】问题已归类；P0 尚未实现该售后处置，请等待人工处理。"
        "系统不会执行退款或退货。",
        "ticket_status": "waiting_approval",
    }


def build_graph(checkpointer):
    """功能：组装分类与回复两个节点的线性 LangGraph 工作流。

    输入：checkpointer：检查点存储对象，测试可使用内存实现。
    输出：已编译图，可通过 invoke 执行并通过 get_state 读取检查点。
    """
    builder = StateGraph(SupportState)
    builder.add_node("classify_mock", classify)
    builder.add_node("compose_mock", compose_reply)
    builder.add_edge(START, "classify_mock")
    builder.add_edge("classify_mock", "compose_mock")
    builder.add_edge("compose_mock", END)
    return builder.compile(checkpointer=checkpointer)
