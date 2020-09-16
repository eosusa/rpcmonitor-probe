# rpcmonitor-probe
Probe to monitor status of all RPC endpoints for an EOSIO network and provide graphs/statistics regarding those nodes
The probe submits telemetry to https://stats.eosusa.news

The probe is made of 2 components:
  * the rpcProxy will cycle trough a remote list of configured endpoints and has a built-in greylist
    the endpoint list is dynamically updated and provided by https://wax.stats.eosusa.news
  * the StressWax.py script runs as a cronjob and simple sends rpc queries to the EOSIO chain.

Note: If you wish to run a community probe, please contact @EOSUSA_Michael on Telegram

## Pre-requirement

Your VPS hostname should be formatted as follows: probe-city-country or probe-city-region
This is very important because it will be used as your identity on the public stats.eosusa.news site.
Please make sure to add the same dns entry for it in /etc/hosts
  
## Probe install instructions

```
wget -qO- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh | bash
```
log out then log in again
```
apt update
apt install python-pip python-requests
pip install prometheus_client
nvm install node
npm install -g pm2
pm2 get pm2-logrotate ; pm2 set pm2-logrotate:retain 5 ; pm2 set pm2-logrotate:max_size 500M
npm i
```

The probe needs to persist the metrics to avoid resets on restart.
create the metrics json files
```
cp example.metrics.json metrics.json
cp example.hyperion-metrics.json hyperion-metrics.json
```

Start the proxy and make it a systemd service
```
pm2 start ecosystem.config.js
pm2 startup
pm2 save
```

add cronjobs
```
*/5 * * * * /root/rpcmonitor-probe/StressWax.py -d >> /var/log/probe.log 2>&1
*/30 * * * * /root/rpcmonitor-probe/StressHyperion.py -d >> /var/log/probe-hyp.log 2>&1
```

