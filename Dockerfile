FROM ubuntu:latest
LABEL authors="alice-vrb"

ENTRYPOINT ["top", "-b"]