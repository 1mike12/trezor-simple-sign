'''
Very simple commandline tool for signing messages and Bitcoin transactions with Trezor

Please do not use for mainnet transactions without first reviewing and testing code yourself. Tool's intention is to be
a proof of concept, not for regular use.

Currently only supporting P2PKH testnet addresses

By: Jason Les
JasonLes@gmail.com
@heyitscheet
'''

import binascii
from trezorlib.client import TrezorClient
from trezorlib.tx_api import TxApiBlockCypher
from trezorlib.transport_hid import HidTransport
import trezorlib.messages as proto_types
import itertools
import argparse


# Take a target address as input and search the client until a matching bip32 path is found, then return it
def find_path(target_address, client, coin='Testnet'):

    if coin == 'Testnet':
        base_path = "44'/1'"
    if coin == 'Bitcoin':
        base_path = "44'/0'"
    # Searches up to 5 accounts and 100 addresses for each (including change addresses)
    for acct, addr, chng in itertools.product(range(5), range(100), range(2)):
        curr_path = base_path + "/{}'/{}/{}".format(acct, chng, addr)
        # print(curr_path)
        bip32_path = client.expand_path(curr_path)
        curr_addr = client.get_address(coin, bip32_path)
        if curr_addr == target_address:
            return bip32_path

    # Return None if search exhausts with no match
    return None

def sign(addr, msg, tx):
    # List all connected Trezors on USB
    devices = HidTransport.enumerate()

    # Check whether we found any trezor devices
    if len(devices) == 0:
        print
        'No TREZOR found'
        return

    # Use first connected device
    transport = devices[0]

    # Determine coin/address type corresponding to signing addresses
    # TODO: Enable mainnet addresses. Currently temporarily disabled for safety.
    prefix = addr[0]
    if prefix == '1' or prefix == '3':
        # coin = 'Bitcoin'
        raise ValueError('Mainnet temporarily disabled until more testing and work is done')
    if prefix == 'm' or prefix == 'n':
        coin = 'Testnet'

    # Creates object for manipulating TREZOR
    client = TrezorClient(transport)
    if coin == 'Testnet':
        TxApi= TxApiBlockCypher(coin, 'https://api.blockcypher.com/v1/btc/test3/')
        print("Making testnet api")
    if coin == 'Bitcoin':
        # TxApi = TxApiBlockCypher(coin, 'https://api.blockcypher.com/v1/btc/main/')
        # print("Making bitcoin api")

    client.set_tx_api(TxApi)

    # Find the bip32 path of the address we are signing a message or tx from
    found_path = find_path(target_address=addr, client=client, coin=coin)
    if found_path is None:
        raise ValueError('The address {} was not found on the connected trezor {} in search for its bip32 path'.format(addr,transport))
    print('Found bip32 path:', client.get_address(coin, found_path))

    if msg is not None :
        signature = client.sign_message(coin_name=coin, n=found_path, message=msg)
        print('Signing message: "{}"\nFrom address: {}'.format(msg, addr))
        print('Signature:', signature)

    if tx is not None :
        # In this basic implementation, remember that tx data comes in the format: <PREV HASH> <PREV INDEX> <DESTINATION ADDRESS> <AMOUNT>
        prev_hash = tx[0]
        prev_index = int(tx[1])
        dest_address = tx[2]
        # TO DO: Fee handling
        send_amount = int(tx[3])

        # The inputs of the transaction.
        inputs = [
            proto_types.TxInputType(
                address_n=found_path,
                prev_hash=binascii.unhexlify(prev_hash),
                prev_index=prev_index,
            ),
        ]
        # The outputs of the transaction
        outputs = [
            proto_types.TxOutputType(
                amount=send_amount,  # Amount is in satoshis
                script_type=proto_types.OutputScriptType.PAYTOADDRESS,
                address=dest_address
            ),
        ]

        (signatures, serialized_tx) = client.sign_tx(coin, inputs, outputs)
        # print('Signatures:', signatures)
        print('Signing tx from address:', addr)
        print('Using UTXO: {} and index {} to send {} {} coins'.format(prev_hash, prev_index, send_amount/100000000, coin))
        print('Transaction:', serialized_tx.hex())

    client.close()

def main():
    parser = argparse.ArgumentParser(description='Sign a message or simple transaction with trezor')
    parser.add_argument("--addr", "-a", action='store', dest='addr', help="Address to sign from", required=True)
    parser.add_argument("--msg", "-m", action='store', dest='msg', help="Sign the following message")
    parser.add_argument("--tx", "-t", dest='tx', nargs=4, help="Sign the following transaction in the format: <PREV HASH> <PREV INDEX> <DESTINATION ADDRESS> <AMOUNT>")

    args = parser.parse_args()
    signing_addr = args.addr
    msg = args.msg
    tx = args.tx

    if msg is None and tx is None:
        raise RuntimeError('No signing operation inputted, nothing to do')

    sign(signing_addr, msg, tx)


if __name__ == '__main__':
    main()