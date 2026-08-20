# MedSimplify Lite 🏥⚡

A cross-platform Flutter application for simplifying complex clinical discharge summaries into **Indian Lay English**, built for both **Web & Mobile (Android/iOS) and Desktop (Linux/macOS/Windows)**.

---

## 🌟 Key Highlights & Architecture

- **100% Client-Side Architecture**: No backend server (Flask removed) and no external database needed.
- **Zero Authentication Required**: Open-and-use immediately with locally stored preferences.
- **Cloud LLM API Integration**: Direct REST client integration with:
  - ⚡ **Cerebras Cloud** (`llama3.1-8b`)
  - ✦ **Google Gemini** (`gemini-2.5-flash`)
  - 🚀 **Groq Cloud** (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`)
- **Clinical Prompt Engineering**:
  - Embedded system prompt with 11 strict rules for Indian Lay English translation.
  - Multi-shot strategy support: **Zero-shot**, **One-shot**, and **Few-shot** (using 4 gold-standard curated medical examples).
  - Preprocessing pipeline with automated clinical term dictionary substitution.
- **Local Persistence & Export**:
  - API keys and session history (last 50 summaries) saved securely on-device via `shared_preferences`.
  - Export formatted PDF summaries directly (`pdf` & `printing`).
  - Native clipboard copy and system share sheet (`share_plus`).
- **UI/UX**:
  - Material 3 theme with **Light & Dark mode** support.
  - Responsive layout (optimized for mobile screens, tablets, and wide desktop displays).
  - Modern typography using Google Fonts (Inter).

---

## 📋 Prerequisites

Ensure Flutter SDK is installed and in your `PATH`:

```bash
# Verify installation
flutter doctor
```

*(If Flutter was installed in your home directory, ensure `export PATH="$HOME/flutter/bin:$PATH"` is present in your `~/.bashrc`)*

---

## 🚀 Running on Different Environments

### 1. 🌐 Web Browser

#### Development Mode (with Hot-Reload in Chrome):
```bash
cd btp_lite
flutter run -d chrome
```

#### Production Web Build & Local HTTP Server:
```bash
cd btp_lite
flutter build web --release

# Serve the static build with Python:
cd build/web
python3 -m http.server 8080
```
Open **[http://localhost:8080](http://localhost:8080)** in your browser.

---

### 2. 🐧 Linux Desktop (Native App)

#### Prerequisites (one-time setup on Ubuntu / Pop!_OS / Debian):
```bash
sudo apt-get install -y clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev libstdc++-12-dev
```

#### Run in Debug Mode:
```bash
cd btp_lite
flutter run -d linux
```

#### Build Standalone Linux Release Binary:
```bash
cd btp_lite
flutter build linux --release
```
The compiled executable bundle will be located at:
```
build/linux/x64/release/bundle/btp_lite
```
You can run it directly:
```bash
./build/linux/x64/release/bundle/btp_lite
```

---

### 3. 📱 Android (Phone / Tablet / Emulator)

#### A. Build Standalone APK (Install on any Android device):
```bash
cd btp_lite
flutter build apk --release
```
The APK file is generated at:
```
build/app/outputs/flutter-apk/app-release.apk
```
- **How to install on your phone**: Send `app-release.apk` to your phone via USB, Google Drive, WhatsApp, or email, tap the file, and choose **Install**.

#### B. Direct USB Debugging / Live Run:
1. Enable **Developer Options** and **USB Debugging** on your phone.
2. Plug your phone into your laptop via USB.
3. Verify your device is detected:
   ```bash
   flutter devices
   ```
4. Run the app directly on your phone:
   ```bash
   flutter run -d android
   ```

#### C. Google Play Store Release (App Bundle):
```bash
flutter build appbundle --release
```
Generated file: `build/app/outputs/bundle/release/app-release.aab`

---

### 4. 🍎 iOS / macOS (iPhone, iPad, Mac Desktop)

> *Note: Building for iOS or macOS requires a machine running macOS with Xcode installed.*

#### Run on iOS Simulator:
```bash
cd btp_lite
flutter run -d ios
```

#### Build iOS IPA Package:
```bash
flutter build ipa --release
```

#### Run Native macOS Desktop App:
```bash
flutter create --platforms macos .
flutter run -d macos
```

---

### 5. 🪟 Windows Desktop

> *Note: Building for Windows requires a Windows machine with "Desktop development with C++" installed via Visual Studio Installer.*

```bash
flutter create --platforms windows .
flutter run -d windows
```

---

## 🔑 First-Time App Configuration

1. Launch **MedSimplify Lite** on any platform.
2. Tap the **⚙ Settings** icon in the top app bar (or open the side drawer).
3. Enter at least one API key from the supported providers:
   - **⚡ Cerebras Cloud** (Free API keys: [cloud.cerebras.ai](https://cloud.cerebras.ai))
   - **✦ Google Gemini** (Free API keys: [aistudio.google.com](https://aistudio.google.com))
   - **🚀 Groq Cloud** (Free API keys: [console.groq.com](https://console.groq.com))
4. Tap **Save API Keys**.
5. Return to the Home screen, select your desired **AI Model** and **Prompting Strategy**, paste any clinical discharge summary, and tap **✨ Simplify Summary**!

---

## 📂 Project Structure

```
btp_lite/
├── lib/
│   ├── main.dart                 # App initialization & theme state
│   ├── theme/
│   │   └── app_theme.dart        # Light & Dark Material 3 color schemes
│   ├── models/
│   │   ├── api_model.dart        # Cloud AI model catalogue & metadata
│   │   └── simplify_result.dart  # Result model & JSON serialization
│   ├── services/
│   │   ├── storage_service.dart  # shared_preferences storage (keys & history)
│   │   ├── prompt_service.dart   # System prompt, dictionary & few-shot examples
│   │   ├── cerebras_service.dart # Cerebras REST API client
│   │   ├── gemini_service.dart   # Google Gemini REST API client
│   │   ├── groq_service.dart     # Groq REST API client
│   │   └── simplify_service.dart # Orchestrator service
│   ├── screens/
│   │   ├── home_screen.dart      # Main dashboard with 2-column responsive layout
│   │   ├── settings_screen.dart  # API key management & about info
│   │   ├── history_screen.dart   # Past simplification records
│   │   └── result_screen.dart    # Full-screen reading mode & PDF exporter
│   └── widgets/
│       ├── app_drawer.dart       # Navigation drawer with theme switch
│       ├── model_selector.dart   # Provider dropdown selector
│       ├── strategy_selector.dart# Zero/One/Few-shot toggle cards
│       ├── output_card.dart      # Result card with markdown rendering
│       └── loading_overlay.dart  # Pulsing shimmer loading indicator
├── web/                          # Web configuration & index.html
├── linux/                        # Native Linux CMake & C++ runner
└── pubspec.yaml                  # Flutter package dependencies
```

---

## 🧪 Testing & Analysis

To verify code quality and check for static analysis issues:

```bash
cd btp_lite
flutter analyze
flutter test
```
