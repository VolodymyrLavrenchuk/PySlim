NAME=py_slim_fitnesse

pushd tests/server
    ./run.sh
popd

docker rm -f $NAME
docker run -d \
    --network py_slim_server \
    -v $(pwd)/tests:/FitNesseRoot \
    -v $(pwd):/FitNesseRoot/Scripts \
    --name=$NAME \
    -p 8081:8081 \
    mikeplavsky/docker-waferslim 

