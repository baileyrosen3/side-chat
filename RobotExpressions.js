// SPDX-License-Identifier: GPL-3.0-or-later
.pragma library

var actions = [
    {id: "arrive", name: "Arrival"}, {id: "idle", name: "Idle"},
    {id: "blink", name: "Blink"}, {id: "greet", name: "Greeting"},
    {id: "hover", name: "Curiosity"}, {id: "ready", name: "Ready to listen"},
    {id: "listening", name: "Listening"}, {id: "hearing", name: "Hearing you"},
    {id: "thinking", name: "Thinking"}, {id: "acting", name: "Working"},
    {id: "speaking", name: "Speaking"}, {id: "success", name: "Success"},
    {id: "needs_input", name: "Needs input"}, {id: "error", name: "Error"},
    {id: "standby", name: "Sleep"}, {id: "wake", name: "Wake up"},
    {id: "drag", name: "Dragging"}, {id: "drop", name: "Landing"},
    {id: "warming", name: "Warming up"}, {id: "wink", name: "Wink"},
    {id: "nod", name: "Reassurance"}
];

function actionName(id) { var action = actions.find(a => a.id === id); return action ? action.name : "Idle"; }
