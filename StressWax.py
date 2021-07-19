#!/usr/bin/env python
"""
   This script sends a bunch of Wax Chain queryies to collect API endpoint reliability Data
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
import socket

RPCNODE = "http://127.0.0.1:3055"
PROMETHEUS_GATEWAY = 'http://wax.stats.eosusa.news'
PROMETHEUS_JOB = 'waxproxy'

DEBUG = False
VERSION=1.0

registry = CollectorRegistry()
rLabels = ['endpoint','range','source']
nLabels = []
wax_rpc_metrics    = Gauge('wax_rpc_metrics','WAX RPC metrics',rLabels, registry=registry)
wax_probe_version  = Gauge('wax_probe_version','probe version',nLabels, registry=registry)
headers = { 'accept': 'application/json', 'content-type': 'application/json' }

def getBotID():
  try:
    return "%s"%(socket.getfqdn())
  except:
    return uuid.uuid1()

def retryRPC( payload ):
    retry=1
    code=-1
    while code != 200:
      try:
          rest_api  = requests.post( url = RPCNODE+"/v1/chain/get_table_rows", timeout=10, headers=headers, data = json.dumps(payload)).json()
      except:
          code = 0
          
      # if rows doesnt exist we have an ERROR
      if "rows" in rest_api:
        code = 200
      else:
        # if rows doesnt exist then we got an error, so we enter retry mode
        code = 0
          
      if code != 200:
        if(retry > 10): return rest_api
        if(DEBUG):
            print(rest_api)
            print("api call returned "+str(code)+" retry attempt "+str(retry))
        time.sleep(1*retry) # Newdex doesn't like spamming , so reducing call rate
        retry+=1
    return rest_api

def is_non_zero_file(fpath):
    return os.path.isfile(fpath) and os.path.getsize(fpath) > 0

def logToPrometheus():

    wax_probe_version.set(VERSION)

    PARAMS_DELPHISTATS  = {"json":true,"code":"delphioracle","scope":"delphioracle","table":"stats","table_key":"","lower_bound":null,"upper_bound":null,"index_position":1,"key_type":"i64","limit":500,"reverse":false,"show_payer":false}
    PARAMS_SIMPLEASSETS_AUTHORS = {"json":true,"code":"simpleassets","scope":"simpleassets","table":"authors","table_key":"","lower_bound":null,"upper_bound":null,"index_position":1,"key_type":"i64","limit":2000,"reverse":false,"show_payer":false}   
    totcalls = 0
    print("Scanning delphioracle stats table.....")
    delphistats = retryRPC(PARAMS_DELPHISTATS) 
    i=0
    while i < len(delphistats['rows']):
      try:
        val_owner   = delphistats['rows'][i]['owner']
        payload     = {"code":"eosio.token","account":val_owner,"symbol":"WAX"} 
        response    = requests.post( url = RPCNODE+"/v1/chain/get_currency_balance" , timeout=10, headers=headers, data = json.dumps(payload)).json()
        #print(" %s has %s"%(val_owner,response))
        totcalls+=1
      except:
        pass # Do Nothing
      i+=1

    print("grabing simple assets authors.....")

    simpleass = retryRPC(PARAMS_SIMPLEASSETS_AUTHORS)
    totcalls+=1
    i=0
    categories = {}
    while i < len(simpleass['rows']):
        try:
          val_author   = simpleass['rows'][i]['author']
          payload     = {"code":"eosio.token","account":val_owner,"symbol":"WAX"}
          response    = requests.post( url = RPCNODE+"/v1/chain/get_currency_balance" , timeout=10, headers=headers, data = json.dumps(payload)).json()
          #print("AUTHOR: %s has %s"%(val_author,response))
          totcalls+=1
          PARAMS = {"json":true,"code":"simpleassets","scope":val_author,"table":"sassets","table_key":"","lower_bound":null,"upper_bound":null,"index_position":1,"key_type":"i64","limit":2000,"reverse":false,"show_payer":false}
          assets = retryRPC(PARAMS)
          totcalls+=1
          j=0
          while j < len(assets['rows']):
            if (len(assets['rows'][j]) > 0):
              if ( assets['rows'][j]['category'] in categories ):
                categories[assets['rows'][j]['category']] += 1
              else:
                categories[assets['rows'][j]['category']] = 1
            j+=1
        except:
          pass # Do nothing
        i+=1
    #print("We found the following categories: %s "%(json.dumps(categories, indent=2, sort_keys=True)))

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
      s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      ## Create an abstract socket, by prefixing it with null. 
      s.bind( '\0stresswax_notify_lock') 
    except socket.error as e:
      error_code = e.args[0]
      error_string = e.args[1]
      print "Process already running (%d:%s ). Exiting" % ( error_code, error_string) 
      sys.exit (0) 

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
