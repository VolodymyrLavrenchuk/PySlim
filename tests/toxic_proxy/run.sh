NETWORK_NAME=py_slim_server

NAME=toxic_proxy

docker build -t $NAME .
docker rm -f $NAME

docker run -d \
    -v $(pwd):/$NAME \
    --network=$NETWORK_NAME \
    -v $(pwd):/$NAME \
    --name=$NAME $NAME 


echo "Configuring proxy"


docker exec  -t $NAME ./go/bin/toxiproxy-cli create jsonserver -l localhost:4000 -u localhost:3000

