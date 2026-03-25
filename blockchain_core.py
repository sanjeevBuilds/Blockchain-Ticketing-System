import copy
import hashlib
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class Block:
    index: int
    timestamp: str
    data: str
    previous_hash: str
    nonce: int
    hash: str


class NodeServer:
    def __init__(self, name: str, difficulty: int = 4) -> None:
        self.name = name
        self.difficulty = difficulty
        self.chain: List[Block] = []
        self.mining_times: List[float] = []
        self.nonce_attempts_total: int = 0
        self.mined_blocks_count: int = 0
        self.create_genesis_block()

    def create_genesis_block(self) -> None:
        genesis = Block(
            index=0,
            timestamp=now_str(),
            data=f"Genesis Block ({self.name})",
            previous_hash="0",
            nonce=0,
            hash="",
        )
        genesis.hash = self.calculate_hash(genesis)
        self.chain = [genesis]

    def calculate_hash(self, block: Block) -> str:
        content = (
            f"{block.index}{block.timestamp}{block.data}"
            f"{block.previous_hash}{block.nonce}"
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def last_block(self) -> Block:
        return self.chain[-1]

    def mine_candidate_block(self, data: str, speed_multiplier: float = 1.0) -> Tuple[Block, float, int]:
        previous = self.last_block()
        candidate = Block(
            index=previous.index + 1,
            timestamp=now_str(),
            data=data,
            previous_hash=previous.hash,
            nonce=0,
            hash="",
        )

        prefix = "0" * self.difficulty
        attempts = 0
        start = time.perf_counter()

        while True:
            candidate.hash = self.calculate_hash(candidate)
            attempts += 1
            if candidate.hash.startswith(prefix):
                break
            candidate.nonce += 1

        elapsed = time.perf_counter() - start
        effective_elapsed = elapsed / max(speed_multiplier, 0.1)

        self.mining_times.append(effective_elapsed)
        self.nonce_attempts_total += attempts
        self.mined_blocks_count += 1

        return candidate, effective_elapsed, attempts

    def append_valid_block(self, block: Block) -> bool:
        if block.previous_hash != self.last_block().hash:
            return False
        if not block.hash.startswith("0" * self.difficulty):
            return False
        if self.calculate_hash(block) != block.hash:
            return False
        self.chain.append(copy.deepcopy(block))
        return True

    def validate_chain(self, chain: Optional[List[Block]] = None) -> bool:
        check_chain = chain if chain is not None else self.chain
        if not check_chain:
            return False

        if check_chain[0].hash != self.calculate_hash(check_chain[0]):
            return False

        for i in range(1, len(check_chain)):
            current = check_chain[i]
            previous = check_chain[i - 1]
            if current.previous_hash != previous.hash:
                return False
            if self.calculate_hash(current) != current.hash:
                return False
            if not current.hash.startswith("0" * self.difficulty):
                return False
        return True

    def set_chain_from_dicts(self, chain_dicts: List[Dict]) -> bool:
        chain: List[Block] = []
        for item in chain_dicts:
            chain.append(
                Block(
                    index=int(item["index"]),
                    timestamp=str(item["timestamp"]),
                    data=str(item["data"]),
                    previous_hash=str(item["previous_hash"]),
                    nonce=int(item["nonce"]),
                    hash=str(item["hash"]),
                )
            )
        if not self.validate_chain(chain):
            return False
        self.chain = chain
        return True

    def chain_as_dicts(self) -> List[Dict]:
        return [asdict(block) for block in self.chain]


def calculate_hash_dict(block: Dict) -> str:
    content = (
        f"{block['index']}{block['timestamp']}{block['data']}"
        f"{block['previous_hash']}{block['nonce']}"
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def validate_chain_dicts(chain: List[Dict], difficulty: int = 4) -> bool:
    if not chain:
        return False

    if calculate_hash_dict(chain[0]) != chain[0]["hash"]:
        return False

    for i in range(1, len(chain)):
        current = chain[i]
        previous = chain[i - 1]
        if current["previous_hash"] != previous["hash"]:
            return False
        if calculate_hash_dict(current) != current["hash"]:
            return False
        if not str(current["hash"]).startswith("0" * difficulty):
            return False

    return True
