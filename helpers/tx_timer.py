from time import sleep, time
from threading import Thread
from brownie.network.state import TxHistory
from rich.console import Console

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

    
    def alert(self) -> None:
        start = time()
        self.waiting = True

        while (self.waiting):
            sleep(self.timer_tick)
            if time() - start >= self.time_threshold:
                # send alert
                # history = TxHistory()
                # last = history.copy()[-1]
                print('tx time has exceeded threshold of', self.time_threshold, 'seconds on tx from', self.sender)
                self.waiting = False
                self.sender = None


    def start_timer(self, sender) -> None:
        self.sender = sender
        self.thr = Thread(target=self.alert)
        self.thr.start()
  
  
    def end_timer(self) -> None:
        self.waiting = False
        self.sender = None


tx_timer = TxTimer()
