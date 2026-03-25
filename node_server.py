import argparse
import random
import time
from datetime import datetime

from flask import Flask, jsonify, request

from blockchain_core import Block, NodeServer


def create_app(node_name: str) -> Flask:
    app = Flask(__name__)
    node = NodeServer(node_name)
    mining_power = {"value": 1.0}
    received_delays = []
    logs = []

    def add_log(message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        logs.append(f"[{ts}] {message}")

    def dashboard_snapshot() -> dict:
        last = node.last_block()
        total_mining_time = sum(node.mining_times)
        avg_mining_time = total_mining_time / len(node.mining_times) if node.mining_times else 0.0
        throughput = node.mined_blocks_count / total_mining_time if total_mining_time > 0 else 0.0
        avg_receive_delay = sum(received_delays) / len(received_delays) if received_delays else 0.0

        return {
            "name": node.name,
            "chain_length": len(node.chain),
            "last_index": last.index,
            "last_hash": last.hash,
            "last_timestamp": last.timestamp,
            "last_data": last.data,
            "last_previous_hash": last.previous_hash,
            "last_nonce": last.nonce,
            "mining_power": mining_power["value"],
            "chain_valid": node.validate_chain(),
            "mined_blocks": node.mined_blocks_count,
            "nonce_attempts_total": node.nonce_attempts_total,
            "avg_mining_time": avg_mining_time,
            "throughput": throughput,
            "avg_receive_delay": avg_receive_delay,
            "receive_delay_samples": len(received_delays),
            "logs": logs[-120:],
            "last_updated": datetime.now().strftime("%H:%M:%S"),
        }

    @app.get("/")
    def home():
        snapshot = dashboard_snapshot()
        valid_class = "ok" if snapshot["chain_valid"] else "bad"
        valid_text = "Yes" if snapshot["chain_valid"] else "No"
        recent_logs = "".join(f"<div>{line}</div>" for line in snapshot["logs"])

        return f"""
                <html>
                <head>
                    <title>Node Dashboard</title>
                    <meta name='viewport' content='width=device-width, initial-scale=1'>
                    <style>
                        :root{{--bg:#f3f7f5;--panel:#fff;--line:#d4dfd8;--text:#122019;--muted:#4f665d;--accent:#0a8f5b;}}
                        *{{box-sizing:border-box;}}
                        body{{margin:0;font-family:Trebuchet MS,Segoe UI,Tahoma,sans-serif;color:var(--text);background:radial-gradient(circle at top right,#d7eee1 0%,rgba(215,238,225,0) 45%),linear-gradient(180deg,#ebf3ef 0%,#f8fbf9 100%);}}
                        .container{{max-width:980px;margin:0 auto;padding:18px 14px 28px;}}
                        .top{{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap;}}
                        h1{{margin:0;font-size:1.6rem;}}
                        .sub{{margin:5px 0 0;color:var(--muted);font-size:.95rem;}}
                        .chips{{display:flex;gap:8px;flex-wrap:wrap;}}
                        .chip{{border:1px solid #b7d7c5;background:#e5f4ec;color:#0d5f40;border-radius:999px;padding:6px 10px;font-size:.8rem;font-weight:700;}}
                        .panel{{margin-top:14px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;box-shadow:0 8px 22px rgba(20,52,39,.05);}}
                        .panel h2{{margin:0 0 10px;font-size:1.05rem;}}
                        .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px 12px;}}
                        .item{{margin:0;font-size:.92rem;}}
                        .mono{{font-family:Consolas,Courier New,monospace;word-break:break-all;font-size:.82rem;color:#1f4637;}}
                        .ok{{color:#0b6d44;font-weight:700;}}
                        .bad{{color:#b12f2f;font-weight:700;}}
                        .links a{{display:inline-block;margin-right:8px;color:#0a5d8f;text-decoration:none;}}
                        .links a:hover{{text-decoration:underline;}}
                        .log-head{{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;}}
                        button{{border:1px solid #ccd8d1;border-radius:8px;background:#fff;padding:7px 10px;font-size:.8rem;cursor:pointer;}}
                        button:hover{{border-color:var(--accent);color:var(--accent);}}
                        .log{{margin-top:10px;border:1px solid #173126;border-radius:8px;background:#102017;color:#d9ece2;font-family:Consolas,Courier New,monospace;font-size:.84rem;padding:10px;height:320px;overflow:auto;line-height:1.42;}}
                        @media (max-width:640px){{h1{{font-size:1.3rem;}}}}
                    </style>
                </head>
                <body>
                    <main class='container'>
                        <section class='top'>
                            <div>
                                <h1 id='nodeName'>{snapshot['name']} Node Dashboard</h1>
                                <p class='sub'>Independent node server with local chain, mining, and validation logic.</p>
                            </div>
                            <div class='chips'>
                                <span class='chip' id='chipChain'>Chain Length: {snapshot['chain_length']}</span>
                                <span class='chip' id='chipPower'>Mining Power: {snapshot['mining_power']}</span>
                                <span class='chip' id='chipValid'>Valid: {valid_text}</span>
                                <span class='chip' id='chipUpdated'>Updated: {snapshot['last_updated']}</span>
                            </div>
                        </section>

                        <section class='panel'>
                            <h2>Node Links</h2>
                            <div class='links'>
                                <a href='http://127.0.0.1:5000' target='_blank' rel='noopener'>Controller</a>
                                <a href='http://127.0.0.1:5001' target='_blank' rel='noopener'>Server A</a>
                                <a href='http://127.0.0.1:5002' target='_blank' rel='noopener'>Server B</a>
                                <a href='http://127.0.0.1:5003' target='_blank' rel='noopener'>Server C</a>
                            </div>
                        </section>

                        <section class='panel'>
                            <h2>Latest Block Properties</h2>
                            <div class='grid'>
                                <p class='item'><b>index:</b> <span id='lastIndex'>{snapshot['last_index']}</span></p>
                                <p class='item'><b>timestamp:</b> <span id='lastTimestamp'>{snapshot['last_timestamp']}</span></p>
                                <p class='item'><b>nonce:</b> <span id='lastNonce'>{snapshot['last_nonce']}</span></p>
                                <p class='item'><b>chain_valid:</b> <span id='chainValid' class='{valid_class}'>{valid_text}</span></p>
                            </div>
                            <p class='item'><b>data:</b><br><span id='lastData' class='mono'>{snapshot['last_data']}</span></p>
                            <p class='item'><b>previous_hash:</b><br><span id='lastPrevHash' class='mono'>{snapshot['last_previous_hash']}</span></p>
                            <p class='item'><b>hash:</b><br><span id='lastHash' class='mono'>{snapshot['last_hash']}</span></p>
                        </section>

                        <section class='panel'>
                            <h2>Performance Snapshot</h2>
                            <div class='grid'>
                                <p class='item'><b>Mined Blocks:</b> <span id='minedBlocks'>{snapshot['mined_blocks']}</span></p>
                                <p class='item'><b>Nonce Attempts:</b> <span id='nonceAttempts'>{snapshot['nonce_attempts_total']}</span></p>
                                <p class='item'><b>Avg Mining Time:</b> <span id='avgMiningTime'>{snapshot['avg_mining_time']:.4f}s</span></p>
                                <p class='item'><b>Throughput:</b> <span id='throughput'>{snapshot['throughput']:.4f} blocks/s</span></p>
                                <p class='item'><b>Avg Receive Delay:</b> <span id='avgDelay'>{snapshot['avg_receive_delay']:.4f}s</span></p>
                                <p class='item'><b>Delay Samples:</b> <span id='delaySamples'>{snapshot['receive_delay_samples']}</span></p>
                            </div>
                        </section>

                        <section class='panel'>
                            <div class='log-head'>
                                <h2>Recent Logs</h2>
                                <button type='button' id='pauseBtn'>Pause Live Updates</button>
                            </div>
                            <div class='log' id='logBox'>{recent_logs}</div>
                        </section>
                    </main>

                    <script>
                        const logBox = document.getElementById('logBox');
                        if (logBox) {{
                            logBox.scrollTop = logBox.scrollHeight;
                        }}

                        let liveUpdates = true;
                        const btn = document.getElementById('pauseBtn');
                        if (btn) {{
                            btn.addEventListener('click', () => {{
                                liveUpdates = !liveUpdates;
                                btn.textContent = liveUpdates ? 'Pause Live Updates' : 'Resume Live Updates';
                            }});
                        }}

                        function setText(id, value) {{
                            const el = document.getElementById(id);
                            if (el) el.textContent = value;
                        }}

                        async function refreshDashboard() {{
                            if (!liveUpdates) return;
                            try {{
                                const response = await fetch('/dashboard_data', {{ cache: 'no-store' }});
                                const data = await response.json();
                                if (!data.ok) return;

                                setText('chipChain', `Chain Length: ${{data.chain_length}}`);
                                setText('chipPower', `Mining Power: ${{data.mining_power}}`);
                                setText('chipValid', `Valid: ${{data.chain_valid ? 'Yes' : 'No'}}`);
                                setText('chipUpdated', `Updated: ${{data.last_updated}}`);

                                setText('lastIndex', data.last_index);
                                setText('lastTimestamp', data.last_timestamp);
                                setText('lastNonce', data.last_nonce);
                                const chainValidEl = document.getElementById('chainValid');
                                if (chainValidEl) {{
                                    chainValidEl.textContent = data.chain_valid ? 'Yes' : 'No';
                                    chainValidEl.className = data.chain_valid ? 'ok' : 'bad';
                                }}

                                setText('lastData', data.last_data);
                                setText('lastPrevHash', data.last_previous_hash);
                                setText('lastHash', data.last_hash);

                                setText('minedBlocks', data.mined_blocks);
                                setText('nonceAttempts', data.nonce_attempts_total);
                                setText('avgMiningTime', `${{Number(data.avg_mining_time).toFixed(4)}}s`);
                                setText('throughput', `${{Number(data.throughput).toFixed(4)}} blocks/s`);
                                setText('avgDelay', `${{Number(data.avg_receive_delay).toFixed(4)}}s`);
                                setText('delaySamples', data.receive_delay_samples);

                                if (logBox) {{
                                    const stickToBottom = logBox.scrollTop + logBox.clientHeight >= logBox.scrollHeight - 8;
                                    logBox.innerHTML = '';
                                    (data.logs || []).forEach((line) => {{
                                        const row = document.createElement('div');
                                        row.textContent = line;
                                        logBox.appendChild(row);
                                    }});
                                    if (stickToBottom) {{
                                        logBox.scrollTop = logBox.scrollHeight;
                                    }}
                                }}
                            }} catch (_error) {{
                                // Keep current values if a single poll fails.
                            }}
                        }}

                        setInterval(refreshDashboard, 1500);
                    </script>
                </body>
                </html>
            """

    @app.get("/dashboard_data")
    def dashboard_data():
        data = dashboard_snapshot()
        data["ok"] = True
        return jsonify(data)

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "name": node.name})

    @app.get("/status")
    def status():
        last = node.last_block()
        return jsonify(
            {
                "ok": True,
                "name": node.name,
                "chain_length": len(node.chain),
                "last_index": last.index,
                "last_hash": last.hash,
            }
        )

    @app.get("/chain")
    def chain():
        return jsonify({"ok": True, "name": node.name, "chain": node.chain_as_dicts(), "valid": node.validate_chain()})

    @app.post("/mine")
    def mine():
        payload = request.get_json(silent=True) or {}
        data = payload.get("data", f"Block from {node.name}")
        block, effective_time, attempts = node.mine_candidate_block(data, speed_multiplier=mining_power["value"])
        add_log(f"Mined candidate block #{block.index} in {effective_time:.4f}s with {attempts} attempts")
        return jsonify(
            {
                "ok": True,
                "block": {
                    "index": block.index,
                    "timestamp": block.timestamp,
                    "data": block.data,
                    "previous_hash": block.previous_hash,
                    "nonce": block.nonce,
                    "hash": block.hash,
                },
                "effective_time": effective_time,
                "attempts": attempts,
            }
        )

    @app.post("/mine_and_append")
    def mine_and_append():
        payload = request.get_json(silent=True) or {}
        data = payload.get("data", f"Private block from {node.name}")
        block, effective_time, attempts = node.mine_candidate_block(data, speed_multiplier=mining_power["value"])
        accepted = node.append_valid_block(block)
        add_log(f"Mined and appended block #{block.index}: accepted={accepted}")
        return jsonify(
            {
                "ok": True,
                "accepted": accepted,
                "block": {
                    "index": block.index,
                    "timestamp": block.timestamp,
                    "data": block.data,
                    "previous_hash": block.previous_hash,
                    "nonce": block.nonce,
                    "hash": block.hash,
                },
                "effective_time": effective_time,
                "attempts": attempts,
            }
        )

    @app.post("/receive_block")
    def receive_block():
        payload = request.get_json(silent=True) or {}
        item = payload.get("block")
        if not item:
            return jsonify({"ok": False, "accepted": False, "error": "missing block"}), 400

        block = Block(
            index=int(item["index"]),
            timestamp=str(item["timestamp"]),
            data=str(item["data"]),
            previous_hash=str(item["previous_hash"]),
            nonce=int(item["nonce"]),
            hash=str(item["hash"]),
        )

        delay = random.uniform(0.03, 0.15)
        time.sleep(delay)
        received_delays.append(delay)

        accepted = node.append_valid_block(block)
        add_log(f"Received block #{block.index}, accepted={accepted}, delay={delay:.4f}s")
        return jsonify({"ok": True, "accepted": accepted, "delay": delay})

    @app.post("/replace_chain")
    def replace_chain():
        payload = request.get_json(silent=True) or {}
        incoming_chain = payload.get("chain", [])
        replaced = node.set_chain_from_dicts(incoming_chain)
        add_log(f"Replace chain requested: replaced={replaced}, new_len={len(node.chain)}")
        return jsonify({"ok": True, "replaced": replaced, "chain_length": len(node.chain)})

    @app.post("/tamper")
    def tamper():
        if len(node.chain) < 2:
            return jsonify({"ok": True, "tampered": False, "message": "Not enough blocks to tamper."})
        old_data = node.chain[1].data
        node.chain[1].data = f"TAMPERED DATA ({datetime.now().strftime('%H:%M:%S')})"
        add_log("Tamper attack: modified block #1 data")
        return jsonify(
            {
                "ok": True,
                "tampered": True,
                "message": f"{node.name} modified block #1 data from '{old_data}' to '{node.chain[1].data}'",
            }
        )

    @app.post("/set_power")
    def set_power():
        payload = request.get_json(silent=True) or {}
        mining_power["value"] = float(payload.get("power", 1.0))
        add_log(f"Mining power set to {mining_power['value']}")
        return jsonify({"ok": True, "power": mining_power["value"]})

    @app.get("/metrics")
    def metrics():
        total_mining_time = sum(node.mining_times)
        throughput = node.mined_blocks_count / total_mining_time if total_mining_time > 0 else 0.0
        avg_mining_time = total_mining_time / len(node.mining_times) if node.mining_times else 0.0
        avg_receive_delay = sum(received_delays) / len(received_delays) if received_delays else 0.0

        return jsonify(
            {
                "ok": True,
                "name": node.name,
                "mined_blocks": node.mined_blocks_count,
                "total_mining_time": total_mining_time,
                "avg_mining_time": avg_mining_time,
                "nonce_attempts_total": node.nonce_attempts_total,
                "throughput": throughput,
                "avg_receive_delay": avg_receive_delay,
                "receive_delay_samples": len(received_delays),
            }
        )

    @app.post("/reset")
    def reset():
        node.create_genesis_block()
        node.mining_times.clear()
        node.nonce_attempts_total = 0
        node.mined_blocks_count = 0
        received_delays.clear()
        logs.clear()
        mining_power["value"] = 1.0
        add_log("Node reset complete")
        return jsonify({"ok": True})

    add_log("Node initialized")
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    app = create_app(args.name)
    app.run(host=args.host, port=args.port, debug=args.debug)
