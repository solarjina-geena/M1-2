import fs from "fs";
const u=process.env.API_BASE_URL || "https://imeb3-ai-agent-api.onrender.com";
fs.writeFileSync("config.js", `window.API_BASE_URL = ${JSON.stringify(u)};\n`);
