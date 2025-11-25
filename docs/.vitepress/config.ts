import { defineConfig } from "vitepress";
import readmeSidebar from "../readme/readme-sidebar.json";

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "LangChain Study",
  description: "LangChain 学习项目文档",
  base: process.env.BASE || "/docs",
  ignoreDeadLinks: [
    // 忽略所有 localhost 链接(开发环境链接)
    /^https?:\/\/localhost/,
    // 忽略所有 127.0.0.1 链接
    /^https?:\/\/127\.0\.0\.1/,
  ],
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: "首页", link: "/" },
      { text: "Agents", link: "/agents" },
    ],

    sidebar: [
      {
        text: "指南",
        items: [{ text: "Agents", link: "/agents" }],
      },
      // 动态导入的 README 部分（由 scripts/collect-readmes.py 生成）
      ...readmeSidebar,
    ],

    socialLinks: [{ icon: "github", link: "https://github.com/yourusername/langchain-study" }],
  },
});
