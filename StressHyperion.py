#!/usr/bin/env python
"""
   This script sends a bunch of Hyperion queryies to collect API endpoint reliability Data
"""

__author__      = "ghobson"
__created__     = ""
__revision__    = ""
__date__        = ""

from prometheus_client import Enum, Gauge, Info, generate_latest , push_to_gateway, pushadd_to_gateway, CollectorRegistry
import requests, json, time, os, sys, getopt
import traceback
import socket
import uuid

RPCNODE = "http://127.0.0.1:3056"
PROMETHEUS_GATEWAY = 'http://wax.stats.eosusa.news'
PROMETHEUS_JOB = 'waxhypproxy'

DEBUG = False
VERSION=1.0

registry = CollectorRegistry()
rLabels = ['endpoint','range','source']
nLabels = []
wax_rpc_metrics    = Gauge('wax_hyp_rpc_metrics','WAX RPC metrics',rLabels, registry=registry)
wax_probe_version  = Gauge('wax_hyp_probe_version','probe version',nLabels, registry=registry)
headers = { 'accept': 'application/json', 'content-type': 'application/json' }

def getBotID():
  try:
    return "%s"%(socket.getfqdn())
  except:
    return uuid.uuid1()

def logToPrometheus():

    wax_probe_version.set(VERSION)

    totcalls = 0
    print("Stressing hyperion endpoints...")
    i=0
    while i < 40:
      history=requests.get(url = RPCNODE+"/v2/history/get_actions?account=producerjson", timeout=30) 
      sys.stdout.write(".")
      sys.stdout.flush()
      totcalls+=1
      i+=1

    print("")
    proxy = requests.get( url = RPCNODE+"/metrics" ).json()
    totcalls+=1
    #print(json.dumps(proxy, indent=4, sort_keys=True))

    # RPC PROXY METRICS
    for i in proxy:
      for j in proxy[i]:
        wax_rpc_metrics.labels(endpoint=i[8:],range=j,source=getBotID()).set(float(proxy[i][j]))

    print("BOTID: %s: Stress run completed, processed %.0f calls"%(getBotID(),totcalls))
    return True

def promFlush():
    #print(generate_latest(registry))
    pushadd_to_gateway(PROMETHEUS_GATEWAY, job=getBotID(), registry=registry)

if __name__ == '__main__':

    null = None
    false = False
    true = True # fix the json below

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hdt:", ["help", "debug", "test"])
    except getopt.error as msg:
        print(msg)
        sys.exit("Invalid arguments.")

    for o, a in opts:
        if o in ("-h", "--help"):
            print("Usage: promgateway -d")
            sys.exit()

        if o in ("-d", "--debug"):
            DEBUG = True

        logToPrometheus()
        promFlush()
