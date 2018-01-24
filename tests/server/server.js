let db = {
    users: []
};

let srv = require('json-server');
let server = srv.create(); 
let router = srv.router(db);

let middlewares = srv.defaults();

let cnt = 0
let users_req_cnt = 0

server.use(middlewares);

function sortObject( obj ) {

  if ( typeof( obj ) !== 'object' || obj === null ) {

    return obj;
  }

  let sorted = {};
  let keys = Object.keys( obj ).sort();

  keys.forEach( function( key ) {

    sorted[ key ] = sortObject( obj[ key ] );
  });

  return sorted;
}

server.all( "/headers", ( req, res ) => {

  res.json( sortObject( req.headers ) );
});

server.get("/none", (req,res) => {
    res.json({
        firstName: "Tony",
        secondName: null
    });
})

server.get("/unstable", (req,res) => {
    if (cnt > 3) {
        res.json(
            [
                {
                    firstName: "Tony",
                    secondName: null
                }
            ]
        );
        cnt = 0
    }
    else {
        cnt += 1

        res.setHeader('content-length','1000')
        res.end(res.writeHead(500, 'bad incomplete response'))
    }

})

function putUsers(req, res) {
    let users = router.db
        .get('users')
        .value();

    var packed = {}
    packed[req.query.field] = users;

    if (req.query.twice) {

        let double_packed = {}
        double_packed[req.query.field] = packed;

        packed = double_packed

    }

    res.json(packed);

}
server.all("/packed/users", (req, res)=>{
    putUsers(req, res);
});

server.all("/fragile/users", (req,res) => {
    if (users_req_cnt > 3) {
        putUsers(req, res)
        users_req_cnt = 0
    }
    else {
        users_req_cnt += 1

        res.status(500).jsonp({error: "Failed to proceed request"})
    }

})

server.post("/delete/users", (req, res)=>{

    let r = router.db.set('users',[]);
    console.log(r);

    res.json({Done:true});

});       

server.put("/change/user", (req,res)=>{

    setTimeout(()=>{

        res = router.db
              .get('users')
              .find({id: req.body.id})
              .assign(req.body);

        console.log(res);

    },2000);

    res.json(req.body);

});

server.post("/create/user", (req,res)=>{

    setTimeout(()=>{

        res = router.db.get('users').push(
                req.body);

        console.log(res);

    },2000);

    res.json(req.body);

});

server.use(router);

server.listen(3000, ()=>{
    console.log("listening 3000 ...");
});
