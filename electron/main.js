const { app, BrowserWindow, dialog, ipcMain } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const net = require('net')
const http = require('http')

let mainWindow = null
let backendProcess = null
let serverPort = null
let openFilePath = null

// ── Port helper ──────────────────────────────────────────────────────────────
function getAvailablePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port
      server.close(() => resolve(port))
    })
    server.on('error', reject)
  })
}

// ── Wait until backend responds ──────────────────────────────────────────────
function waitForServer(url, maxRetries = 50) {
  return new Promise((resolve, reject) => {
    let retries = 0
    const check = () => {
      http.get(url, (res) => {
        if (res.statusCode === 200) resolve()
        else retry()
      }).on('error', retry)
    }
    const retry = () => {
      if (++retries >= maxRetries) {
        reject(new Error('Backend server did not start in time'))
      } else {
        setTimeout(check, 400)
      }
    }
    check()
  })
}

// ── Start the Python / PyInstaller backend ───────────────────────────────────
async function startBackend() {
  serverPort = await getAvailablePort()

  if (!app.isPackaged) {
    // Development: run Python script directly
    const serverScript = path.join(__dirname, '..', 'backend', 'server.py')
    backendProcess = spawn('python', [serverScript, '--port', String(serverPort)], {
      stdio: 'pipe'
    })
  } else {
    // Production: run bundled PyInstaller exe
    const backendExe = path.join(process.resourcesPath, 'backend', 'server.exe')
    backendProcess = spawn(backendExe, ['--port', String(serverPort)], {
      stdio: 'pipe'
    })
  }

  backendProcess.stdout.on('data', (d) => console.log('[Backend]', d.toString()))
  backendProcess.stderr.on('data', (d) => console.error('[Backend]', d.toString()))
  backendProcess.on('error', (err) => {
    console.error('Failed to start backend:', err)
    dialog.showErrorBox('Error', 'Failed to start backend server:\n' + err.message)
    app.quit()
  })

  await waitForServer(`http://127.0.0.1:${serverPort}/api/health`)
}

// ── Create the main window ──────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  let url = `http://127.0.0.1:${serverPort}`
  if (openFilePath) {
    url += `?file=${encodeURIComponent(openFilePath)}`
  }

  mainWindow.loadURL(url)
  mainWindow.setMenuBarVisibility(false)
  mainWindow.on('closed', () => { mainWindow = null })
}

// ── IPC handlers for native dialogs ─────────────────────────────────────────
ipcMain.handle('dialog:openFile', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    filters: [{ name: 'Markdown Files', extensions: ['md'] }],
    properties: ['openFile']
  })
  return result.canceled ? null : result.filePaths[0]
})

ipcMain.handle('dialog:saveFileAs', async () => {
  const result = await dialog.showSaveDialog(mainWindow, {
    filters: [{ name: 'Markdown Files', extensions: ['md'] }],
    defaultPath: 'untitled.md'
  })
  return result.canceled ? null : result.filePath
})

ipcMain.handle('dialog:exportPdf', async (_event, defaultPath) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    filters: [{ name: 'PDF Files', extensions: ['pdf'] }],
    defaultPath: defaultPath || 'document.pdf'
  })
  return result.canceled ? null : result.filePath
})

ipcMain.handle('dialog:exportHtml', async (_event, defaultPath) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    filters: [{ name: 'HTML Files', extensions: ['html'] }],
    defaultPath: defaultPath || 'document.html'
  })
  return result.canceled ? null : result.filePath
})

ipcMain.handle('get-file-path', () => openFilePath)

ipcMain.handle('app:exit', () => {
  app.quit()
})

// ── Extract .md path from command-line argv ─────────────────────────────────
function extractFilePath(argv) {
  const mdArg = argv.find(a => a.toLowerCase().endsWith('.md') && !a.startsWith('--'))
  if (mdArg) openFilePath = path.resolve(mdArg)
}

// ── Single-instance lock ────────────────────────────────────────────────────
const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
} else {
  app.on('second-instance', (_event, argv) => {
    extractFilePath(argv)
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
      if (openFilePath) {
        mainWindow.loadURL(
          `http://127.0.0.1:${serverPort}?file=${encodeURIComponent(openFilePath)}`
        )
      }
    }
  })
}

// ── App lifecycle ───────────────────────────────────────────────────────────
app.on('ready', async () => {
  extractFilePath(process.argv)
  try {
    await startBackend()
    createWindow()
  } catch (err) {
    dialog.showErrorBox('Startup Error', err.message)
    app.quit()
  }
})

app.on('window-all-closed', () => {
  if (backendProcess) backendProcess.kill()
  app.quit()
})

app.on('before-quit', () => {
  if (backendProcess) backendProcess.kill()
})
