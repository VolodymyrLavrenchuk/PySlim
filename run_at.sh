NAME=py_slim_fitnesse

pushd tests/waferslim
    ./build.sh
popd

pushd tests/server
    ./run.sh
popd

pushd tests/toxic_proxy
    ./run.sh
popd

docker rm -f $NAME
docker run -d \
    --network py_slim_server \
    -v $(pwd)/tests:/FitNesseRoot \
    -v $(pwd):/FitNesseRoot/Scripts \
    --name=$NAME \
    -p 8082:8081 \
    waferslim-coverage

