// SPDX-License-Identifier: GPL-3.0-or-later
.pragma library

// Gentle nearby movement, with a bounded look toward distant monitors.
function direction(pointer, face, distance) {
    var scale = Math.max(1, distance);
    return {
        x: Math.atan((pointer.x - face.x) / scale) * 2 / Math.PI,
        y: Math.atan((pointer.y - face.y) / scale) * 2 / Math.PI
    };
}

// Attention follows the conversation and task before incidental mouse motion.
// The caller expires action targets; absent or invalid targets never get guessed.
function attention(voice, busy, cursor, target) {
    if (voice.reducedMotion || voice.expressiveness === 0 || voice.stage === "standby" || voice.stage === "off")
        return {source: "rest", point: null, tracking: false};
    if (voice.hearing || voice.transcribing || voice.speaking || voice.stage === "needs_input")
        return {source: "user", point: null, tracking: true};
    if (busy) {
        if (target && typeof target.x === "number" && typeof target.y === "number" && isFinite(target.x) && isFinite(target.y))
            return {source: "task", point: target, tracking: true};
        return {source: "rest", point: null, tracking: false};
    }
    return cursor ? {source: "cursor", point: cursor, tracking: true} : {source: "rest", point: null, tracking: false};
}

// Critically damped motion keeps velocity through target changes. Sampling
// the cursor less often must not restart an ease-out on every new position.
function spring(value, velocity, target, dt) {
    if (Math.abs(target - value) < .005 && Math.abs(velocity) < .05)
        return {value: target, velocity: 0};
    var omega = 2 / .14;
    var offset = value - target;
    var step = (velocity + omega * offset) * dt;
    var decay = Math.exp(-omega * dt);
    return {
        value: target + (offset + step) * decay,
        velocity: (velocity - omega * step) * decay
    };
}
