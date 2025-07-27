import argparse
import os
import sys
import logging
from typing import Optional
from pathlib import Path
from blockchain import Blockchain  # Assuming blockchain.py exists
from ipfs_utils import IPFSHandler  # Assuming improved ipfs_utils.py from previous response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('data_sharing.log')
    ]
)
logger = logging.getLogger(__name__)

class DataSharingCLI:
    """Command Line Interface for Blockchain-based Data Sharing Platform."""
    
    def __init__(self, ipfs_endpoint: str = '/ip4/127.0.0.1/tcp/5001'):
        """Initialize CLI with blockchain and IPFS handler."""
        try:
            self.blockchain = Blockchain()
            self.ipfs_handler = IPFSHandler(ipfs_endpoint)
            logger.info("DataSharingCLI initialized successfully")
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            sys.exit(1)

    def upload_file(self, filepath: str, owner: str) -> None:
        """Upload a file to IPFS and record transaction on blockchain."""
        filepath = Path(filepath).resolve()
        if not filepath.is_file():
            logger.error(f"File does not exist: {filepath}")
            print(f"Error: File {filepath} does not exist.")
            return

        try:
            # Calculate file hash
            file_hash = self.ipfs_handler.calculate_file_hash(str(filepath))
            if not file_hash:
                logger.error("Failed to calculate file hash")
                print("Error: Failed to calculate file hash.")
                return

            # Upload to IPFS
            ipfs_cid = self.ipfs_handler.add_file_to_ipfs(str(filepath))
            if not ipfs_cid:
                logger.error("Failed to upload file to IPFS")
                print("Error: Failed to upload file to IPFS.")
                return

            # Add transaction to blockchain
            filename = filepath.name
            metadata = {
                "ipfs_cid": ipfs_cid,
                "filename": filename,
                "owner": owner.strip()
            }

            self.blockchain.add_new_transaction(owner.strip(), owner.strip(), file_hash, metadata)
            logger.info(f"File uploaded: {filename}, CID: {ipfs_cid}, Hash: {file_hash}")
            print(f"File uploaded successfully!")
            print(f"Filename: {filename}")
            print(f"File Hash: {file_hash}")
            print(f"IPFS CID: {ipfs_cid}")
            print("Transaction added to pending pool. Use 'mine' command to confirm.")
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            print(f"Error: Failed to upload file: {e}")

    def grant_access(self, file_hash: str, owner: str, recipient: str) -> None:
        """Grant access to a file for a recipient."""
        try:
            # Validate inputs
            file_hash = file_hash.strip()
            owner = owner.strip()
            recipient = recipient.strip()
            if not all([file_hash, owner, recipient]):
                logger.error("Invalid input: file_hash, owner, or recipient is empty")
                print("Error: File hash, owner, and recipient must not be empty.")
                return

            # Find file metadata
            file_metadata = None
            for block in self.blockchain.chain:
                for transaction in block.transactions:
                    if transaction["data_hash"] == file_hash and transaction["sender"] == owner:
                        file_metadata = transaction["metadata"]
                        break
                if file_metadata:
                    break

            if not file_metadata:
                logger.error(f"File not found or not owned: Hash={file_hash}, Owner={owner}")
                print(f"Error: File with hash {file_hash} not found or you don't own it.")
                return

            # Add access grant transaction
            self.blockchain.add_new_transaction(owner, recipient, file_hash, file_metadata)
            logger.info(f"Access granted: File={file_metadata['filename']}, Recipient={recipient}")
            print(f"Access granted to {recipient} for file {file_metadata['filename']}")
            print("Transaction added to pending pool. Use 'mine' command to confirm.")
        except Exception as e:
            logger.error(f"Error granting access: {e}")
            print(f"Error: Failed to grant access: {e}")

    def request_file(self, file_hash: str, recipient: str, output_dir: str) -> None:
        """Request and download a file from IPFS if access is granted."""
        try:
            # Validate inputs
            file_hash = file_hash.strip()
            recipient = recipient.strip()
            output_dir = Path(output_dir).resolve()
            if not file_hash or not recipient:
                logger.error("Invalid input: file_hash or recipient is empty")
                print("Error: File hash and recipient must not be empty.")
                return

            # Check access permissions
            if not self.blockchain.has_access(recipient, file_hash):
                logger.error(f"Access denied: Recipient={recipient}, Hash={file_hash}")
                print(f"Error: {recipient} does not have access to file with hash {file_hash}")
                return

            # Find IPFS CID and filename
            ipfs_cid = None
            filename = None
            for block in self.blockchain.chain:
                for transaction in block.transactions:
                    if transaction["data_hash"] == file_hash and transaction["recipient"] == recipient:
                        ipfs_cid = transaction["metadata"]["ipfs_cid"]
                        filename = transaction["metadata"]["filename"]
                        break
                if ipfs_cid:
                    break

            if not ipfs_cid or not filename:
                logger.error(f"IPFS CID not found: Hash={file_hash}")
                print("Error: IPFS CID not found for this file.")
                return

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / filename

            # Download from IPFS
            if self.ipfs_handler.get_file_from_ipfs(ipfs_cid, str(output_path)):
                # Verify integrity
                downloaded_hash = self.ipfs_handler.calculate_file_hash(str(output_path))
                if downloaded_hash == file_hash:
                    logger.info(f"File downloaded: {output_path}, Integrity verified")
                    print(f"File downloaded successfully to {output_path}")
                    print("File integrity verified!")
                else:
                    logger.warning(f"File integrity check failed: {output_path}")
                    print("Warning: File integrity check failed!")
            else:
                logger.error(f"Failed to download file: CID={ipfs_cid}")
                print("Error: Failed to download file from IPFS.")
        except Exception as e:
            logger.error(f"Error requesting file: {e}")
            print(f"Error: Failed to request file: {e}")

    def mine_block(self) -> None:
        """Mine a new block with pending transactions."""
        try:
            if not self.blockchain.pending_transactions:
                logger.info("No pending transactions to mine")
                print("No pending transactions to mine.")
                return

            logger.info("Starting mining process")
            print("Mining new block...")
            last_block = self.blockchain.last_block
            proof = self.blockchain.proof_of_work(last_block.nonce)
            block = self.blockchain.create_new_block(proof)
            logger.info(f"Block mined: Index={block.index}, Hash={block.hash}")
            print(f"Block {block.index} mined successfully!")
            print(f"Block Hash: {block.hash}")
            print(f"Transactions: {len(block.transactions)}")
        except Exception as e:
            logger.error(f"Error mining block: {e}")
            print(f"Error: Failed to mine block: {e}")

    def show_status(self) -> None:
        """Display blockchain status and recent blocks."""
        try:
            logger.info("Displaying blockchain status")
            print("Blockchain Status:")
            print(f"Total Blocks: {len(self.blockchain.chain)}")
            print(f"Pending Transactions: {len(self.blockchain.pending_transactions)}")
            print("\nRecent Blocks (up to last 3):")
            for block in self.blockchain.chain[-3:]:
                print(f"  Block {block.index}: {len(block.transactions)} transactions, "
                      f"Hash: {block.hash[:16]}...")
        except Exception as e:
            logger.error(f"Error showing status: {e}")
            print(f"Error: Failed to show status: {e}")

def main():
    """Main function to parse arguments and run CLI commands."""
    parser = argparse.ArgumentParser(
        description="Blockchain-based Data Sharing Platform CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload a file')
    upload_parser.add_argument('filepath', help='Path to the file to upload')
    upload_parser.add_argument('--owner', required=True, help='Owner of the file')

    # Grant command
    grant_parser = subparsers.add_parser('grant', help='Grant access to a file')
    grant_parser.add_argument('file_hash', help='Hash of the file')
    grant_parser.add_argument('--owner', required=True, help='Owner of the file')
    grant_parser.add_argument('--recipient', required=True, help='Recipient to grant access to')

    # Request command
    request_parser = subparsers.add_parser('request', help='Request and download a file')
    request_parser.add_argument('file_hash', help='Hash of the file to download')
    request_parser.add_argument('--recipient', required=True, help='Your identity')
    request_parser.add_argument('--output', default='./downloads', help='Output directory')

    # Mine command
    subparsers.add_parser('mine', help='Mine a new block')

    # Status command
    subparsers.add_parser('status', help='Show blockchain status')

    args = parser.parse_args()

    try:
        cli = DataSharingCLI()
        if args.command == 'upload':
            cli.upload_file(args.filepath, args.owner)
        elif args.command == 'grant':
            cli.grant_access(args.file_hash, args.owner, args.recipient)
        elif args.command == 'request':
            cli.request_file(args.file_hash, args.recipient, args.output)
        elif args.command == 'mine':
            cli.mine_block()
        elif args.command == 'status':
            cli.show_status()
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"CLI error: {e}")
        print(f"Error: An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()