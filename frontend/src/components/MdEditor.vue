<template>
  <div class="editor-container" @click="closeAllMenus">
    <!-- Menu Bar -->
    <div class="menubar" v-show="showMenubar">
      <div class="menubar-left">
        <div class="menu-item" v-for="menu in menus" :key="menu.label"
             @click.stop="toggleMenu(menu.label)"
             @mouseenter="hoverMenu(menu.label)">
          <span class="menu-label">{{ menu.label }}</span>
          <div class="dropdown" v-if="activeMenu === menu.label">
            <template v-for="item in menu.items">
              <div v-if="item.separator" :key="item.id" class="dropdown-separator"></div>
              <div v-else :key="item.label" class="dropdown-item"
                   :class="{ 'has-check': item.checked !== undefined, 'checked': item.checked }"
                   @click.stop="item.action">
                <span class="dropdown-item-label">{{ item.label }}</span>
                <span class="dropdown-item-shortcut" v-if="item.shortcut">{{ item.shortcut }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>
      <div class="menubar-center">
        <span class="file-name">{{ fileName }}</span>
        <span class="modified-dot" v-if="isModified">●</span>
      </div>
      <div class="menubar-right"></div>
    </div>
    <!-- Editor -->
    <mavon-editor
      ref="editor"
      v-model="content"
      :language="locale"
      :toolbars-flag="true"
      :subfield="true"
      :editable="true"
      :scroll-style="true"
      class="md-editor"
      @change="onContentChange"
      @save="onEditorSave"
      @imgAdd="onImgAdd"
    />
    <!-- About Dialog -->
    <div class="overlay" v-if="showAbout" @click="showAbout = false">
      <div class="about-dialog" @click.stop>
        <h2>{{ t('about.title') }}</h2>
        <p class="about-version">{{ t('about.version') }}</p>
        <p class="about-author">{{ t('about.author') }}</p>
        <div class="about-powered">
          <p class="powered-label">{{ t('about.poweredBy') }}</p>
          <div class="tech-tags">
            <span class="tech-tag" v-for="tech in techStack" :key="tech">{{ tech }}</span>
          </div>
        </div>
        <p class="about-copy">&copy; 2026 Aelln Chien. All rights reserved.</p>
        <button class="about-close" @click="showAbout = false">{{ t('about.ok') }}</button>
      </div>
    </div>
  </div>
</template>

<script>
import { readFile, writeFile, exportToPdf, exportToHtml, saveImage } from '../api/fileApi'
import messages from '../i18n'

export default {
  name: 'MdEditor',
  data() {
    return {
      content: '# Welcome to Markdown Editor\n\nStart writing your markdown here...\n',
      currentFile: null,
      isModified: false,
      originalContent: '',
      viewMode: 'split',
      activeMenu: null,
      menuOpen: false,
      showAbout: false,
      showMenubar: true,
      locale: localStorage.getItem('md-editor-locale') || 'zh-TW',
      techStack: ['Electron', 'Vue.js', 'mavon-editor', 'FastAPI', 'Uvicorn', 'Python', 'Node.js', 'Markdown', 'fpdf2']
    }
  },
  computed: {
    fileName() {
      if (!this.currentFile) return 'Untitled'
      const parts = this.currentFile.replace(/\\/g, '/').split('/')
      return parts[parts.length - 1]
    },
    viewModeLabel() {
      return this.t('viewMode.' + this.viewMode)
    },
    isNavigationOn() {
      const editor = this.$refs.editor
      return editor ? editor.s_navigation : false
    },
    menus() {
      return [
        {
          label: this.t('menu.file'),
          items: [
            { label: this.t('menu.newFile'), shortcut: 'Ctrl+N', action: () => { this.newFile(); this.closeAllMenus() } },
            { label: this.t('menu.openFile'), shortcut: 'Ctrl+O', action: () => { this.openFile(); this.closeAllMenus() } },
            { separator: true, id: 's1' },
            { label: this.t('menu.save'), shortcut: 'Ctrl+S', action: () => { this.saveFile(); this.closeAllMenus() } },
            { label: this.t('menu.saveAs'), shortcut: 'Ctrl+Shift+S', action: () => { this.saveFileAs(); this.closeAllMenus() } },
            { separator: true, id: 's2' },
            { label: this.t('menu.exit'), action: () => { this.exitApp() } }
          ]
        },
        {
          label: this.t('menu.view'),
          items: [
            { label: this.viewModeLabel, shortcut: 'F9', action: () => { this.cycleViewMode(); this.closeAllMenus() } },
            { label: this.t('menu.readMode'), shortcut: 'F11', action: () => { this.toggleReadMode(); this.closeAllMenus() } },
            { separator: true, id: 's3' },
            { label: this.t('menu.navigation'), shortcut: 'F8', checked: this.isNavigationOn, action: () => { this.toggleNavigation(); this.closeAllMenus() } },
            { label: this.t('menu.hideMenuBar'), shortcut: 'F10', action: () => { this.toggleMenubar(); this.closeAllMenus() } },
            { separator: true, id: 's4' },
            { label: this.t('language.zhTW'), checked: this.locale === 'zh-TW', action: () => { this.setLocale('zh-TW'); this.closeAllMenus() } },
            { label: this.t('language.en'), checked: this.locale === 'en', action: () => { this.setLocale('en'); this.closeAllMenus() } }
          ]
        },
        {
          label: this.t('menu.output'),
          items: [
            { label: this.t('menu.toPdf'), action: () => { this.doExportPdf(); this.closeAllMenus() } },
            { label: this.t('menu.toHtml'), action: () => { this.doExportHtml(); this.closeAllMenus() } }
          ]
        },
        {
          label: this.t('menu.help'),
          items: [
            { label: this.t('menu.about'), action: () => { this.showAbout = true; this.closeAllMenus() } }
          ]
        }
      ]
    }
  },
  async mounted() {
    if (window.electronAPI) {
      try {
        const filePath = await window.electronAPI.getFilePath()
        if (filePath) {
          await this.loadFile(filePath)
        }
      } catch (e) {
        console.error('Failed to get file path from Electron:', e)
      }
    } else {
      const params = new URLSearchParams(window.location.search)
      const file = params.get('file')
      if (file) {
        await this.loadFile(file)
      }
    }
    window.addEventListener('keydown', this.handleKeydown, true)
  },
  beforeDestroy() {
    window.removeEventListener('keydown', this.handleKeydown, true)
  },
  methods: {
    t(key) {
      const keys = key.split('.')
      let val = messages[this.locale] || messages['en']
      for (const k of keys) {
        if (val && typeof val === 'object') val = val[k]
        else return key
      }
      return val || key
    },
    setLocale(loc) {
      this.locale = loc
      localStorage.setItem('md-editor-locale', loc)
    },
    handleKeydown(e) {
      if (e.ctrlKey && e.key === 's') {
        e.preventDefault()
        e.stopImmediatePropagation()
        this.currentFile ? this.saveFile() : this.saveFileAs()
      }
      if (e.ctrlKey && e.key === 'o') {
        e.preventDefault()
        this.openFile()
      }
      if (e.ctrlKey && e.key === 'n') {
        e.preventDefault()
        this.newFile()
      }
      if (e.key === 'F9') {
        e.preventDefault()
        e.stopPropagation()
        this.cycleViewMode()
      }
      if (e.key === 'F10') {
        e.preventDefault()
        e.stopPropagation()
        this.toggleMenubar()
      }
      if (e.key === 'F11') {
        e.preventDefault()
        e.stopPropagation()
        this.toggleReadMode()
      }
      if (e.key === 'F8') {
        e.preventDefault()
        e.stopPropagation()
        this.toggleNavigation()
      }
      if (e.key === 'Escape') {
        this.closeAllMenus()
      }
    },
    toggleMenu(label) {
      if (this.activeMenu === label) {
        this.activeMenu = null
        this.menuOpen = false
      } else {
        this.activeMenu = label
        this.menuOpen = true
      }
    },
    hoverMenu(label) {
      if (this.menuOpen) {
        this.activeMenu = label
      }
    },
    closeAllMenus() {
      this.activeMenu = null
      this.menuOpen = false
    },
    cycleViewMode() {
      const editor = this.$refs.editor
      if (!editor) return
      if (this.viewMode === 'split') {
        this.viewMode = 'edit'
        editor.s_subfield = false
        editor.s_preview_switch = false
      } else if (this.viewMode === 'edit') {
        this.viewMode = 'preview'
        editor.s_subfield = false
        editor.s_preview_switch = true
      } else {
        this.viewMode = 'split'
        editor.s_subfield = true
        editor.s_preview_switch = true
      }
    },
    toggleReadMode() {
      const editor = this.$refs.editor
      if (!editor) return
      const el = editor.$refs.vReadModel
      if (!el) return
      if (!document.fullscreenElement) {
        if (el.requestFullscreen) el.requestFullscreen()
        else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen()
        else if (el.msRequestFullscreen) el.msRequestFullscreen()
      } else {
        if (document.exitFullscreen) document.exitFullscreen()
      }
    },
    toggleMenubar() {
      this.showMenubar = !this.showMenubar
    },
    toggleNavigation() {
      const editor = this.$refs.editor
      if (!editor) return
      editor.toolbar_right_click('navigation')
    },
    exitApp() {
      if (this.isModified) {
        if (!confirm(this.t('dialog.unsavedExit'))) return
      }
      if (window.electronAPI && window.electronAPI.exit) {
        window.electronAPI.exit()
      } else {
        window.close()
      }
    },
    async loadFile(filePath) {
      try {
        const data = await readFile(filePath)
        const display = this.prepareContentForDisplay(data.content, data.path)
        this.content = display
        this.currentFile = data.path
        this.originalContent = display
        this.isModified = false
        document.title = data.filename + ' - Markdown Editor'
      } catch (err) {
        alert(this.t('dialog.failedOpen') + err.message)
      }
    },
    async openFile() {
      if (window.electronAPI) {
        const filePath = await window.electronAPI.openFile()
        if (filePath) {
          await this.loadFile(filePath)
        }
      } else {
        const filePath = prompt(this.t('dialog.enterPath'))
        if (filePath) {
          await this.loadFile(filePath)
        }
      }
    },
    async saveFile() {
      if (!this.currentFile) {
        await this.saveFileAs()
        return
      }
      try {
        await writeFile(this.currentFile, this.prepareContentForSave(this.content))
        this.originalContent = this.content
        this.isModified = false
      } catch (err) {
        alert(this.t('dialog.failedSave') + err.message)
      }
    },
    async saveFileAs() {
      let filePath = null
      if (window.electronAPI) {
        filePath = await window.electronAPI.saveFileAs()
      } else {
        filePath = prompt(this.t('dialog.saveAsPrompt'), this.currentFile || '')
      }
      if (!filePath) return
      if (!filePath.toLowerCase().endsWith('.md')) {
        filePath += '.md'
      }
      try {
        // Extract any base64 images and save them to the proper image subfolder
        const processedContent = await this.extractAndSaveBase64Images(this.content, filePath)
        await writeFile(filePath, this.prepareContentForSave(processedContent, filePath))
        this.content = processedContent
        this.currentFile = filePath
        this.originalContent = processedContent
        this.isModified = false
        document.title = this.fileName + ' - Markdown Editor'
      } catch (err) {
        alert(this.t('dialog.failedSave') + err.message)
      }
    },
    newFile() {
      if (this.isModified) {
        if (!confirm(this.t('dialog.discardChanges'))) return
      }
      this.content = ''
      this.currentFile = null
      this.isModified = false
      this.originalContent = ''
      document.title = 'Markdown Editor'
    },
    onContentChange() {
      this.isModified = this.content !== this.originalContent
    },
    onEditorSave() {
      this.currentFile ? this.saveFile() : this.saveFileAs()
    },
    getDirectory(filePath) {
      const sep = filePath.includes('\\') ? '\\' : '/'
      const parts = filePath.split(sep)
      parts.pop()
      return parts.join(sep)
    },
    getImageFolder(filePath) {
      // Returns <dir>\<basename_no_ext> as the image subfolder for a given .md path
      const normalized = filePath.replace(/\\/g, '/')
      const parts = normalized.split('/')
      const baseName = parts[parts.length - 1].replace(/\.md$/i, '')
      const dir = parts.slice(0, -1).join('/')
      const sep = filePath.includes('\\') ? '\\' : '/'
      if (sep === '\\') {
        return dir.replace(/\//g, '\\') + '\\' + baseName
      }
      return dir + '/' + baseName
    },
    prepareContentForSave(content, mdFilePath) {
      const apiBase = window.location.origin + '/api/image?path='
      const mdDir = this.getDirectory(mdFilePath || this.currentFile || '')
      const sep = mdDir.includes('\\') ? '\\' : '/'
      return content.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, src) => {
        if (src.startsWith(apiBase)) {
          const absPath = decodeURIComponent(src.slice(apiBase.length))
          // Make path relative to the .md file's directory
          if (mdDir && absPath.startsWith(mdDir + sep)) {
            let rel = absPath.slice(mdDir.length + sep.length)
            rel = rel.replace(/\\/g, '/')
            return `![${alt}](${rel})`
          }
          // Fallback: just the filename
          const filename = absPath.replace(/\\/g, '/').split('/').pop()
          return `![${alt}](${filename})`
        }
        return match
      })
    },
    prepareContentForDisplay(content, filePath) {
      if (!filePath) return content
      const dir = this.getDirectory(filePath)
      const sep = dir.includes('\\') ? '\\' : '/'
      const imgExts = /\.(png|jpg|jpeg|gif|bmp|webp|svg)$/i
      return content.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, src) => {
        if (/^https?:\/\/|^data:/i.test(src)) return match
        if (src.startsWith(window.location.origin)) return match
        if (imgExts.test(src)) {
          const absPath = dir + sep + src.replace(/\//g, sep)
          const apiUrl = `${window.location.origin}/api/image?path=${encodeURIComponent(absPath)}`
          return `![${alt}](${apiUrl})`
        }
        return match
      })
    },
    async onImgAdd(pos, $file) {
      const reader = new FileReader()
      reader.onload = async (e) => {
        const dataUrl = e.target.result
        if (this.currentFile) {
          // Save to <dir>/<basename_no_ext>/ subfolder
          const imgFolder = this.getImageFolder(this.currentFile)
          try {
            const base64 = dataUrl.split(',')[1]
            const result = await saveImage(imgFolder, $file.name, base64)
            const apiUrl = `${window.location.origin}/api/image?path=${encodeURIComponent(result.path)}`
            this.$refs.editor.$img2Url(pos, apiUrl)
            return
          } catch (err) {
            console.error('Failed to save image to disk, falling back to base64:', err)
          }
        }
        // Fallback: keep as base64 until user saves the file
        this.$refs.editor.$img2Url(pos, dataUrl)
      }
      reader.readAsDataURL($file)
    },
    async extractAndSaveBase64Images(content, mdFilePath) {
      // Find all base64-embedded images, save them to disk, replace with API URLs
      const imgFolder = this.getImageFolder(mdFilePath)
      const regex = /!\[([^\]]*)\]\((data:image\/([^;]+);base64,([^)]+))\)/g
      const replacements = []
      let match
      let idx = 0
      while ((match = regex.exec(content)) !== null) {
        const [fullMatch, alt, , mimeExt, base64Data] = match
        const ext = mimeExt === 'jpeg' ? 'jpg' : mimeExt.split('+')[0]
        replacements.push({ fullMatch, alt, base64Data, ext, idx: idx++ })
      }
      let updatedContent = content
      for (const r of replacements) {
        try {
          const filename = `image_${Date.now()}_${r.idx}.${r.ext}`
          const result = await saveImage(imgFolder, filename, r.base64Data)
          const apiUrl = `${window.location.origin}/api/image?path=${encodeURIComponent(result.path)}`
          updatedContent = updatedContent.replace(r.fullMatch, `![${r.alt}](${apiUrl})`)
        } catch (err) {
          console.error('Failed to save embedded image to disk:', err)
        }
      }
      return updatedContent
    },
    async ensureSaved() {
      if (!this.currentFile) {
        alert(this.t('dialog.mustSaveFirst'))
        if (confirm(this.t('dialog.saveNowConfirm'))) {
          await this.saveFileAs()
        }
        return !!this.currentFile
      }
      if (this.isModified) {
        alert(this.t('dialog.mustSaveFirst'))
        if (confirm(this.t('dialog.saveNowConfirm'))) {
          await this.saveFile()
        }
        return !this.isModified
      }
      return true
    },
    getExportDefaultName(ext) {
      if (!this.currentFile) return 'document' + ext
      const base = this.fileName.replace(/\.md$/i, '')
      return base + ext
    },
    getExportDefaultDir() {
      if (!this.currentFile) return ''
      const sep = this.currentFile.includes('/') ? '/' : '\\'
      const parts = this.currentFile.split(sep)
      parts.pop()
      return parts.join(sep) + sep
    },
    async doExportPdf() {
      const saved = await this.ensureSaved()
      if (!saved) return
      let filePath = null
      if (window.electronAPI && window.electronAPI.exportPdf) {
        filePath = await window.electronAPI.exportPdf(this.getExportDefaultDir() + this.getExportDefaultName('.pdf'))
      } else {
        const defaultPath = this.getExportDefaultDir() + this.getExportDefaultName('.pdf')
        filePath = prompt(this.t('dialog.exportPdfPrompt'), defaultPath)
      }
      if (!filePath) return
      try {
        await exportToPdf(this.content, filePath, this.currentFile || '')
        alert(this.t('dialog.exportSuccess'))
      } catch (err) {
        alert(this.t('dialog.exportFailed') + err.message)
      }
    },
    async doExportHtml() {
      const saved = await this.ensureSaved()
      if (!saved) return
      let filePath = null
      if (window.electronAPI && window.electronAPI.exportHtml) {
        filePath = await window.electronAPI.exportHtml(this.getExportDefaultDir() + this.getExportDefaultName('.html'))
      } else {
        const defaultPath = this.getExportDefaultDir() + this.getExportDefaultName('.html')
        filePath = prompt(this.t('dialog.exportHtmlPrompt'), defaultPath)
      }
      if (!filePath) return
      try {
        await exportToHtml(this.content, filePath)
        alert(this.t('dialog.exportSuccess'))
      } catch (err) {
        alert(this.t('dialog.exportFailed') + err.message)
      }
    }
  }
}
</script>

<style scoped>
.editor-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
}

/* ── Menu Bar ─────────────────────────────────── */
.menubar {
  display: flex;
  align-items: center;
  height: 30px;
  background: #3c3c3c;
  color: #cccccc;
  font-size: 13px;
  user-select: none;
  -webkit-app-region: drag;
  padding: 0 8px;
  position: relative;
  z-index: 100;
}

.menubar-left {
  display: flex;
  align-items: center;
  -webkit-app-region: no-drag;
}

.menubar-center {
  flex: 1;
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
}

.menubar-right {
  width: 120px;
}

.file-name {
  font-size: 12px;
  opacity: 0.85;
}

.modified-dot {
  color: #e74c3c;
  font-size: 14px;
  line-height: 1;
}

.menu-item {
  position: relative;
  padding: 2px 8px;
  cursor: pointer;
  border-radius: 3px;
}

.menu-item:hover,
.menu-item .menu-label:hover {
  background: rgba(255, 255, 255, 0.1);
}

.menu-label {
  line-height: 26px;
}

/* ── Dropdown ─────────────────────────────────── */
.dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 220px;
  background: #252526;
  border: 1px solid #454545;
  border-radius: 5px;
  padding: 4px 0;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
  z-index: 200;
}

.dropdown-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 24px;
  cursor: pointer;
  white-space: nowrap;
}

.dropdown-item:hover {
  background: #094771;
  color: #ffffff;
}

.dropdown-item.has-check {
  padding-left: 12px;
}

.dropdown-item.has-check::before {
  content: '';
  display: inline-block;
  width: 14px;
  margin-right: 6px;
}

.dropdown-item.checked::before {
  content: '✓';
  width: 14px;
  margin-right: 6px;
}

.dropdown-item-label {
  flex: 1;
}

.dropdown-item-shortcut {
  margin-left: 32px;
  opacity: 0.55;
  font-size: 12px;
}

.dropdown-separator {
  height: 1px;
  background: #454545;
  margin: 4px 0;
}

/* ── Editor ───────────────────────────────────── */
.md-editor {
  flex: 1;
  border: none !important;
  z-index: 1;
}

/* ── About Dialog ─────────────────────────────── */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 999;
}

.about-dialog {
  background: #252526;
  color: #cccccc;
  border: 1px solid #454545;
  border-radius: 8px;
  padding: 32px 40px;
  text-align: center;
  min-width: 300px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6);
}

.about-dialog h2 {
  margin: 0 0 12px;
  color: #ffffff;
  font-size: 20px;
}

.about-version {
  margin: 4px 0;
  font-size: 13px;
  opacity: 0.7;
}

.about-author {
  margin: 8px 0 4px;
  font-size: 13px;
}

.about-copy {
  margin: 4px 0 20px;
  font-size: 12px;
  opacity: 0.5;
}

.about-close {
  padding: 6px 28px;
  background: #0e639c;
  color: #ffffff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.about-close:hover {
  background: #1177bb;
}

.about-powered {
  margin: 16px 0;
}

.powered-label {
  font-size: 12px;
  opacity: 0.6;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.tech-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
}

.tech-tag {
  background: rgba(14, 99, 156, 0.3);
  color: #7ec8e3;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
}
</style>
