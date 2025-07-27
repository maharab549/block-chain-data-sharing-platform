import hashlib
import json
import time
from typing import List, Dict, Any, Optional
import logging
from copy import deepcopy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('blockchain.log')
    ]
)
logger = logging.getLogger(__name__)

class Block:
    """Represents a block in the blockchain."""
    
    def __init__(self, index: int, transactions: List[Dict], previous_hash: str, nonce: int = 0):
        """Initialize a block with index, transactions, previous hash, and nonce."""
        self.index: int = index
        self.timestamp: float = time.time()
        self.transactions: List[Dict] = deepcopy(transactions)  # Deep copy to prevent external modification
        self.previous_hash: str = previous_hash
        self.nonce: int = nonce
        self.hash: str = self.calculate_hash()
        logger.debug(f"Created block {index} with hash {self.hash[:10]}")

    def calculate_hash(self) -> str:
        """Calculate SHA256 hash of the block."""
        try:
            block_dict = {
                "index": self.index,
                "timestamp": self.timestamp,
                "transactions": self.transactions,
                "previous_hash": self.previous_hash,
                "nonce": self.nonce
            }
            block_string = json.dumps(block_dict, sort_keys=True).encode()
            return hashlib.sha256(block_string).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating block hash: {e}")
            raise ValueError(f"Failed to calculate block hash: {e}")

    def __repr__(self) -> str:
        """String representation of the block."""
        return f"Block(Index: {self.index}, Hash: {self.hash[:10]}..., Transactions: {len(self.transactions)})"

    def validate(self, previous_block: Optional['Block'] = None) -> bool:
        """Validate block integrity."""
        try:
            # Recalculate hash to verify integrity
            if self.hash != self.calculate_hash():
                logger.error(f"Block {self.index} hash verification failed")
                return False
            
            # Verify previous hash if provided
            if previous_block and self.previous_hash != previous_block.hash:
                logger.error(f"Block {self.index} previous hash mismatch")
                return False
                
            # Validate transaction format
            for tx in self.transactions:
                required_keys = {'sender', 'recipient', 'data_hash', 'metadata'}
                if not all(key in tx for key in required_keys):
                    logger.error(f"Invalid transaction format in block {self.index}")
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Error validating block {self.index}: {e}")
            return False

class Blockchain:
    """Implements a blockchain for secure data sharing."""
    
    def __init__(self, difficulty: int = 4):
        """Initialize blockchain with genesis block."""
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict] = []
        self.difficulty: int = difficulty  # Number of leading zeros for proof-of-work
        self.create_genesis_block()
        logger.info("Blockchain initialized")

    def create_genesis_block(self) -> None:
        """Create and add the genesis block."""
        try:
            genesis_block = Block(
                index=0,
                transactions=[],
                previous_hash='0',
                nonce=100
            )
            if genesis_block.validate():
                self.chain.append(genesis_block)
                logger.info("Genesis block created")
            else:
                logger.error("Failed to validate genesis block")
                raise ValueError("Invalid genesis block")
        except Exception as e:
            logger.error(f"Error creating genesis block: {e}")
            raise

    @property
    def last_block(self) -> Block:
        """Return the last block in the chain."""
        if not self.chain:
            raise ValueError("Blockchain is empty")
        return self.chain[-1]

    def proof_of_work(self, last_proof: int) -> int:
        """Perform proof-of-work to find a valid nonce."""
        try:
            proof = 0
            start_time = time.time()
            while not self.valid_proof(last_proof, proof):
                proof += 1
                if proof % 100000 == 0:  # Log progress for long-running PoW
                    logger.debug(f"Proof-of-work progress: {proof} attempts")
            logger.info(f"Proof-of-work completed in {time.time() - start_time:.2f} seconds")
            return proof
        except Exception as e:
            logger.error(f"Error in proof-of-work: {e}")
            raise

    def valid_proof(self, last_proof: int, proof: int) -> bool:
        """Validate proof by checking if hash has required leading zeros."""
        try:
            guess = f'{last_proof}{proof}'.encode()
            guess_hash = hashlib.sha256(guess).hexdigest()
            return guess_hash[:self.difficulty] == "0" * self.difficulty
        except Exception as e:
            logger.error(f"Error validating proof: {e}")
            return False

    def create_new_block(self, nonce: int, previous_hash: Optional[str] = None) -> Block:
        """Create and add a new block to the chain."""
        try:
            block = Block(
                index=len(self.chain),
                transactions=self.pending_transactions,
                previous_hash=previous_hash or self.last_block.hash,
                nonce=nonce
            )
            if not block.validate(self.last_block):
                logger.error(f"Invalid block created at index {len(self.chain)}")
                raise ValueError("Block validation failed")
            
            self.pending_transactions = []
            self.chain.append(block)
            logger.info(f"New block created: Index={block.index}, Hash={block.hash[:10]}")
            return block
        except Exception as e:
            logger.error(f"Error creating block: {e}")
            raise

    def add_new_transaction(self, sender: str, recipient: str, data_hash: str, metadata: Dict[str, Any]) -> int:
        """Add a new transaction to pending transactions."""
        try:
            if not all([sender.strip(), recipient.strip(), data_hash.strip(), metadata]):
                logger.error("Invalid transaction: Missing required fields")
                raise ValueError("All transaction fields must be non-empty")
                
            transaction = {
                'sender': sender.strip(),
                'recipient': recipient.strip(),
                'data_hash': data_hash.strip(),
                'metadata': deepcopy(metadata)  # Prevent external modification
            }
            self.pending_transactions.append(transaction)
            logger.info(f"Added transaction: Sender={sender}, Recipient={recipient}, DataHash={data_hash[:10]}...")
            return self.last_block.index + 1
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            raise

    def has_access(self, recipient: str, data_hash: str) -> bool:
        """Check if a recipient has access to a file by data hash."""
        try:
            recipient = recipient.strip()
            data_hash = data_hash.strip()
            
            # Check chain
            for block in self.chain:
                for transaction in block.transactions:
                    if transaction["recipient"] == recipient and transaction["data_hash"] == data_hash:
                        logger.debug(f"Access found in chain: Recipient={recipient}, Hash={data_hash[:10]}...")
                        return True
            
            # Check pending transactions
            for transaction in self.pending_transactions:
                if transaction["recipient"] == recipient and transaction["data_hash"] == data_hash:
                    logger.debug(f"Access found in pending: Recipient={recipient}, Hash={data_hash[:10]}...")
                    return True
                    
            logger.debug(f"No access found: Recipient={recipient}, Hash={data_hash[:10]}...")
            return False
        except Exception as e:
            logger.error(f"Error checking access: {e}")
            return False

    def validate_chain(self) -> bool:
        """Validate the entire blockchain."""
        try:
            for i, block in enumerate(self.chain):
                if i == 0:
                    if block.previous_hash != '0':
                        logger.error("Invalid genesis block previous hash")
                        return False
                else:
                    if not block.validate(self.chain[i-1]):
                        logger.error(f"Invalid block at index {i}")
                        return False
            logger.info("Blockchain validation successful")
            return True
        except Exception as e:
            logger.error(f"Error validating blockchain: {e}")
            return False

# Example Usage
if __name__ == '__main__':
    try:
        blockchain = Blockchain(difficulty=4)
        logger.info("Mining genesis block...")
        # Genesis block is created during initialization

        # Add some transactions
        blockchain.add_new_transaction("Alice", "Bob", "hash123", {"filename": "document1.pdf"})
        blockchain.add_new_transaction("Bob", "Charlie", "hash456", {"filename": "image.jpg"})

        logger.info("Mining Block 1...")
        proof = blockchain.proof_of_work(blockchain.last_block.nonce)
        block = blockchain.create_new_block(proof)
        logger.info(f"Block 1 mined: {block}")

        blockchain.add_new_transaction("Charlie", "David", "hash789", {"filename": "report.docx"})

        logger.info("Mining Block 2...")
        proof = blockchain.proof_of_work(blockchain.last_block.nonce)
        block = blockchain.create_new_block(proof)
        logger.info(f"Block 2 mined: {block}")

        logger.info("\nBlockchain:")
        for block in blockchain.chain:
            print(f"Index: {block.index}")
            print(f"Timestamp: {time.ctime(block.timestamp)}")
            print(f"Transactions: {block.transactions}")
            print(f"Previous Hash: {block.previous_hash}")
            print(f"Nonce: {block.nonce}")
            print(f"Hash: {block.hash}\n")

        # Validate the entire chain
        is_valid = blockchain.validate_chain()
        print(f"Blockchain valid: {is_valid}")
    except Exception as e:
        logger.error(f"Error in example usage: {e}")
        print(f"Error: {e}")