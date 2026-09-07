// SPDX-License-Identifier: GPL-3.0-or-later
// Resident JSONL adapter for the same Unified ONNX files used by Voxtype.
use parakeet_rs::{ExecutionConfig, ParakeetUnified, UnifiedStreamingConfig};
use serde_json::{json, Value};
use std::io::{self, BufRead, Write};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    let path = args.get(1).ok_or("Missing model directory")?;
    let threads: usize = args.get(2).ok_or("Missing thread count")?.parse()?;
    let chunk: f32 = args.get(3).ok_or("Missing chunk duration")?.parse()?;
    let config = UnifiedStreamingConfig { left_context_secs: 5.6, chunk_secs: chunk, right_context_secs: chunk };
    let mut model = ParakeetUnified::from_pretrained_with_streaming_config(
        path, Some(ExecutionConfig::new().with_intra_threads(threads)), config)?;
    println!("{}", json!({"ready":true}));
    io::stdout().flush()?;
    for line in io::stdin().lock().lines() {
        let result = (|| -> Result<Value, Box<dyn std::error::Error>> {
            let cmd: Value = serde_json::from_str(&line?)?;
            match cmd["op"].as_str().unwrap_or("") {
                "audio" => {
                    let values = cmd["samples"].as_array().ok_or("Missing audio samples")?;
                    if values.len() > 16000 * 2 { return Err("Audio chunk too large".into()); }
                    let audio: Vec<f32> = values.iter().map(|v| v.as_f64().unwrap_or(0.0) as f32).collect();
                    model.transcribe_chunk(&audio)?;
                }
                "finish" => { model.flush()?; }
                "reset" => model.reset(),
                _ => return Err("Unknown recognition operation".into()),
            }
            Ok(json!({"text": model.get_transcript()}))
        })();
        let response = result.unwrap_or_else(|e| json!({"error":e.to_string()}));
        println!("{}", response);
        io::stdout().flush()?;
    }
    Ok(())
}
