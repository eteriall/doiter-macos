# **Product Requirements Document (PRD)**

## **Project Name:** **doiter** (working title, lowercase)

## **Platform:** macOS

## **Language:** Python (100 percent Python for app logic, storage, and UI bridging)

## **Installer:** macOS `.dmg` package

---

# **1. Overview**

Elist is a minimalistic macOS todo application that behaves like Spotlight search:

* Opens instantly with **Cmd + E**
* Displays a centered overlay with a text input field
* Shows a list of existing tasks below
* Tasks can be added, searched, deleted, undone, and redone
* State persists across restarts and shutdowns
* Runs fully in Python
* Auto-starts when macOS boots
* Distributed as a `.dmg` installer

The goal: a fast, elegant, always-available todo list for power users.

---

# **2. Key User Experience**

### **Trigger**

* User presses **Cmd + E** anywhere on macOS.
* Overlay pops up on top of everything (similar to Spotlight / Raycast).

### **Overlay UI**

A small modal centered on screen:

* Rounded panel with subtle blur (macOS-like)
* Top: **Single text input**
* Below: **List of tasks**, filtered as the user types
* Keyboard-only UX:

  * Enter → add task
  * Up/Down → navigate tasks
  * Backspace → delete selected
  * Cmd+Z → undo
  * Cmd+Shift+Z → redo
  * Esc → hide overlay

---

# **3. Core Features**

## **3.1 Task Management**

### **Add tasks**

* Typing text + Enter = task added to top of list
* Empty input + Enter = no-op

### **Delete tasks**

* Select task (arrow keys) + Backspace = delete
* Deletion goes to history stack

### **Undo/Redo**

* Cmd+Z → undo last operation
* Cmd+Shift+Z → redo
* Undo/Redo history **persists across app restarts and macOS reboots**

### **Search**

* Typing text filters tasks in realtime
* Case-insensitive fuzzy search

### **Persistency**

* All tasks, history, and state stored in a local file:

  * JSON or SQLite
  * Must survive:

    * App restart
    * macOS reboot
    * Version updates

---

# **4. System Behavior**

### **4.1 Autostart**

App must automatically start when macOS boots.

Possible methods (pick one in implementation):

* A LaunchAgent `.plist` created during installation
* `pyobjc-framework-LaunchServices` call
* User allowed to disable autostart from settings

### **4.2 Global Hotkey**

* The app listens globally for **Cmd + E**
* Opens overlay (even if background)
* Must not conflict with Spotlight / other global shortcuts

### **4.3 Overlay Window**

* Always on top
* Transparent glassy background
* Blur behind panel
* Smooth show/hide animation
* Dark/light mode auto-adapting

### **4.4 Idle & Invisible Mode**

* When overlay is hidden, app uses minimal memory
* No menu bar icon by default (optional setting)
* No dock icon (runs as background agent)

---

# **5. Technical Requirements**

## **5.1 Programming Language & Libraries**

**100 percent Python preferred.**
Recommended stack:

* **PyObjC** → macOS UI, global hotkeys, blur effect, overlay window
* **pynput** or **Quartz** → global keyboard capture
* **rumps** (optional) → menu-bar helper if needed
* **SQLite** → persistent tasks & undo/redo stack
* **PyInstaller / py2app** → packaging into macOS app
* **create-dmg** → final `.dmg` with drag-to-Applications installer

---

# **6. Data Model**

## **6.1 Task**

```
task_id: str (uuid)
text: str
created_at: timestamp
updated_at: timestamp
completed: false (future extension)
```

## **6.2 Undo/Redo Log Entry**

```
action: "add" | "delete"
task_snapshot: full task object
timestamp: unix_timestamp
```

Undo stack and redo stack stored in SQLite as separate tables.

---

# **7. UI Design Requirements**

### **7.1 Layout**

* Width: ~500px
* Height: dynamic
* Round corners (12px)
* macOS vibrancy backdrop (Light/Medium/Dark)

### **Input field**

* Large, centered
* Placeholder: “Add or search tasks…”
* Auto focused on open

### **Tasks list**

* Scrollable
* Highlight selection
* Fades in/out with animations

### **Animations**

* Overlay appears with 150ms fade-in + scale
* Tasks animate in when added
* Deletions collapse smoothly

---

# **8. Interaction Flow**

### **1. Press Cmd + E**

Overlay appears → cursor in input.

### **2. Type text**

* If matches existing tasks → filter list
* If new → Enter adds task

### **3. Arrow keys to select**

Selected task is highlighted.

### **4. Press Backspace**

Task deleted → Undo stack updated.

### **5. Press Cmd+Z**

Undo last deletion or addition.

### **6. Press Esc**

Overlay disappears.

---

# **9. Packaging and Distribution**

### **9.1 Build Steps**

1. Python source code
2. py2app or PyInstaller → macOS .app bundle
3. Sign & notarize the app (required for macOS >= Catalina)
4. Create `.dmg` installer
5. DMG includes:

   * App bundle
   * Symlink to `/Applications`
   * Custom background image