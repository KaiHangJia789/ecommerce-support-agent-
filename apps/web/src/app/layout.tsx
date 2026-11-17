import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "售后工作台 · P0 演示",
  description: "电商售后多 Agent 工程基础，使用合成数据验证异步工单流程。",
};

/**
 * 功能：提供简体中文页面的 HTML 根布局。
 * 输入：children，当前路由的 React 子节点。
 * 输出：包含 html/body 与 children 的 React 节点。
 */
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
