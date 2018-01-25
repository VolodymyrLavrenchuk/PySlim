const toxy = require('toxy')

const proxy = toxy()
const rules = proxy.rules
const poisons = proxy.poisons

proxy
  .all('/users')
  .forward('http://py_slim_server:3000')
  .poison(poisons.inject({
    code: 503,
    body: '{"error": "toxy injected error"}',
    headers: {'Content-Type': 'application/json'}
  }))
  //.withRule(rules.method('GET'))  all requests are poisoned
  .withRule(rules.probability(50))

//proxy.all('/*')

proxy
  .all('/create/user')
  .poison(poisons.inject({
    code: 502,
    body: '{"error": "toxy injected error"}',
    headers: {'Content-Type': 'application/json'}
  }))
  .withRule(rules.probability(100))

proxy.listen(4000)
console.log('Server listening on port:', 4000)
