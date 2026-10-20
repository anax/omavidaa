globalThis.__OMARCHY_CMD_QUEUE = globalThis.__OMARCHY_CMD_QUEUE || [];

export default function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Access-Control-Allow-Origin", "*");

  if (globalThis.__OMARCHY_CMD_QUEUE.length > 0) {
    const cmd = globalThis.__OMARCHY_CMD_QUEUE.shift();
    res.status(200).json(cmd);
    return;
  }

  res.status(200).json({});
}
