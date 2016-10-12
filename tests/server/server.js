let db = {
    users: []
};

let srv = require('json-server');
let server = srv.create(); 
let router = srv.router(db);

let middlewares = srv.defaults();

server.use(middlewares);

server.post("/delete/users", (req, res)=>{
    console.log(router.db.set('users',[]));
    res.jsonp({Done:true});
});

server.use(router);

server.listen(3000, ()=>{
    console.log("listening 3000 ...");
});
