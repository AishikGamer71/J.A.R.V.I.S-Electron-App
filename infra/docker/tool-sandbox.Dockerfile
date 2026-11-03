FROM alpine:3.20

RUN apk update && apk add --no-cache \
    bash \
    curl \
    git \
    python3 \
    py3-pip \
    nodejs \
    npm \
    jq

# Create non-root user
RUN addgroup -S jarvis && adduser -S jarvis -G jarvis

# Create working directory
WORKDIR /sandbox
RUN chown -R jarvis:jarvis /sandbox

USER jarvis

CMD ["/bin/bash"]
