from time import time
import hashlib
import json
from textwrap import dedent
from flask import Flask, jsonify, request
from urllib.parse import urlparse
from uuid import uuid4

class Blockchain(object):

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        self.new_block(proof=100, previous_hash=1)

    def register_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def new_block(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.last_block),
        }

        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        transaction = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        }
        self.current_transactions.append(transaction)

        return self.last_block['index'] + 1

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            if block.previous_hash != self.hash(last_block):
                return False
            
            if not self.valid_proof(last_block.proof, block.proof):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conficts(self):
        neighbors = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in neighbors:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

            if length > max_length and self.valid_chain(chain):
                max_length = length
                new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False

    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]


app = Flask(__name__)

node_id = str(uuid4()).replace('-', '')

blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    blockchain.new_transaction("0", node_id, 1)

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash=previous_hash)

    response = {
        'response': 'Mined a new coin',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }

    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    
    if 'sender' not in values or \
       'recipient' not in values or \
       'amount' not in values:
        return jsonify({'response': 'malformed request'}), 400

    sender = values['sender']
    recipient = values['recipient']
    amount = values['amount']

    blockchain.new_transaction(sender, recipient, amount)
    return jsonify({'response': 'success'}), 200

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error, please specify nodes field", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'response': "New nodes have been added",
        'total_nodes': list(blockchain.nodes),
    }

    return jsonify(response), 200

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conficts()

    if replaced:
        response = {
            'response': "chain was replaced",
            'new_chain': blockchain.chain,
        }
    else:
        response = {
            'response': 'chain was not replaced',
            'chain': blockchain.chain,
        }
    return jsonify(response), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
