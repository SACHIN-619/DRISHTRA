// Bundles the console into web/dist. No CDN, no web fonts: everything ships with the app.
import * as esbuild from "esbuild";
import { cpSync, mkdirSync, rmSync } from "node:fs";

const watch = process.argv.includes("--watch");
rmSync("dist", { recursive: true, force: true });
mkdirSync("dist/assets", { recursive: true });
cpSync("index.html", "dist/index.html");
cpSync("src/favicon.svg", "dist/favicon.svg");
cpSync("src/media", "dist/media", { recursive: true });
cpSync("src/fonts", "dist/fonts", { recursive: true });

const options = {
  entryPoints: { app: "src/main.tsx" },
  bundle: true,
  outdir: "dist/assets",
  format: "esm",
  target: ["es2020"],
  minify: !watch,
  sourcemap: watch,
  jsx: "automatic",
  loader: { ".css": "css" },
  external: ["/fonts/*", "/media/*"],
  nodePaths: process.env.NODE_PATH ? process.env.NODE_PATH.split(":") : [],
  define: { "process.env.NODE_ENV": JSON.stringify(watch ? "development" : "production") },
  logLevel: "info",
};

if (watch) {
  const ctx = await esbuild.context(options);
  await ctx.watch();
  console.log("watching src/ … (run the backend and open http://localhost:8000)");
} else {
  await esbuild.build(options);
}
