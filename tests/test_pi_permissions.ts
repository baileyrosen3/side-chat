import assert from "node:assert/strict";
import permissionGate from "../agents/pi_permissions.ts";

let handler: any;
permissionGate({
    registerCommand(name: string) { assert.equal(name, "side-chat-permissions"); },
    on(name: string, callback: any) { assert.equal(name, "tool_call"); handler = callback; },
});
const event = { toolName: "write", input: { path: "file.txt", content: "test" } };
assert.equal((await handler(event, { hasUI: false })).block, true);
for (const answer of [false, undefined, null, "true"]) {
    assert.equal((await handler(event, { hasUI: true, ui: { confirm: async () => answer } })).block, true);
}
assert.equal(await handler(event, { hasUI: true, ui: { confirm: async (title: string, message: string) => {
    assert.equal(title, "Allow write?");
    assert.equal(JSON.parse(message).path, "file.txt");
    return true;
} } }), undefined);
assert.equal((await handler(event, { hasUI: true, ui: { confirm: async () => { throw Error("disconnected"); } } })).block, true);
console.log("Pi permission gate: allow, deny, cancellation, missing UI, and disconnect passed.");
