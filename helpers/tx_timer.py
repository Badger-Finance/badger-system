from time import sleep, time
from threading import Thread
import requests
import os

class TxTimer:
    '''
    - keep track of time since a tx was first posted
    - sends alert if tx takes longer than threshold
    '''

    def __init__(self, time_threshold=1200, timer_tick=1) -> None:
        self.time_threshold = time_threshold
        self.timer_tick = timer_tick
        self.waiting = False
        self.sender = None
        self.webhook = os.environ['TX_TIMER_WEBHOOK']
        self.tx_type = ''


    def alert(self, msg) -> None:
        print(msg)
        requests.post(self.webhook, {'content': msg})

    
    def track_tx(self) -> None:
        start = time()
        self.waiting = True

        while (self.waiting):
            sleep(self.timer_tick)
            if time() - start >= self.time_threshold:
                if self.tx_type:
                    msg = '🕔 *' + self.tx_type + '* - ' + 'tx sent from ' + str(self.sender.address) + ' has exceeded threshold of ' + str(self.time_threshold) + ' seconds' 
                else:
                    msg = '🕔 tx sent from ' + str(self.sender.address) + ' has exceeded threshold of ' + str(self.time_threshold) + ' seconds'
                self.alert(msg)
                self.waiting = False
                self.sender = None
                self.tx_type = ''


    def start_timer(self, sender, tx_type) -> None:
        self.sender = sender
        self.tx_type = tx_type
        self.thr = Thread(target=self.track_tx)
        self.thr.start()
  
  
    def end_timer(self) -> None:
        self.waiting = False
        self.sender = None
        self.tx_type = ''


tx_timer = TxTimer()
