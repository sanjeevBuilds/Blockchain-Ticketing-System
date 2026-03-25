import argparse
import random
import time
from datetime import datetime
from typing import Dict, List, Tuple

import requests
from flask import Flask, redirect, render_template, request, url_for

from blockchain_core import validate_chain_dicts


app = Flask(__name__)

NODE_URLS = {
    "Server A": "http://127.0.0.1:5001",
    "Server B": "http://127.0.0.1:5002",
    "Server C": "http://127.0.0.1:5003",
}

logs: List[str] = []
broadcast_delays: List[float] = []


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_log(section: str, message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    logs.append(f"[{ts}] --- {section.upper()} --- {message}")


def call_node(node_name: str, method: str, path: str, payload: Dict | None = None) -> Dict:
    url = f"{NODE_URLS[node_name]}{path}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=8)
        else:
            response = requests.post(url, json=payload or {}, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        add_log("SYSTEM", f"{node_name} unavailable at {url}: {exc}")
        return {"ok": False, "error": str(exc)}


def state_snapshot() -> Dict[str, Dict[str, str]]:
    snapshot: Dict[str, Dict[str, str]] = {}
    for node_name, node_url in NODE_URLS.items():
        status = call_node(node_name, "GET", "/status")
        chain_resp = call_node(node_name, "GET", "/chain")
        metrics = call_node(node_name, "GET", "/metrics")

        if not status.get("ok", False) or not chain_resp.get("ok", False):
            snapshot[node_name] = {
                "online": "No",
                "endpoint": node_url,
                "chain_length": "N/A",
                "last_index": "N/A",
                "last_hash": "offline",
                "last_timestamp": "N/A",
                "last_data": "N/A",
                "last_previous_hash": "N/A",
                "last_nonce": "N/A",
                "chain_valid": "Unknown",
                "mined_blocks": "N/A",
                "avg_mining_time": "N/A",
                "throughput": "N/A",
                "nonce_attempts": "N/A",
                "avg_receive_delay": "N/A",
            }
            continue

        chain = chain_resp.get("chain", [])
        last_block = chain[-1] if chain else {}
        chain_valid = validate_chain_dicts(chain) if chain else False
        snapshot[node_name] = {
            "online": "Yes",
            "endpoint": node_url,
            "chain_length": str(status["chain_length"]),
            "last_index": str(status["last_index"]),
            "last_hash": str(last_block.get("hash", "")),
            "last_timestamp": str(last_block.get("timestamp", "N/A")),
            "last_data": str(last_block.get("data", "N/A")),
            "last_previous_hash": str(last_block.get("previous_hash", "N/A")),
            "last_nonce": str(last_block.get("nonce", "N/A")),
            "chain_valid": "Yes" if chain_valid else "No",
            "mined_blocks": str(metrics.get("mined_blocks", "N/A")),
            "avg_mining_time": f"{float(metrics.get('avg_mining_time', 0.0)):.4f}s" if metrics.get("ok", False) else "N/A",
            "throughput": f"{float(metrics.get('throughput', 0.0)):.4f} blk/s" if metrics.get("ok", False) else "N/A",
            "nonce_attempts": str(metrics.get("nonce_attempts_total", "N/A")),
            "avg_receive_delay": f"{float(metrics.get('avg_receive_delay', 0.0)):.4f}s" if metrics.get("ok", False) else "N/A",
        }
    return snapshot


def broadcast_block(sender_name: str, block: Dict) -> None:
    add_log("BROADCAST", f"{sender_name} broadcasting block #{block['index']}...")
    for node_name in NODE_URLS:
        delay = random.uniform(0.08, 0.2)
        time.sleep(delay)
        broadcast_delays.append(delay)
        add_log(
            "BROADCAST",
            f"{node_name} received block #{block['index']} after {delay:.4f}s and is validating...",
        )
        result = call_node(node_name, "POST", "/receive_block", {"block": block})
        if result.get("accepted"):
            add_log("BROADCAST", f"{node_name} validation success: block added")
        else:
            add_log("BROADCAST", f"{node_name} validation failed: block rejected")


def start_mining_all() -> None:
    add_log("MINING", "Start Mining (All Servers) clicked")
    mining_data = f"Shared transaction set at {now_str()}"

    results: List[Tuple[str, Dict, float, int]] = []
    for node_name in NODE_URLS:
        response = call_node(node_name, "POST", "/mine", {"data": mining_data})
        if not response.get("ok", False):
            continue
        total_time = float(response["effective_time"])
        attempts = int(response["attempts"])
        block = response["block"]
        add_log(
            "MINING",
            f"{node_name} mined candidate block #{block['index']} in {total_time:.4f}s "
            f"(nonce attempts: {attempts})",
        )
        results.append((node_name, block, total_time, attempts))

    if not results:
        add_log("MINING", "No servers available to mine")
        return

    winner_name, winner_block, winner_time, _ = min(results, key=lambda item: item[2])
    add_log("MINING", f"Winner: {winner_name} (fastest mining time: {winner_time:.4f}s)")
    broadcast_block(winner_name, winner_block)


def mine_single(node_name: str) -> None:
    add_log("MINING", f"Mine Block ({node_name}) clicked")
    response = call_node(node_name, "POST", "/mine", {"data": f"Block from {node_name} at {now_str()}"})
    if not response.get("ok", False):
        return

    block = response["block"]
    add_log(
        "MINING",
        f"{node_name} mined block #{block['index']} in {response['effective_time']:.4f}s "
        f"(nonce attempts: {response['attempts']})",
    )
    broadcast_block(node_name, block)


def apply_consensus() -> None:
    add_log("CONSENSUS", "Apply Consensus clicked")
    chains: Dict[str, List[Dict]] = {}
    before_lengths: Dict[str, int] = {}

    for node_name in NODE_URLS:
        response = call_node(node_name, "GET", "/chain")
        if not response.get("ok", False):
            continue
        chains[node_name] = response["chain"]
        before_lengths[node_name] = len(response["chain"])

    add_log("CONSENSUS", f"Chain lengths before: {before_lengths}")

    valid_chains: List[Tuple[str, List[Dict]]] = []
    for node_name, chain in chains.items():
        is_valid = validate_chain_dicts(chain)
        add_log("CONSENSUS", f"{node_name} chain valid: {is_valid}")
        if is_valid:
            valid_chains.append((node_name, chain))

    if not valid_chains:
        add_log("CONSENSUS", "No valid chains found. Consensus skipped.")
        return

    winner_name, longest_chain = max(valid_chains, key=lambda item: len(item[1]))
    for node_name in NODE_URLS:
        call_node(node_name, "POST", "/replace_chain", {"chain": longest_chain})

    after_lengths = {}
    for node_name in NODE_URLS:
        response = call_node(node_name, "GET", "/chain")
        if response.get("ok", False):
            after_lengths[node_name] = len(response["chain"])
    add_log("CONSENSUS", f"Longest valid chain chosen from {winner_name}")
    add_log("CONSENSUS", f"Chain lengths after:  {after_lengths}")


def simulate_invalid_block_attack() -> None:
    add_log("ATTACK", "Simulate Invalid Block Attack clicked")
    tamper = call_node("Server B", "POST", "/tamper")
    if not tamper.get("ok", False):
        return
    if not tamper.get("tampered", False):
        add_log("ATTACK", "Not enough blocks to tamper. Mine at least one block first.")
        return

    add_log("ATTACK", tamper["message"])
    chain_resp = call_node("Server B", "GET", "/chain")
    is_valid = validate_chain_dicts(chain_resp.get("chain", [])) if chain_resp.get("ok") else False
    add_log("ATTACK", f"Server B chain valid after tampering: {is_valid}")
    if not is_valid:
        add_log("ATTACK", "Validation failure detected. Running consensus to reject invalid chain.")
        apply_consensus()


def simulate_51_percent_attack() -> None:
    add_log("ATTACK", "Simulate 51% Attack clicked")
    call_node("Server C", "POST", "/set_power", {"power": 2.5})
    add_log("ATTACK", "Server C gets higher mining power and mines faster")

    # Sync attacker with longest valid public chain before private mining.
    chains = []
    for node_name in NODE_URLS:
        response = call_node(node_name, "GET", "/chain")
        if response.get("ok") and validate_chain_dicts(response["chain"]):
            chains.append(response["chain"])
    if chains:
        longest = max(chains, key=len)
        call_node("Server C", "POST", "/replace_chain", {"chain": longest})

    for i in range(3):
        response = call_node(
            "Server C",
            "POST",
            "/mine_and_append",
            {"data": f"51% attacker private block {i + 1} at {now_str()}"},
        )
        if response.get("ok", False):
            add_log(
                "ATTACK",
                f"Server C mined extra block #{response['block']['index']} in "
                f"{response['effective_time']:.4f}s (nonce attempts: {response['attempts']})",
            )

    lengths = {}
    for node_name in NODE_URLS:
        chain_resp = call_node(node_name, "GET", "/chain")
        if chain_resp.get("ok"):
            lengths[node_name] = len(chain_resp["chain"])
    add_log("ATTACK", f"Chain lengths after attack mining: {lengths}")
    add_log("ATTACK", "Applying consensus to see if network adopts attacker chain")
    apply_consensus()
    call_node("Server C", "POST", "/set_power", {"power": 1.0})


def show_performance_metrics() -> None:
    add_log("PERFORMANCE", "Show Performance Metrics clicked")
    avg_network_delay = sum(broadcast_delays) / len(broadcast_delays) if broadcast_delays else 0.0
    max_network_delay = max(broadcast_delays) if broadcast_delays else 0.0
    add_log(
        "PERFORMANCE",
        f"Controller broadcast delay: samples={len(broadcast_delays)}, "
        f"avg={avg_network_delay:.4f}s, max={max_network_delay:.4f}s",
    )

    total_blocks = 0
    total_mining_time = 0.0
    for node_name in NODE_URLS:
        metrics = call_node(node_name, "GET", "/metrics")
        if not metrics.get("ok", False):
            continue
        total_blocks += int(metrics["mined_blocks"])
        total_mining_time += float(metrics["total_mining_time"])
        add_log(
            "PERFORMANCE",
            f"{node_name}: mined={metrics['mined_blocks']}, "
            f"avg_mining_time={metrics['avg_mining_time']:.4f}s, "
            f"nonce_attempts={metrics['nonce_attempts_total']}, "
            f"throughput={metrics['throughput']:.4f} blocks/s",
        )

    effective_network_time = total_mining_time + sum(broadcast_delays)
    overall_throughput = total_blocks / effective_network_time if effective_network_time > 0 else 0.0
    add_log("PERFORMANCE", f"Overall throughput (including delay): {overall_throughput:.4f} blocks/s")

    # Simple projection for scalability as node count grows.
    base_block_time = (total_mining_time / total_blocks) if total_blocks > 0 else 1.0
    for projected_nodes in [3, 5, 10, 20]:
        projected_delay = avg_network_delay * max(projected_nodes - 1, 1)
        projected_time = base_block_time + projected_delay
        projected_throughput = 1.0 / projected_time if projected_time > 0 else 0.0
        add_log(
            "PERFORMANCE",
            f"Scalability projection ({projected_nodes} nodes): "
            f"estimated_block_time={projected_time:.4f}s, "
            f"estimated_throughput={projected_throughput:.4f} blocks/s",
        )


def reset_system() -> None:
    logs.clear()
    broadcast_delays.clear()
    for node_name in NODE_URLS:
        call_node(node_name, "POST", "/reset")
    add_log("SYSTEM", "System reset complete")


add_log("SYSTEM", "Controller initialized. Ensure Server A/B/C are running on ports 5001-5003")


@app.get("/")
def index():
    state = state_snapshot()
    online_nodes = sum(1 for details in state.values() if details["online"] == "Yes")
    return render_template(
        "index.html",
        logs=logs[-300:],
        state=state,
        online_nodes=online_nodes,
        total_nodes=len(NODE_URLS),
        last_updated=datetime.now().strftime("%H:%M:%S"),
    )


@app.post("/action")
def action():
    op = request.form.get("op", "")

    if op == "start_mining_all":
        start_mining_all()
    elif op == "mine_a":
        mine_single("Server A")
    elif op == "mine_b":
        mine_single("Server B")
    elif op == "consensus":
        apply_consensus()
    elif op == "invalid_attack":
        simulate_invalid_block_attack()
    elif op == "attack_51":
        simulate_51_percent_attack()
    elif op == "performance":
        show_performance_metrics()
    elif op == "reset":
        reset_system()

    return redirect(url_for("index"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)
