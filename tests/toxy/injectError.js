const toxy = require('toxy')

const proxy = toxy()
const rules = proxy.rules
const poisons = proxy.poisons

proxy
  .forward('http://py_slim_server:3000')
  .poison(poisons.inject({
    code: 503,
    body: '{"error": "toxy injected error"}',
    headers: {'Content-Type': 'application/json'}
  }))
  //.withRule(rules.method('GET'))
  .withRule(rules.probability(99))

proxy.all('/*')

proxy.listen(4000)
console.log('Server listening on port:', 4000)