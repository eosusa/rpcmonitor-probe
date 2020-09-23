const express = require('express')
var app = express()
const ax = require('axios')
const sleep = ms => new Promise(res => setTimeout(res, ms))
const rand = (min, max) => Math.floor(Math.random() * (Math.floor(max) - Math.ceil(min) + 1)) + Math.ceil(min)
const randSelect = (arr) => arr[rand(0, arr.length - 1)]
const logger = require('logging').default('rpcProxyNew')
const fs = require('fs-extra')
ax.defaults.timeout = 5000

app.use(function(req, res, next) {
  if (!req.headers['content-type']) req.headers['content-type'] = 'application/json'
  if (req.headers['content-type'] === 'application/x-www-form-urlencoded') req.headers['content-type'] = 'application/json'
  next()
})
app.use(express.text({limit:"20mb"}))
app.use(express.json({limit:"20mb",strict:false}))
app.set('trust proxy', 1)

var metrics = require('./metrics.json')
if (!metrics) metrics = {}

async function syncEndpoints(){
  try {
     endpoints = (await ax.get('https://wax.stats.eosusa.news/public/rpc/endpoints-wax.json')).data
     console.log('Getting Remote Endpoints',endpoints)
     setTimeout(syncEndpoints,86400000)
  } catch (err) {
    console.error(err)
    // Retry every 5 mins
    setTimeout(syncEndpoints,300000)
  }
}

async function syncMetrics(){
  try {
    await fs.writeJson('./metrics.json', metrics)
  } catch (err) {
    console.error(err)
  }
  setTimeout(syncMetrics,60000)
}

function pickEndpoint () {
  //logger.info(endpoints);
  endpoints.filter(el => !greylist.find(el2 => el === el2))
  return randSelect(endpoints)
}

var greylist = []

async function addToGreylist (endpoint) {
  const existing = greylist.indexOf(endpoint)
  if (existing > -1) return
  //logger.info('Greylisting API and picking new endpoint.', endpoint)
  greylist.push(endpoint)
  logger.info('Greylist ADD:', greylist)

  await sleep(300000)
  const index = greylist.indexOf(endpoint)
  if (index < 0) return
  else greylist.splice(index, 1)
  //logger.info('Removing API from greylist:', endpoint)
  logger.info('Greylist DEL:', greylist)
}

function isObject (item) {
  return (typeof item === 'object' && item !== null)
}

async function doQuery (req) {
  const endpoint = pickEndpoint()
  if (!endpoint) {
    await sleep(10000)
    return doQuery(req)
  }
  var start = new Date()
  const response = await ax({
    url: endpoint + req.originalUrl,
    method: req.method,
    timeout: 5000,
    validateStatus: function (status) {
      var end = new Date() - start
      logger.info(`CALL ${endpoint} `+JSON.stringify(req.body)+' '+JSON.stringify(req.params)+` ${status}`)
      if( metrics[endpoint] ) {
	      if(metrics[endpoint][status]) {
	        metrics[endpoint][status] += 1
		//logger.info(`METRICS adding 1 to ${status} for ${endpoint}`)
	      }else{
	        metrics[endpoint][status] = 1
	        //logger.info(`METRICS ADDING NEW STATUS CODE FOR ${metrics}`)
	      }
      } else {
	      var codes = {}
	      codes[status] = 1
	      metrics[endpoint] = codes
      }
      // Record total executed transactions
      if( metrics[endpoint]['total'] ) {
        metrics[endpoint]['total'] += 1
      }else{
        metrics[endpoint]['total'] = 1
      }

      // Record response times
      if( metrics[endpoint]['elapsed'] ) {
        metrics[endpoint]['elapsed'] += end
      }else{
        metrics[endpoint]['elapsed'] = end
      }

      return status < 501
    },
    data: req.body
  }).catch((err) => {
    logger.error('RPC Error:')
    logger.error(endpoint, err.message)
    if( metrics[endpoint] ) {
	if(metrics[endpoint]['50000']) {
          metrics[endpoint]['5000'] += 1
	} else {
	  metrics[endpoint]['5000'] = 1
	}
    } else {
        var codes = {}
        codes['5000'] = 1
	//logger.error(codes)
        metrics[endpoint] = codes
    }
    //addToGreylist(endpoint)
  })
  if (!response || !isObject(response.data)) {
    //if (response) logger.error('Unexpected Response:',response.data)
    await sleep(1000)
    //addToGreylist(endpoint)
    return doQuery(req)
  } else if (response.status == 500) {
    logger.error('')
    logger.error('500 ERROR')
    logger.error(JSON.stringify(response.data))
    logger.error('')
    logger.error(response.data.error.code)
    const repeatCodes = [3081001, 3010008]
    if (repeatCodes.find(el => el === response.data.error.code)) {
      //console.log('Found Repeat err code:',response.data.error.code)
      //addToGreylist(endpoint)
      await sleep(1000)
      return doQuery(req)
    } else return response
  } else {
    // response.setHeader('RPCProxyEndpoint',endpoint)
    return response
  }
}

async function init () {

  await syncEndpoints()
  await syncMetrics()

  app.all('*', async (req, res) => {
    if(req.url == '/metrics' ) {
       res.json(metrics)
    } else {
      const response = await doQuery(req)
      for (const header of Object.entries(response.headers)) { res.setHeader(header[0], header[1]) }
      res.status(response.status)
      res.send(response.data)
    }
  })
  app.listen(3055,"127.0.0.1", function () { logger.info('rpcProxy listening on port 3055') })
}

init().catch((err) => { logger.error(err.message), process.exit() })
