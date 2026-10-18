import fs from "fs";
const u=process.env.API_BASE_URL || "http://127.0.0.1:8000";
fs.writeFileSync("config.js", `window.API_BASE_URL = ${JSON.stringify(u)};\n`);
