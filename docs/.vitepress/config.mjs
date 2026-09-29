import { defineConfig } from "vitepress"

export default defineConfig({
  lang: "en-US",
  title: "wraw",
  description: "A lightweight, cross-platform reader for Waters MassLynx RAW directories",
  base: "/wraw/",
  lastUpdated: true,
  cleanUrls: true,
  themeConfig: {
    nav: [
      { text: "Guide", link: "/guide/getting-started" },
      { text: "API reference", link: "/api/" },
    ],
    sidebar: [
      {
        text: "Guide",
        items: [
          { text: "Getting started", link: "/guide/getting-started" },
        ],
      },
      {
        text: "API reference",
        items: [
          { text: "Overview", link: "/api/" },
          { text: "Readers", link: "/api/readers" },
          { text: "Data models", link: "/api/models" },
          { text: "Exceptions", link: "/api/exceptions" },
        ],
      },
    ],
    socialLinks: [
      { icon: "github", link: "https://github.com/aryan-f/wraw" },
    ],
    search: {
      provider: "local",
    },
    outline: [2, 3],
    footer: {
      message: "Built with VitePress",
    },
  },
})
