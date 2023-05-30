from nicegui import ui,app
from stellar_sdk import Server, Keypair, Network, TransactionBuilder, Asset
from stellar_sdk.client.aiohttp_client import AiohttpClient
from stellar_sdk.client.requests_client import RequestsClient
from nicegui import background_tasks

import datetime 
import asyncio
import json

trading = False
    
class Bot():
    def __init__(self):
        pub_secret_key = "SBQXZ25X3SB3JMAAUB36MZHKD2MEKQGUZL6ZQIO5Z2IDTEHWM2XN6L3C"
        TRANSACTION_TIMEOUT = 12 # seconds, how long should it wait for transaction
        self.BASE_FEE = 250000
        from_asset = Asset('QUIN', 'GDZ6UQE3EMDS5G3RDDW22RFCTRLROA3ULETFVPWC3UHC6SKEWVFWV67W')
        dest_asset = Asset('USDC', 'GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN')



        testnet = False 
        client = RequestsClient(num_retries=0, post_timeout=TRANSACTION_TIMEOUT)
        if testnet:
            testnet_secret_key = "SCCRCMFZFKG2F56ZN7GYCXFFU7SFSW4SFXZXQJJ7P66SWXOFY5ATD2IU"
            self.server = Server(horizon_url="https://horizon-testnet.stellar.org", client=client)
            self.passphrase = Network.TESTNET_NETWORK_PASSPHRASE
            self.source_asset = Asset.native()
            self.destination_asset = Asset('USDC', 'GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5')
            self.keypair = Keypair.from_secret(testnet_secret_key)
        else:
            self.server = Server(horizon_url="https://horizon.stellar.org/", client=client)
            self.passphrase = Network.PUBLIC_NETWORK_PASSPHRASE
            self.source_asset = from_asset
            self.destination_asset = dest_asset
            self.keypair = Keypair.from_secret(pub_secret_key)

        self.name = "Bot"
        
        #self.destination_asset = Asset("USDC", "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5")
        #self.destination_asset = Asset("USDC", "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN")



    def print_balance(self):
        account = self.server.accounts().account_id(self.keypair.public_key).call()
        for balance in account['balances']:
            asset_type = balance['asset_type']
            if asset_type == 'native':
                asset_type = 'XLM'
            balance_amount = balance['balance']
            print(f"Asset Type: {asset_type}, Balance: {balance_amount}")
    

    def trade(self, send_amount, dest_min):
        # Build the transaction
        paths = self.server.strict_send_paths(
            source_asset=self.source_asset,
            source_amount=send_amount,
            destination=[self.destination_asset],
        ).call()

        # Build optimal Path
        first_path = paths['_embedded']['records'][0]
        '''
        print (first_path)
        if len(first_path ) == 1:
            print ('1 length path')
            first_path = paths['_embedded']['records'][1]
        '''
        
        optimal_path = []
        
        for item in first_path['path']:
            #print(item['asset_code'])
            if item['asset_type'] == 'native':
                optimal_path.append(Asset.native())
            else:
                optimal_path.append(Asset(item['asset_code'], item['asset_issuer']))
        
        account = self.server.load_account(account_id=self.keypair.public_key)
        transaction = (
            TransactionBuilder(
                source_account=account,
                network_passphrase=bot.passphrase,
                #base_fee=self.server.fetch_base_fee(),
                base_fee=self.BASE_FEE,
            )
            .append_path_payment_strict_send_op(
                destination=self.keypair.public_key,  # sending to ourselves
                send_asset=self.source_asset,
                send_amount=send_amount,
                dest_asset=self.destination_asset,
                dest_min=dest_min,
                path=optimal_path,
            )
            .set_timeout(80)
            .build()
        )

        # Sign and submit the transaction
        print ('Submitting')
        transaction.sign(self.keypair)
        #print ('Transaction signed')
        response = self.server.submit_transaction(transaction)
        print ("Successfully Submited")
        return response 

class Globals:
    trading = False
    def __init__(self):
        pass

gl = Globals()
bot = Bot()

def try_trade():
    send_mnt = "{:.7f}".format(float(gl.tosell.value))
    min_recieve_mnt = "{:.7f}".format(float(gl.minamount.value))
    err = False
    
    #time.sleep(0.1)
    try:
        response = bot.trade(send_mnt,  min_recieve_mnt)
    except Exception as e:
        #print (str(e))
        try:
            err = str(json.loads(e.message).get('extras').get('result_codes'))
        except:
            err = str(e)
            if 'read timeout' in err:
                err = 'Timed out'
    
    #gl.status.set_text(str(response))

    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not err and response.get('successful') is True:
        print('Sucessful request')
        #print (response)
        # Get current time readable string in local timezone
        gl.status.set_text(response)
        gl.log.add_rows({'time': time, 'amount': send_mnt, 'hash': response['hash'][-5:], 'status': 'Success', 'error':''})
    else:
        error_string = err
        #print(error_string)
        
        gl.log.add_rows({'time': time, 'amount': send_mnt, 'hash': 'None', 'status': 'Failed', 'error':error_string})


        #gl.status.set_text('Trade Successful')
    #gl.status.set_text(str(response))


def on_click():
    #recieve_mnt = str(float(gl.minamount.value))
    #print (send_mnt, recieve_mnt)
    print ('Trying trade')  
    try_trade()

async def tradeloop():
    global trading 
    while True:
        if trading:
            try_trade()
        await asyncio.sleep(float(gl.delay.value))


def start_clicked():
    global trading 

    print ('Start clicked')
    trading = not trading 
    if trading is True:
        gl.startbtn.style("background: red !important;")
        gl.startbtn.set_text('Stop')
        gl.loading.set_visibility(True)
        #tradeloop()
    else:
        gl.startbtn.set_text('Start')
        gl.startbtn.style("background: rgb(90,151,207) !important;")
        gl.loading.set_visibility(False)

async def testloop():
     while trading is True:
        try_trade()
        await asyncio.sleep(float(gl.delay.value))

def test_clicked():
    #gl.startbtn.set_text('Stop')
    gl.test.style("background: red !important;")
    #time.sleep(10)


with ui.row().classes('w-full justify-center'):
    with ui.card().classes('w-full lg:w-2/3') as card:
        with ui.column().classes('w-full he'):
            label = ui.label('Converting from {} to {}'.format(bot.source_asset.code, bot.destination_asset.code))
            gl.tosell = ui.input(value='0.000003', label='Amount of {} to sell'.format(bot.source_asset.code), placeholder='type a number').classes('w-full')
            gl.minamount = ui.input(value='1000', label='Minimum {} to recieve'.format(bot.destination_asset.code), placeholder='type a number').classes('w-full')
            gl.delay = ui.number(label='Delay between trades (sec)', value=1).classes('w-full')
            with ui.row():
                gl.startbtn = ui.button('Start', on_click=lambda: start_clicked())
                ui.button('Swap once', on_click=lambda: on_click())
                #ui.button('Clear table', on_click=lambda: gl.log.clear())
                #gl.test = ui.button('Test', on_click=lambda: test_clicked())



            gl.status = ui.label('Status: ')
        with ui.column().classes('w-full'):
            columns = [
                {'name': 'time', 'label': 'Time', 'field': 'time', 'required': True, 'align': 'left'},
                {'name': 'amount', 'label': 'amount', 'field': 'amount', 'sortable': True},
                {'name': 'hash', 'label': 'Hash', 'field': 'hash', 'sortable': True},
                {'name': 'status', 'label': 'Status', 'field': 'status', 'sortable': True},
                {'name': 'error', 'label': 'Message', 'field': 'error'},
            ]
            rows = [
                {'name': 123, 'amount': '12afafafafafafafaaaaaaaaaaaaaaaaaaaaaaaaaaaaffffffffffffffffffffff3', 'hash': 123, 'status': 123, 'error': '1212312312321312312312312312313123'}
            ]
            rows =[]
            gl.log = ui.table(columns=columns, rows=rows, row_key='name').classes('w-full')
            gl.loading = ui.spinner('dots', size='lg')
            gl.loading.set_visibility(False)



app.on_startup(tradeloop)

ui.run(dark=True)

#try_trade()
