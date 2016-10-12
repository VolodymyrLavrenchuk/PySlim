NAME=py_slim_server

docker build -t $NAME .
docker rm -f $NAME

docker network create $NAME
docker run -d \
    -v $(pwd):/$NAME \
    --network=$NAME \
    -v $(pwd):/$NAME \
    --name=$NAME $NAME 
