module.exports = {
  apps : [
    {
      name: 'rpcProxyWaxServer',
      script: 'rpcProxyWax.js',
      args: null,
      restart_delay:0,
    },
    {
      name: 'rpcProxyHyperion',
      script: 'rpcProxyHyperion.js',
      args: null,
      restart_delay:0,
    }
  ]
}
