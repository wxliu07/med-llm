FROM ubuntu:latest
LABEL authors="echo"

ENTRYPOINT ["top", "-b"]