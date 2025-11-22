import { defineConfig } from "vitepress";

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "My Awesome Project",
  description: "A VitePress Site",
  base: process.env.BASE || "/docs",
  ignoreDeadLinks: [
    // 忽略本地开发链接
    /^https?:\/\/localhost/,
    /^https?:\/\/127\.0\.0\.1/,
  ],
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: "Home", link: "/" },
      { text: "Examples", link: "/markdown-examples" },
      { text: "Apps", link: "/links/100-simple-chat-invoke" },
    ],

    sidebar: [
      {
        text: "Examples",
        items: [
          { text: "Markdown Examples", link: "/markdown-examples" },
          { text: "Runtime API Examples", link: "/api-examples" },
        ],
      },
      {
        text: "应用示例",
        items: [
          { text: "100 Simple Chat Invoke", link: "/links/100-simple-chat-invoke" },
          { text: "101 Simple Chat Stream", link: "/links/101-simple-chat-stream" },
          { text: "110 Simple LangGraph TUI", link: "/links/110-simple-langgraph-tui" },
          { text: "120 Chainlit Demo", link: "/links/120-chainlit-demo" },
          { text: "130 Streamlit Demo", link: "/links/130-streamlit-demo" },
        ],
      },
    ],

    socialLinks: [
      { icon: "github", link: "https://github.com/vuejs/vitepress" },
    ],
  },
});
