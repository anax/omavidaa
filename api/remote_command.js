// In-memory queue for serverless Vercel runtime
// Also saved to globalThis so multiple invocations can read
globalThis.__OMARCHY_CMD_QUEUE = globalThis.__OMARCHY_CMD_QUEUE || [];

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    res.status(200).end();
    return;
  }

  if (req.method === "POST") {
    try {
      const body = typeof req.body === "string" ? JSON.parse(req.body) : req.body;
      const cmdItem = {
        id: Date.now(),
        remoteCmd: body,
        // Convert to immediate JS execution on TV
        js: generateTvJs(body)
      };
      globalThis.__OMARCHY_CMD_QUEUE.push(cmdItem);
      res.status(200).json({ ok: true, queued: cmdItem.id });
      return;
    } catch (e) {
      res.status(400).json({ ok: false, error: String(e) });
      return;
    }
  }

  res.status(200).json({ queueLength: globalThis.__OMARCHY_CMD_QUEUE.length });
}

function generateTvJs(cmd) {
  if (cmd.type === "key") {
    return `if (typeof handleKeycodeDirect === 'function') { handleKeycodeDirect(${cmd.keyCode}); } else { try { var e = document.createEvent('Events'); e.initEvent('keydown', true, true); e.keyCode = ${cmd.keyCode}; e.which = ${cmd.keyCode}; window.dispatchEvent(e); } catch(x) {} }`;
  }
  if (cmd.type === "action") {
    return `if (typeof handleRemoteCommand === 'function') { handleRemoteCommand(${JSON.stringify(cmd)}); }`;
  }
  if (cmd.type === "launch" || cmd.type === "browse") {
    return `if (typeof browseTo === 'function') { browseTo(${JSON.stringify(cmd.url)}, ${JSON.stringify(cmd.title || cmd.url)}); }`;
  }
  if (cmd.type === "hal") {
    return `if (typeof handleRemoteCommand === 'function') { handleRemoteCommand(${JSON.stringify(cmd)}); }`;
  }
  return "";
}
