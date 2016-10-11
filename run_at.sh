NAME=py_slim_fitnesse


docker rm -f $NAME
docker run -d \
    -v $(pwd)/tests:/FitNesseRoot \
    -v $(pwd):/FitNesseRoot/Scripts \
    --name=$NAME \
    -p 8083:8081 \
    mikeplavsky/docker-waferslim 
