import ipfshttpclient
import hashlib
import os
import logging
from typing import Optional, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IPFSHandler:
    """A class to handle IPFS file operations with error handling and validation."""
    
    def __init__(self, ipfs_endpoint: str = '/ip4/127.0.0.1/tcp/5001'):
        """Initialize IPFS client with specified endpoint."""
        self.ipfs_endpoint = ipfs_endpoint
        self.client = None
        self.connect()

    def connect(self) -> bool:
        """Establish connection to IPFS node."""
        try:
            self.client = ipfshttpclient.connect(self.ipfs_endpoint)
            logger.info("Successfully connected to IPFS node")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IPFS node: {e}")
            return False

    def add_file_to_ipfs(self, filepath: str) -> Optional[str]:
        """Add a file to IPFS and return its CID."""
        if not Path(filepath).is_file():
            logger.error(f"File not found: {filepath}")
            return None

        try:
            res = self.client.add(filepath)
            cid = res["Hash"]
            logger.info(f"File added to IPFS with CID: {cid}")
            return cid
        except Exception as e:
            logger.error(f"Error adding file to IPFS: {e}")
            return None

    def get_file_from_ipfs(self, ipfs_hash: str, output_filepath: str) -> bool:
        """Retrieve a file from IPFS using its CID."""
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_filepath) or '.'
            os.makedirs(output_dir, exist_ok=True)
            
            self.client.get(ipfs_hash, output_filepath)
            logger.info(f"File {ipfs_hash} retrieved and saved to {output_filepath}")
            return True
        except Exception as e:
            logger.error(f"Error getting file from IPFS: {e}")
            return False

    @staticmethod
    def calculate_file_hash(filepath: str, chunk_size: int = 4096) -> Optional[str]:
        """Calculate SHA256 hash of a file."""
        if not Path(filepath).is_file():
            logger.error(f"File not found for hashing: {filepath}")
            return None

        try:
            hasher = hashlib.sha256()
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
            file_hash = hasher.hexdigest()
            logger.info(f"Calculated SHA256 hash for {filepath}: {file_hash}")
            return file_hash
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return None

    def verify_file_integrity(self, original_filepath: str, retrieved_filepath: str) -> Tuple[bool, Optional[str]]:
        """Verify integrity of retrieved file by comparing hashes."""
        original_hash = self.calculate_file_hash(original_filepath)
        retrieved_hash = self.calculate_file_hash(retrieved_filepath)
        
        if original_hash is None or retrieved_hash is None:
            return False, "Hash calculation failed"
        
        if original_hash == retrieved_hash:
            logger.info("File integrity verified: Hashes match")
            return True, "File integrity verified"
        else:
            logger.warning("File integrity compromised: Hashes do not match")
            return False, f"Hashes differ - Original: {original_hash}, Retrieved: {retrieved_hash}"

def main():
    """Main function to demonstrate IPFS file operations."""
    # Initialize IPFS handler
    ipfs_handler = IPFSHandler()
    
    # Create test file
    test_file = "test_data.txt"
    try:
        with open(test_file, "w") as f:
            f.write("This is some sensitive data to be shared securely.")
        logger.info(f"Created test file: {test_file}")
        
        # Add file to IPFS
        ipfs_cid = ipfs_handler.add_file_to_ipfs(test_file)
        if not ipfs_cid:
            logger.error("Failed to add file to IPFS")
            return

        # Calculate local file hash
        local_file_hash = ipfs_handler.calculate_file_hash(test_file)
        if not local_file_hash:
            logger.error("Failed to calculate local file hash")
            return

        # Retrieve file from IPFS
        retrieved_file = "retrieved_data.txt"
        if not ipfs_handler.get_file_from_ipfs(ipfs_cid, retrieved_file):
            logger.error("Failed to retrieve file from IPFS")
            return

        # Verify file integrity
        is_valid, message = ipfs_handler.verify_file_integrity(test_file, retrieved_file)
        logger.info(message)

    finally:
        # Cleanup
        for file in [test_file, retrieved_file]:
            if Path(file).exists():
                try:
                    os.remove(file)
                    logger.info(f"Cleaned up file: {file}")
                except Exception as e:
                    logger.error(f"Error cleaning up file {file}: {e}")

if __name__ == '__main__':
    main()