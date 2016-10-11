NAME=py_slim_fitnesse


docker rm -f $NAME
docker run -d \
    --name=$NAME \
    -p 8082:3680 \
    mikeplavsky/docker-waferslim 
