run () {
    docker exec -t py_slim_fitnesse $1
}

run "coverage report"
run "coverage html"
run "rm -fr FitNesseRoot/files/htmlcov"
run "mv htmlcov FitNesseRoot/files/"

echo "navigate to http://<host:port>/files/htmlcov/index.html" 
