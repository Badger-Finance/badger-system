'''
Converts token amount per time frame to a decimal adjusted per second rate
for salary entries in the ContributorLogger contract
'''

import argparse

parser = argparse.ArgumentParser(description='Convert a token salary rate to a decimal adusted, per second rate')

parser.add_argument('amount', type=int, help='amount of tokens')                      
parser.add_argument('timeframe', type=str, help='time frame to convert (minute, hour, day, week, month (30 days), year)')
parser.add_argument('--periods', type=int, help='number of periods of the specified timeframe')
parser.add_argument('--decimals', type=int, help='decimals in token, default 18')

args = parser.parse_args()

accepted_time_frames = {
  "minute": 60, 
  "hour": 60*60, 
  "day": 60*60*24, 
  "week": 60*60*24*7, 
  "month": 60*60*24*30, 
  "year": 60*60*24*365
}

if args.timeframe not in accepted_time_frames:
  print("invalid time frame")
  exit()
seconds = accepted_time_frames[args.timeframe]

if args.decimals:
  decimals = args.decimals
else:
  decimals = 18

if args.periods:
  periods = args.periods
else:
  periods = 1

print(seconds * args.amount * decimals * periods)
