NETWORK_NAME=py_slim_server

NAME=toxic_proxy

docker build -t $NAME .
docker rm -f $NAME

docker run -d \
    -v $(pwd):/$NAME \
    --network=$NETWORK_NAME \
    -v $(pwd):/$NAME \
    --name=$NAME $NAME 
