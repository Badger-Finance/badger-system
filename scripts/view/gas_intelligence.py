from brownie import *
from elasticsearch import Elasticsearch
import numpy as np
import json
import os

'''
Find the cheapest gas price that could be expected to get mined in a reasonable amount of time.
Historical query returns average gas price for each of the specified 
time units (minutes or hours). 

For API access:
----------------
1. Create a copy of 'credentials.example.json' in the project root 
2. Rename it 'credentials.json'
3. Create an account with https://www.anyblockanalytics.com/
4. Fill in the values in 'credentials.json'

Entry Point: 
----------------
analyze_gas()

Returns:
----------------
- Midpoint of largest bin from gas price histogram (this is the expected best gas price)
- Standard deviation
- Average gas price

Test:
----------------
test()
'''

HISTORICAL_URL = 'https://api.anyblock.tools/ethereum/ethereum/mainnet/es/'
HISTORICAL_TIMEFRAME = 'minutes' # 'minutes' or 'hours'
BINS = 60 # number of bins for histogram

# Api access credentials from https://www.anyblockanalytics.com/
AUTH = json.load(open(os.path.dirname(__file__) + "/../../credentials.json"))

# convert wei to gwei
def to_gwei(x: float) -> float:
    return x / 10**9


# Initialize the ElasticSearch Client
def initialize_elastic(network: str) -> any:
    return Elasticsearch(hosts=[network], http_auth=(AUTH['email'], AUTH['key']), timeout=180)


# fetch average hourly gas prices over the last specified days
def fetch_gas_hour(network: str, days=7) -> list[float]:
    es = initialize_elastic(network)
    data = es.search(index='tx', doc_type='tx', body = {
        "_source":["timestamp","gasPrice.num"],
        "query": {
        "bool": {
            "must": [{ 
                "range":{
                    "timestamp": {
                        "gte": "now-"+ str(days) +"d"
                    }
                }}
                
            ]
        }
        },
        "aggs": {
        "hour_bucket": {
            "date_histogram": {
                "field": "timestamp",
                "interval": "1H",
                "format": "yyyy-MM-dd hh:mm:ss"
            },
            "aggs": {
                "avgGasHour": {
                    "avg": {
                        "field": "gasPrice.num"
                    }
                }
            }
        }
    }
    })
    return [ x['avgGasHour']['value'] for x in data['aggregations']['hour_bucket']['buckets'] if x['avgGasHour']['value']]


# fetch average hourly gas prices over the last specified days
def fetch_gas_min(network: str, days=1) -> list[float]:
    es = initialize_elastic(network)
    data = es.search(index='tx', doc_type='tx', body = {
        "_source":["timestamp","gasPrice.num"],
        "query": {
        "bool": {
            "must": [{
                    
                "range":{
                    "timestamp": {
                        "gte": "now-"+ str(days) +"d"
                    }
                }}
                
            ]
        }
        },
        "aggs": {
        "minute_bucket": {
            "date_histogram": {
                "field": "timestamp",
                "interval": "1m",
                "format": "yyyy-MM-dd hh:mm"
            },
            "aggs": {
                "avgGasMin": {
                    "avg": {
                        "field": "gasPrice.num"
                    }
                }}}
    }
    })
    return [ x['avgGasMin']['value'] for x in data['aggregations']['minute_bucket']['buckets'] if x['avgGasMin']['value']]


def is_outlier(points: list[float], thresh=3.5) -> list[bool]:
    """
    Returns a boolean array with True if points are outliers and False 
    otherwise.

    Parameters:
    -----------
        points : A numobservations by numdimensions array of observations
        thresh : The modified z-score to use as a threshold. Observations with
            a modified z-score (based on the median absolute deviation) greater
            than this value will be classified as outliers.

    Returns:
    --------
        mask : A numobservations-length boolean array.

    References:
    ----------
        Boris Iglewicz and David Hoaglin (1993), "Volume 16: How to Detect and
        Handle Outliers", The ASQC Basic References in Quality Control:
        Statistical Techniques, Edward F. Mykytka, Ph.D., Editor. 
    """
    if len(points.shape) == 1:
        points = points[:,None]
    median = np.median(points, axis=0)
    diff = np.sum((points - median)**2, axis=-1)
    diff = np.sqrt(diff)
    med_abs_deviation = np.median(diff)

    modified_z_score = 0.6745 * diff / med_abs_deviation
    
    return modified_z_score > thresh


# main entry point
def analyze_gas() -> tuple[float, float, float]:
    gas_data = []

    # fetch data
    if HISTORICAL_TIMEFRAME == 'minutes':
        gas_data = fetch_gas_min(HISTORICAL_URL)
    else:
        gas_data = fetch_gas_hour(HISTORICAL_URL)
    gas_data = np.array(gas_data)

    # remove outliers
    filtered_gas_data = gas_data[~is_outlier(gas_data)]

    # Create histogram 
    counts, bins = np.histogram(filtered_gas_data, bins = BINS)

    # Find most common gas price
    biggest_bin = 0
    biggest_index = 0
    for i, x in enumerate(counts):
        if x > biggest_bin:
            biggest_bin = x
            biggest_index = i
    midpoint = (bins[biggest_index] + bins[biggest_index + 1]) / 2

    # standard deviation
    standard_dev = np.std(filtered_gas_data, dtype=np.float64)

    # average
    median = np.median(filtered_gas_data, axis=0)

    return (midpoint, standard_dev, median)


# run this to test analyze_gas and print values
def test() -> tuple[float, float, float]:
    results = analyze_gas()
    print('timeframe:', HISTORICAL_TIMEFRAME or 'hours')
    print('approximate most common gas price:', to_gwei(results[0]))
    print('standard deviation:', to_gwei(results[1]))
    print('average gas price:', to_gwei(results[2]))
    return results
