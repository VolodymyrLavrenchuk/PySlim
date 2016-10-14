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

server.post("/create/user", (req,res)=>{

    setTimeout(()=>{

        var res = router.db.set('users',[]);
        console.log(res);

        res = router.db.get('users').push(
                req.body);
        console.log(res);

    },2000);

    res.json(req.body);

});

server.get("/result", (req, res)=>{

    setTimeout(()=>{
        res.json({Done:true});
    },3000);

});

server.use(router);

server.listen(3000, ()=>{
    console.log("listening 3000 ...");
});
