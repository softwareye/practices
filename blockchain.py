import sys
import getopt
import hashlib
import json
import requests
from time import time
from uuid import uuid1
from textwrap import dedent
from flask import Flask,jsonify,request
from urllib.parse import urlparse

class BlockChain(object):
    def __init__(self):
        self.chain=[]
        self.current_transactions=[]
        self.nodes=set()
        self.new_block(proof=100,previous_hash=1)

    def register_node(self,address):
        parsed_url=urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self,chian):
        last_block=chain[0]
        current_index=1
        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False
            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            last_block = block
            current_index += 1
        return True

    def resolve_conflicts(self):
        neighbours=self.nodes
        #print(neighbours)
        new_chain=None
        max_length=len(self.chain)
        for node in neighbours:
            response=requests.get(f'http://{node}/chain')
            if response.status_code==200:
                length=response.json()['length']
                chain=response.json()['chain']
                if length>max_length and self.valid_chain(chain):
                    max_length=length
                    new_chain=chain
        if new_chain:
            self.chain=new_chain
            return True
        return False

    def new_block(self,proof,previous_hash=None):
        block={
            'index':len(self.chain)+1,
            'timestamp':time(),
            'transactions':self.current_transactions,
            'proof':proof,
            'previous_hash':previous_hash or self.hash(self.chain[-1]),
        }
        self.current_transactions=[]
        self.chain.append(block)
        return block

    def new_trasaction(self,sender,recipient,amount):
        self.current_transactions.append({
            'sender':sender,
            'recipient':recipient,
            'amount':amount,
        })
        return self.last_block['index']+1

    @staticmethod
    def hash(block):
       block_string=json.dumps(block,sort_keys=True).encode()
       return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
       return self.chain[-1]

    def proof_of_work(self,last_proof):
        proof=0
        while self.valid_proof(last_proof,proof) is False:
            proof+=1
        return proof

    @staticmethod
    def valid_proof(last_proof,proof):
        guess=f'{last_proof}{proof}'.encode()
        guess_hash=hashlib.sha256(guess).hexdigest()
        return guess_hash[:4]=='0000'

app=Flask(__name__)
node_identify=str(uuid1()).replace('-','')
block_chain=BlockChain()
@app.route('/mine',methods=['GET'])
def mine():
    last_block=block_chain.last_block
    last_proof=last_block['proof']
    proof=block_chain.proof_of_work(last_proof)
    block_chain.new_trasaction(sender=0,recipient=node_identify,amount=1)
    block=block_chain.new_block(proof)
    response={
        'message':'New block forged',
        'index':block['index'],
        'proof':block['proof'],
        'transactions':block['transactions'],
        'previous_hash':block['previous_hash'],
    }
    return jsonify(response),200

@app.route('/transactions/new',methods=['POST'])
def new_trasaction():
    values=request.get_json()
    required=['sender','recipient','amount']
    if not all(k in values for k in required):
        return 'Missing values',400
    index=block_chain.new_trasaction(values['sender'],values['recipient'],
                                     values['amount'])
    response={'message':f'Transaction will be add to block {index}'}
    return jsonify(response),201

@app.route('/chain',methods=['GET'])
def full_chain():
    response={
        'chain':block_chain.chain,
        'length':len(block_chain.chain),
    }
    return jsonify(response),200

@app.route('/nodes/register',methods=['POST'])
def register_nodes():
    values=request.get_json()
    nodes=values.get('nodes')
    if nodes==None:
        return "Error:Please supply a valid list of nodes",400
    for node in nodes:
        block_chain.register_node(node)
    response={
        'message':'New nodes has been added',
        'total_nodes':list(block_chain.nodes),
    }
    return jsonify(response),201

@app.route('/nodes/resolve',methods=['GET'])
def consensus():
    replaced=block_chain.resolve_conflicts()
    if replaced:
        response={
            'message':'Our chain was replaced',
            'new_chain':block_chain.chain,
        }
    else:
        response={
            'messsage':'Our chain was authoritactive',
            'new_chain':block_chain.chain,
        }
    return jsonify(response),200


if __name__=='__main__':
    opts,args=getopt.getopt(sys.argv[1:],'-p:',['port='])
    port=5000
    for opt_name,opt_value in opts:
        if opt_name in ('-p','--port'):
            port=int(opt_value)
    app.run(host='0.0.0.0',port=port)
