// SPDX-License-Identifier: GPL-3.0-or-later
.pragma library

var companions = [
    {id: "peek", name: "Peek", kind: "The robot", color: "#b7c8dc", description: "An inquisitive edge dweller. Head tilts, finger taps, and a luminous voice."},
    {id: "ember", name: "Ember", kind: "The fox", color: "#ed995f", description: "A quick little troublemaker. Twitching ears, soft paws, and a very talkative tail."},
    {id: "nimbus", name: "Nimbus", kind: "The jellyfish", color: "#baabfa", description: "A gentle daydreamer. Buoyant bobs, rippling tendrils, and a bioluminescent bell."},
    {id: "orbit", name: "Orbit", kind: "The solar system", color: "#edc67d", description: "A small universe in motion. Dancing moons, gyroscopic rings, and stellar bursts."}
];

var actions = [
    {id: "arrive", name: "Arrival"}, {id: "idle", name: "Idle"},
    {id: "blink", name: "Blink / eclipse"}, {id: "greet", name: "Greeting"},
    {id: "hover", name: "Curiosity"}, {id: "listening", name: "Listening"},
    {id: "thinking", name: "Thinking"}, {id: "acting", name: "Working"},
    {id: "speaking", name: "Speaking"}, {id: "success", name: "Success"},
    {id: "needs_input", name: "Needs input"}, {id: "error", name: "Error"},
    {id: "standby", name: "Sleep"}, {id: "wake", name: "Wake up"},
    {id: "drag", name: "Dragging"}, {id: "drop", name: "Landing"},
    {id: "warming", name: "Warming up"}
];

function companion(id) { return companions.find(c => c.id === id) || companions[0]; }
function actionName(id) { var action = actions.find(a => a.id === id); return action ? action.name : "Idle"; }
