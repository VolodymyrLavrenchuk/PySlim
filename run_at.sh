NAME=py_slim_fitnesse


docker rm -f $NAME
docker run -d \
    -v $(pwd)/tests:/FitNesseRoot \
    --name=$NAME \
    -p 8081:8081 \
    mikeplavsky/docker-waferslim 
