const { app, BrowserWindow, dialog } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");

let mainWindow = null;
let pythonProcess = null;
let nodeServer = null;

const PYTHON_PORT = 5001;
const NODE_PORT = 5000;

function startPythonBackend() {
  const pythonScript = path.join(__dirname, "..", "image-service", "app.py");
  console.log("Starting Python OCR service from:", pythonScript);

  pythonProcess = spawn("python", [pythonScript], {
    cwd: path.join(__dirname, "..", "image-service"),
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
    shell: true,
  });

  pythonProcess.stdout.on("data", (data) => {
    console.log(`[Python OCR] ${data}`);
  });

  pythonProcess.stderr.on("data", (data) => {
    console.error(`[Python OCR Error] ${data}`);
  });
}

function startNodeBackend() {
  const serverPath = path.join(__dirname, "..", "server", "server.js");
  console.log("Starting Node Backend from:", serverPath);

  nodeServer = spawn("node", [serverPath], {
    cwd: path.join(__dirname, "..", "server"),
    env: { ...process.env, PORT: NODE_PORT },
    shell: true,
  });

  nodeServer.stdout.on("data", (data) => {
    console.log(`[Node Server] ${data}`);
  });

  nodeServer.stderr.on("data", (data) => {
    console.error(`[Node Server Error] ${data}`);
  });
}

function waitForServer(port, callback, retries = 30) {
  if (retries <= 0) {
    callback(false);
    return;
  }

  const req = http.get(`http://127.0.0.1:${port}`, (res) => {
    callback(true);
  });

  req.on("error", () => {
    setTimeout(() => waitForServer(port, callback, retries - 1), 500);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1080,
    minHeight: 700,
    title: "INVA-AUDIT — Physical Inventory Verification Desktop",
    backgroundColor: "#0d1117",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    autoHideMenuBar: true,
  });

  mainWindow.loadURL(`http://localhost:${NODE_PORT}`);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  startPythonBackend();
  startNodeBackend();

  waitForServer(NODE_PORT, (ready) => {
    if (ready) {
      createWindow();
    } else {
      dialog.showErrorBox(
        "Launch Error",
        "Failed to connect to internal services. Please check Python and Node installations."
      );
      app.quit();
    }
  });
});

app.on("window-all-closed", () => {
  // Kill child background servers on exit
  if (pythonProcess) {
    try {
      process.kill(-pythonProcess.pid);
    } catch (e) {
      pythonProcess.kill();
    }
  }
  if (nodeServer) {
    try {
      process.kill(-nodeServer.pid);
    } catch (e) {
      nodeServer.kill();
    }
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});
