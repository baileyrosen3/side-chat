// A per-conversation approval gate. Existing Pi extensions remain enabled.
export default function (pi: any) {
    pi.registerCommand("side-chat-permissions", {
        description: "Show the Side Chat tool approval status",
        handler: async (_args: string, ctx: any) => ctx.ui.notify("Ask before tools is enabled for this session.", "info"),
    });
    pi.on("tool_call", async (event: any, ctx: any) => {
        if (!ctx.hasUI) return { block: true, reason: "Tool approval requires a user interface." };
        try {
            const allowed = await ctx.ui.confirm(
                "Allow " + event.toolName + "?",
                JSON.stringify(event.input, null, 2).slice(0, 16000),
            );
            if (allowed !== true) return { block: true, reason: "The user declined this tool call." };
        } catch {
            return { block: true, reason: "Tool approval was interrupted." };
        }
    });
}
