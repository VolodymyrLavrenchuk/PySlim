let db = {
    users: []
};

let srv = require('json-server');
let server = srv.create(); 
let router = srv.router(db);

let middlewares = srv.defaults();

server.use(middlewares);

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
