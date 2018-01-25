NETWORK_NAME=py_slim_server

NAME=toxy

docker build -t $NAME .
docker rm -f $NAME

docker run -d \
    -v $(pwd):/$NAME \
    --network=$NETWORK_NAME \
    -v $(pwd):/$NAME \
    --name=$NAME $NAME


sleep 2

docker logs toxy
#echo "Configuring proxy"


#docker exec  -t $NAME ./go/bin/toxiproxy-cli create jsonserver -l $NAME:4000 -u py_slim_server:3000

