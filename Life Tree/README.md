# Life Tree 🌳
> **"This app helps to solve life problems."**

![Life Tree Banner](Assets/banner_placeholder.png)
*(Replace this with a banner image showing the full dashboard)*

**Life Tree** is a comprehensive productivity and life-management ecosystem built with **Python** and **PyQt6**. It goes beyond simple task lists by combining hierarchical goal setting, deep-work tools, distraction blocking, and immersive writing environments into a single, cohesive desktop application.

Designed for users who need to maintain high focus while tracking complex, long-term goals, Life Tree enforces accountability through "hardcore" productivity mechanics and rewards progress with gamified elements.

---

## ⚡ Key Features

### 🎯 Hierarchical Goal Management
Break down your life's biggest ambitions into manageable nodes.
- **Tree Visualization**: View your goals as a branching tree of intentions.
- **Progress Tracking**: Track completion percentages that propagate up the tree.
- **Drill-Down Focus**: Zoom in on specific sub-nodes to work without clutter.

### 🍅 Advanced Focus System
A powerful Pomodoro-style engine that refuses to let you fail.
- **Strict Accountability**: Hardcore mode prevents exiting or distracting yourself during focus sessions.
- **Idle Detection**: Automatically pauses or penalizes you if you drift away.
- **Monitor Blackout**: Optionally turns off your screen during strict breaks to force mental recovery.

### ✍️ The Mechanical Scribe (TypeWriter Mode)
An integrated immersive writing environment invoked via `Ctrl+Alt+N`.
- **Vintage Aesthetic**: Realistic paper textures and typewriter sound effects.
- **Permanent Ink**: No backspace (optional) to encourage flow state and forward momentum.
- **Distraction-Free**: Full-screen, always-on-top interface for pure writing.

### 🛡️ Distraction Blocking & Analytics
- **App Restriction**: Automatically closes distracting apps (social media, games) during focus sessions.
- **Session Analytics**: Detailed graphs tracking focus time, wpm (words per minute), and consistency.
- **Mini Status Bar**: An unobtrusive, always-on-top pill showing real-time words typed and session timers.

---

## 📸 Screenshots

| **Main Dashboard** | **Tree Visualization** |
|:---:|:---:|
| ![Dashboard](Assets/dashboard_screenshot.png) | ![Tree View](Assets/tree_screenshot.png) |
| *Central command for your day.* | *Visualize your life's path.* |

| **Mechanical Scribe** | **Analytics** |
|:---:|:---:|
| ![TypeWriter](Assets/typewriter_screenshot.png) | ![Graphs](Assets/analytics_screenshot.png) |
| *Immersive, sound-rich writing.* | *Track your growth over time.* |

---

## 🛠️ Technology Stack

- **Core**: Python 3.10+
- **GUI Framework**: PyQt6 (Qt 6)
- **Architecture**: Modular Hexagonal Architecture (Separation of UI, Core Logic, and Infrastructure)
- **Data Persistence**: JSON-based local database.
- **System Integation**: Low-level Windows API hooks for idle detection and monitor control.

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- Windows 10/11 (Required for system hooks)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/life-tree.git
   cd life-tree
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Ensure you include `PyQt6`, `pygetwindow`, `pystray`, `pillow`, etc.)*

3. **Run the Application**
   ```bash
   python App/main.py
   ```

## 🏗️ Architecture

The project follows a **Hexagonal Architecture** pattern to ensure scalability and testability:

- **`App/`**: Entry point and composition root.
- **`Core/`**: Pure business logic (Timer Engine, Percentage calculations).
- **`Adapters/`**:
    - **`UI/`**: PyQt6 implementation of ports.
    - **`Sensors/`**: Keyboard hooks, Idle detectors.
    - **`Persistence/`**: File system storage.
- **`Infrastructure/`**: Global configuration and assets.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

*Built with ❤️ by Walid*
