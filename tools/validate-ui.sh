#!/usr/bin/env bash
# Native UI checks. Fixtures use sample data and do not call an agent or microphone.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
export QT_QPA_PLATFORMTHEME=generic QT_QUICK_CONTROLS_STYLE=Basic
export QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software
for suite in chatstyle permissions approvals outline speechsettings thoughts workspace audit_fixes; do
    /usr/lib/qt6/bin/qmltestrunner -input "tests/qml/tst_$suite.qml" -import tests/qml/imports
done
export QT_QPA_PLATFORM=wayland QT_QUICK_BACKEND=rhi QSG_RHI_BACKEND=opengl
for suite in companions companion_transition companion_gaze task_surface; do
    /usr/lib/qt6/bin/qmltestrunner -input "tests/qml/tst_$suite.qml" -import tests/qml/imports
done
